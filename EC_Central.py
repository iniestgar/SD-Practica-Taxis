import socket
import threading
import random
import string
from kafka import KafkaProducer, KafkaConsumer
import sys
import time
from interfaz import Mapa  # Importamos la clase Mapa desde el archivo de la interfaz
import json
from cryptography.fernet import Fernet 
import ssl
import mysql.connector
import requests
import io


class EC_Central:
    def __init__(self, ip, puerto, fichero_localizaciones, ip_kafka, puerto_kafka):
        self.ip = ip
        self.puerto = puerto
        self.localizaciones = {}
        self.estados_taxis = {}  # Diccionario para almacenar el estado actual de cada taxi
        self.tokens_taxis = {}  # Diccionario para mapear tokens a IDs de taxis
        self.ip_kafka = ip_kafka
        self.puerto_kafka = puerto_kafka
        self.producer = KafkaProducer(bootstrap_servers=f'{ip_kafka}:{puerto_kafka}')  # Productor Kafka
        self.mapa = Mapa()  # Inicializamos la clase Mapa para manejar la visualización

        # Cargar las localizaciones desde el fichero
        self.leer_fichero_localizaciones(fichero_localizaciones)

         # Conectar a la base de datos
        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="hola",
            database="sd_mysql"
        )
        self.cursor = self.conn.cursor()

        # Iniciar hilo para imprimir el estado de los taxis cada 10 segundos
        threading.Thread(target=self.imprimir_estado_periodico, daemon=True).start()

    def enviar_log(self, mensaje):
        """Envía el mensaje de log al servidor Node.js."""
        url = 'http://localhost:3001/logs'  # Cambia 'localhost' por la IP de tu servidor Node.js si está en otra máquina
        headers = {'Content-Type': 'application/json'}
        data = {'message': mensaje}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                pass  # Opcional: Puedes manejar una confirmación si lo deseas
            else:
                print(f"Error al enviar log: {response.text}")
        except Exception as e:
            print(f"Excepción al enviar log: {e}")

    def log(self, mensaje):
        """Imprime el mensaje en la consola y lo envía al front-end."""
        print(mensaje)
        self.enviar_log(mensaje)


    def leer_fichero_localizaciones(self, fichero):
        """Lee el archivo JSON de localizaciones e inicializa la estructura de datos."""
        try:
            import json
            with open(fichero, 'r') as file:
                data = json.load(file)
                
                # Iterar sobre las localizaciones en el JSON
                for location in data['locations']:
                    id_localizacion = location['Id']
                    # Separar las coordenadas que vienen como "x,y"
                    coordenadas = location['POS'].split(',')
                    try:
                        cx = int(coordenadas[0])
                        cy = int(coordenadas[1])
                        self.localizaciones[id_localizacion] = (cx, cy)
                        self.mapa.agregar_destino(id_localizacion, cx, cy)  # Agregar destino al mapa
                    except (ValueError, IndexError) as e:
                        self.log(f"Error: Formato de coordenadas inválido para la localización {id_localizacion}: {e}")
                    
        except FileNotFoundError:
            self.log(f"Error: El fichero '{fichero}' no se encuentra.")
        except json.JSONDecodeError as e:
            self.log(f"Error: El fichero '{fichero}' no tiene un formato JSON válido: {e}")
        except KeyError as e:
            self.log(f"Error: El fichero JSON no tiene la estructura esperada: {e}")

    def mostrar_localizaciones(self):
        """Muestra todas las localizaciones almacenadas."""
        self.log("Localizaciones disponibles:")
        for id_localizacion, coordenadas in self.localizaciones.items():
            self.log(f"ID: {id_localizacion}, Coordenadas: {coordenadas}")

    def generar_token(self):
        """Genera un token de autenticación de longitud 10."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    def manejar_solicitud(self, connstream, direccion):
        """Maneja la solicitud de alta y autenticación del taxi."""
        self.log(f"Conexión establecida desde {direccion}")

        try:
            # Recibir mensaje del taxi
            mensaje = connstream.recv(1024).decode()
            self.log(f"Mensaje recibido: {mensaje}")

            if mensaje.startswith("ALTA"):
                # Extraer el id_taxi del mensaje
                partes = mensaje.split(" ")
                if len(partes) < 2:
                    connstream.send("Error: Formato de mensaje inválido".encode())
                    connstream.close()
                    return
                id_taxi = partes[1]

                # Generar un token para el taxi
                token = self.generar_token()

                # Generar una clave de cifrado para el taxi
                clave_cifrado = Fernet.generate_key().decode()  # Convertir a cadena para enviar

                # Actualizar el diccionario tokens_taxis
                self.tokens_taxis[token] = {
                    'id_taxi': id_taxi,
                    'clave_cifrado': clave_cifrado
                }

                # Insertar o actualizar el token y la clave en la base de datos
                # Verificar si el id_taxi existe en la tabla
                self.cursor.execute("SELECT id_taxi FROM Taxis WHERE id_taxi = %s", (id_taxi,))
                result = self.cursor.fetchone()

                if result:
                    # Si existe, actualizar token y clave_cifrado
                    self.cursor.execute("UPDATE Taxis SET token=%s WHERE id_taxi=%s",
                                        (token, id_taxi))
                else:
                    # Si no existe, insertar un nuevo registro
                    self.cursor.execute("INSERT INTO Taxis (id_taxi, token) VALUES (%s, %s, %s)",
                                        (id_taxi, token))

                self.conn.commit()

                # Enviar el token y la clave de vuelta al taxi
                respuesta = json.dumps({"token": token, "clave": clave_cifrado})
                connstream.send(respuesta.encode())
                self.log(f"Token y clave generados y enviados al taxi {id_taxi}, y guardados en la base de datos.")

        except Exception as e:
            self.log(f"Error al manejar la solicitud: {e}")
        finally:
            connstream.close()


    def procesar_estado_taxi(self, mensaje):
        try:
            # Verificar y decodificar el mensaje recibido
            if hasattr(mensaje, 'value'):
                mensaje_cifrado = mensaje.value
            else:
                if isinstance(mensaje, str):
                    mensaje_cifrado = mensaje.encode('utf-8')
                else:
                    mensaje_cifrado = mensaje

            # Separar el token y el mensaje cifrado
            partes = mensaje_cifrado.split(b'|', 1)
            if len(partes) < 2:
                self.log("Mensaje mal formado: no se encontró el separador '|'")
                return

            token_bytes, mensaje_cifrado_real = partes
            token = token_bytes.decode('utf-8')

            # Obtener id_taxi y clave_cifrado desde tokens_taxis usando el token
            datos_taxi = self.tokens_taxis.get(token)
            if not datos_taxi:
                self.log(f"No se encontró el token {token} en tokens_taxis.")
                return

            id_taxi = datos_taxi['id_taxi']
            clave_cifrado = datos_taxi['clave_cifrado']

            # Descifrar el mensaje
            fernet = Fernet(clave_cifrado.encode('utf-8'))
            mensaje_descifrado = fernet.decrypt(mensaje_cifrado_real).decode('utf-8')

            # Convertir el mensaje descifrado a JSON
            datos = json.loads(mensaje_descifrado)

            # Extraer los datos del mensaje
            ocupado = bool(datos['ocupado'])
            incidencia = bool(datos['incidencia'])
            coordenada_x, coordenada_y = datos['coordenadas']

            # Comparar con el estado anterior para detectar cambios
            estado_anterior = self.estados_taxis.get(id_taxi)
            if estado_anterior:
                estado_cambiado = (
                    estado_anterior[0] != ocupado or
                    estado_anterior[1] != incidencia or
                    estado_anterior[2] != coordenada_x or
                    estado_anterior[3] != coordenada_y
                )
            else:
                estado_cambiado = True  # Si no hay estado anterior, siempre es un cambio

            if estado_cambiado:
                # Actualizar estado en el diccionario de memoria
                self.estados_taxis[id_taxi] = (ocupado, incidencia, coordenada_x, coordenada_y)

                # Actualizar estado en la base de datos
                self.cursor.execute(
                    """
                    UPDATE Taxis
                    SET ocupado = %s, incidencia = %s, coordenada_x = %s, coordenada_y = %s
                    WHERE id_taxi = %s
                    """,
                    (ocupado, incidencia, coordenada_x, coordenada_y, id_taxi)
                )
                self.conn.commit()

                # Log del estado actualizado solo si hay cambios
                self.log(f"Estado actualizado: Taxi {id_taxi} - Ocupado: {ocupado}, Incidencia: {incidencia}, Coordenadas: ({coordenada_x}, {coordenada_y})")

                # Actualizar el mapa con el nuevo estado
                self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y, incidencia)

        except json.JSONDecodeError as e:
            self.log(f"Error al decodificar JSON: {e}")
        except mysql.connector.Error as e:
            self.log(f"Error en la base de datos: {e}")
        except Exception as e:
            self.log(f"Error al procesar el mensaje del taxi: {e}")


    def asignar_taxi(self, id_cliente, coordenada_cliente, destinos, reintentos=5, espera=3):
        # Convertir la lista de destinos (letras) a coordenadas reales
        destinos_coordenadas = []
        for destino in destinos:
            if destino in self.localizaciones:
                destinos_coordenadas.append(self.localizaciones[destino])
            else:
                self.log(f"Destino {destino} no encontrado en las localizaciones.")
                return

        intentos = 0
        taxi_asignado = False
        self.mapa.agregar_cliente(id_cliente, coordenada_cliente[0], coordenada_cliente[1])  # Agregar cliente al mapa

        while not taxi_asignado:
            for id_taxi, estado in self.estados_taxis.items():
                ocupado, incidencia, _, _ = estado
                if not ocupado:
                    # Encontramos un taxi disponible
                    self.log(f"Taxi {id_taxi} asignado al cliente {id_cliente}.")

                    # Generar el mensaje de asignación con múltiples destinos (sin cifrar por ahora)
                    mensaje_asignacion = json.dumps({
                        "Taxi": id_taxi,
                        "Cliente": id_cliente,
                        "PosicionCliente": coordenada_cliente,
                        "Destinos": destinos_coordenadas
                    })

                    # Buscar el token y clave_cifrado asociados al id_taxi
                    token = None
                    clave_cifrado = None
                    for tok, datos in self.tokens_taxis.items():
                        if datos['id_taxi'] == id_taxi:
                            token = tok
                            clave_cifrado = datos['clave_cifrado']
                            break

                    if not token:
                        self.log(f"No se encontró información para el taxi {id_taxi} en tokens_taxis.")
                        continue  # Continúa buscando otro taxi disponible

                    # Crear objeto Fernet con la clave de cifrado
                    try:
                        fernet = Fernet(clave_cifrado.encode('utf-8'))
                    except Exception as e:
                        self.log(f"Error al crear objeto Fernet para el taxi {id_taxi}: {e}")
                        continue

                    # Cifrar el mensaje
                    try:
                        mensaje_cifrado = fernet.encrypt(mensaje_asignacion.encode('utf-8'))
                    except Exception as e:
                        self.log(f"Error al cifrar el mensaje para el taxi {id_taxi}: {e}")
                        continue

                    # Formato: token en claro + '|' + mensaje cifrado
                    mensaje_final = token.encode('utf-8') + b'|' + mensaje_cifrado

                    # Enviar mensaje cifrado al topic 'asignacionCliente'
                    try:
                        self.producer.send('asignacionCliente', mensaje_final)
                        self.producer.flush()
                        self.log(f"Mensaje de asignación enviado al taxi {id_taxi}.")
                    except Exception as e:
                        self.log(f"Error al enviar mensaje al topic 'asignacionCliente' para el taxi {id_taxi}: {e}")
                        continue

                    # Actualizar el estado del taxi a ocupado
                    self.estados_taxis[id_taxi] = (True, incidencia, estado[2], estado[3])

                    # Actualizar la base de datos para asignar el cliente al taxi
                    try:
                        self.cursor.execute(
                            """
                            UPDATE Taxis
                            SET cliente_asignado = %s
                            WHERE id_taxi = %s
                            """,
                            (id_cliente, id_taxi)
                        )
                        self.conn.commit()
                        self.log(f"Cliente {id_cliente} asignado al taxi {id_taxi} en la base de datos.")
                    except Exception as e:
                        self.log(f"Error al actualizar el cliente asignado en la base de datos para el taxi {id_taxi}: {e}")

                    taxi_asignado = True
                    break  # Salir del bucle si se asignó un taxi

            if not taxi_asignado:
                self.log(f"No hay taxis disponibles para el cliente {id_cliente}. Reintentando en {espera} segundos...")
                intentos += 1
                time.sleep(espera)  # Esperar antes de intentar nuevamente

        if not taxi_asignado:
            self.log(f"No se pudo asignar un taxi al cliente {id_cliente} después de {reintentos} intentos.")

    def procesar_solicitud_cliente(self, mensaje_cliente):
        """Procesa el mensaje del cliente y lo muestra en el mapa inmediatamente, luego asigna un taxi."""
        try:
            # Decodificar el mensaje JSON
            data = json.loads(mensaje_cliente)
            id_cliente = data['id_cliente']
            coordenada_cliente = (data['posicion']['x'], data['posicion']['y'])
            destinos = data['destinos']  # Lista de destinos (letras)

            self.log(f"Solicitud recibida del cliente {id_cliente}, coordenadas: {coordenada_cliente}, destinos: {destinos}")

            # Agregar el cliente al mapa de inmediato
            self.mapa.agregar_cliente(id_cliente, coordenada_cliente[0], coordenada_cliente[1])

            # Asignar taxi y pasarle la lista de destinos
            threading.Thread(
                target=self.asignar_taxi,
                args=(id_cliente, coordenada_cliente, destinos),
                daemon=True
            ).start()

        except json.JSONDecodeError as e:
            self.log(f"Error al decodificar JSON: {e}")
        except KeyError as e:
            self.log(f"Error: Falta la clave {e} en la solicitud del cliente.")
        except Exception as e:
            self.log(f"Error al procesar la solicitud del cliente: {e}")


    def imprimir_estado_periodico(self, url_ctc):
        """Imprime el estado de todos los taxis autenticados y la temperatura de la ciudad cada 10 segundos."""
        estado_clima_actual = "UNKNOWN"

        while True:
            # Obtener información del clima
            temperatura = "Desconocida"
            ciudad = "Desconocida"

            try:
                # Consultar el estado del clima
                response = requests.get(url_ctc)
                if response.status_code == 200:
                    datos_clima = response.json()
                    ciudad = datos_clima.get('city', 'Desconocida')
                    temperatura = datos_clima.get('temperature', 'N/A')
                    nuevo_estado_clima = datos_clima.get('trafficAllowed', 'NO')  # 'SI' o 'NO'

                    # Actualizar la incidencia climática si el estado cambia
                    if nuevo_estado_clima != estado_clima_actual:
                        estado_clima_actual = nuevo_estado_clima
                        if estado_clima_actual == "NO":
                            self.log(f"Incidencia climática detectada: Temperatura {temperatura}°C. Deteniendo taxis.")
                            self.establecer_incidencia_climatologica(True)
                        elif estado_clima_actual == "SI":
                            self.log(f"Clima seguro detectado: Temperatura {temperatura}°C. Reanudando tráfico.")
                            self.establecer_incidencia_climatologica(False)
                else:
                    self.log(f"Error al consultar el CTC: {response.status_code} - {response.text}")

            except Exception as e:
                self.log(f"Error al conectar con el servidor CTC: {e}")

            # Imprimir el estado de los taxis
            print("\n--- Estado de los taxis autenticados ---")
            if not self.estados_taxis:
                print("No hay taxis autenticados.")
            else:
                for id_taxi, estado in self.estados_taxis.items():
                    ocupado, incidencia, x, y = estado
                    print(f"Taxi {id_taxi}: Ocupado: {ocupado}, Incidencia: {incidencia}, Coordenadas: ({x}, {y})")
            print(f"Clima actual en {ciudad}: Temperatura: {temperatura}°C, Estado: {estado_clima_actual}")
            print("---------------------------------------")

            # Esperar 10 segundos antes de imprimir de nuevo
            time.sleep(10)


    def imprimir_estados_taxis(self):
        """Imprime el estado actual de todos los taxis."""
        self.log("Estados de los taxis:")
        for id_taxi, estado in self.estados_taxis.items():
            ocupado, incidencia, x, y = estado
            self.log(f"Taxi {id_taxi} - Ocupado: {ocupado}, Incidencia: {incidencia}, Posición: ({x}, {y})")
            

    def consultar_estado_clima(self, url_ctc):
        """Consulta el estado del clima al servidor CTC y actualiza el estado de los taxis según la temperatura."""
        estado_clima_anterior = None

        while True:
            try:
                # Realizar la petición al servidor CTC
                response = requests.get(url_ctc)
                if response.status_code == 200:
                    datos = response.json()
                    temperatura = datos.get('temperature', 0)
                    estado_clima = datos.get('trafficAllowed', 'NO')  # SI o NO

                    # Cambio de estado del clima
                    if estado_clima != estado_clima_anterior:
                        if estado_clima == "NO":
                            self.log(f"Clima peligroso detectado: Temperatura {temperatura}°C. Deteniendo taxis.")
                            self.establecer_incidencia_climatologica(True)
                        elif estado_clima == "SI":
                            self.log(f"Clima seguro detectado: Temperatura {temperatura}°C. Reanudando tráfico.")
                            self.establecer_incidencia_climatologica(False)

                        estado_clima_anterior = estado_clima
                else:
                    self.log(f"Error al consultar el CTC: {response.status_code} - {response.text}")
            except Exception as e:
                self.log(f"Error al conectar con el servidor CTC: {e}")

            # Esperar 10 segundos antes de la próxima consulta
            time.sleep(10)

    def establecer_incidencia_climatologica(self, incidencia):
        """Activa o desactiva la incidencia climática para todos los taxis."""
        # Actualizar el estado en memoria y en la base de datos
        for id_taxi in self.estados_taxis.keys():
            ocupado, _, x, y = self.estados_taxis[id_taxi]
            self.estados_taxis[id_taxi] = (ocupado, incidencia, x, y)

            # Actualizar la base de datos
            self.cursor.execute(
                "UPDATE Taxis SET incidencia = %s WHERE id_taxi = %s",
                (incidencia, id_taxi)
            )

            # Actualizar el estado en el mapa
            self.mapa.agregar_taxi(id_taxi, x, y, incidencia)

        self.conn.commit()

        # Notificar a los taxis sobre el cambio de incidencia
        mensaje = {"tipo": "incidencia_climatologica", "incidencia": incidencia}
        self.enviar_mensaje_a_todos_los_taxis(mensaje)



    def iniciar_consulta_clima(self, url_ctc):
        """Inicia un hilo para consultar el clima periódicamente."""
        hilo_clima = threading.Thread(target=self.consultar_estado_clima, args=(url_ctc,), daemon=True)
        hilo_clima.start()

    def enviar_mensaje_a_todos_los_taxis(self, mensaje):
        """Envía un mensaje cifrado a todos los taxis usando Kafka."""
        mensaje_json = json.dumps(mensaje)

        for token, datos in self.tokens_taxis.items():
            clave_cifrado = datos['clave_cifrado']
            try:
                fernet = Fernet(clave_cifrado.encode('utf-8'))
                mensaje_cifrado = fernet.encrypt(mensaje_json.encode('utf-8'))
                mensaje_final = f"{token}|".encode('utf-8') + mensaje_cifrado

                # Enviar el mensaje al tópico 'incidenciaClima'
                self.producer.send('incidenciaClima', mensaje_final)
            except Exception as e:
                self.log(f"Error al enviar mensaje al taxi {datos['id_taxi']}: {e}")    



    def iniciar_consumidor_kafka_taxis(self, tema='solicitud'):
        """Inicia un consumidor de Kafka para recibir el estado de los taxis."""
        servidor_kafka = f"{self.ip_kafka}:{self.puerto_kafka}"
        consumer = KafkaConsumer(tema, bootstrap_servers=servidor_kafka, auto_offset_reset='latest')
        self.log(f"Esperando mensajes de Kafka en el tema '{tema}' desde {servidor_kafka}...")
        
        for mensaje in consumer:
            estado_taxi = mensaje.value.decode('utf-8')
            self.procesar_estado_taxi(estado_taxi)

    def iniciar_consumidor_kafka_clientes(self, tema='destinos'):
        """Inicia un consumidor de Kafka para recibir las solicitudes de los clientes."""
        servidor_kafka = f"{self.ip_kafka}:{self.puerto_kafka}"
        consumer = KafkaConsumer(tema, bootstrap_servers=servidor_kafka, auto_offset_reset='latest')
        self.log(f"Esperando mensajes de Kafka en el tema '{tema}' desde {servidor_kafka}...")
        
        for mensaje in consumer:
            solicitud_cliente = mensaje.value.decode('utf-8')
            self.procesar_solicitud_cliente(solicitud_cliente)

    import ssl  # Asegúrate de tener esta importación

    def iniciar(self):
        """Inicia el servidor de sockets y los consumidores de Kafka en hilos separados."""
        # Iniciar los consumidores de Kafka
        threading.Thread(target=self.iniciar_consumidor_kafka_taxis, daemon=True).start()
        threading.Thread(target=self.iniciar_consumidor_kafka_clientes, daemon=True).start()

        # Crear contexto SSL
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')  # Asegúrate de tener los certificados

        # Iniciar el servidor de sockets
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.puerto))
        servidor.listen(5)
        self.log(f"EC_Central escuchando en {self.ip}:{self.puerto}...")

        while True:
            conexion, direccion = servidor.accept()
            # Envolver el socket con SSL
            connstream = context.wrap_socket(conexion, server_side=True)
            hilo = threading.Thread(target=self.manejar_solicitud, args=(connstream, direccion))
            hilo.start()

    def imprimir_estado_periodico(self):
        """Imprime el estado de todos los taxis autenticados cada 10 segundos."""
        while True:
            self.log("\n--- Estado de los taxis autenticados ---")
            if not self.estados_taxis:
                self.log("No hay taxis autenticados.")
            else:
                for id_taxi, estado in self.estados_taxis.items():
                    ocupado, incidencia, x, y = estado
                    self.log(f"Taxi {id_taxi}: Ocupado: {ocupado}, Incidencia: {incidencia}, Coordenadas: ({x}, {y})")
            self.log("---------------------------------------")
            time.sleep(10)  # Espera 10 segundos antes de imprimir de nuevo


# Ejecutar el servidor con IP, Puerto y archivo de localizaciones pasados por consola
if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Uso: python EC_Central.py <IP> <Puerto> <archivo_de_localizaciones> <IP_Kafka> <Puerto_Kafka>")
        sys.exit(1)

    ip = sys.argv[1]
    puerto = int(sys.argv[2])
    archivo_localizaciones = sys.argv[3]
    ip_kafka = sys.argv[4]
    puerto_kafka = sys.argv[5]

    # Crear instancia de EC_Central con IP, Puerto, archivo de localizaciones, IP y puerto de Kafka
    central = EC_Central(ip, puerto, archivo_localizaciones, ip_kafka, puerto_kafka)

    # Mostrar localizaciones antes de iniciar el servidor
    print("Localizaciones cargadas desde el archivo:")
    central.mostrar_localizaciones()

     # Iniciar la consulta de clima al servidor CTC
    url_ctc = "http://localhost:4000/city-traffic"  # Asegúrate de usar http
    central.iniciar_consulta_clima(url_ctc)

    # Iniciar el servidor y el mapa de manera concurrente
    threading.Thread(target=central.iniciar, daemon=True).start()
    central.mapa.ejecutar()  # Ejecutar el mapa en el hilo principal
