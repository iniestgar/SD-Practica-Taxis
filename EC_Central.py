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
            password="6633",
            database="sd_mysql"
        )
        self.cursor = self.conn.cursor()

        # Iniciar hilo para imprimir el estado de los taxis cada 10 segundos
        threading.Thread(target=self.imprimir_estado_periodico, daemon=True).start()


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
                        print(f"Error: Formato de coordenadas inválido para la localización {id_localizacion}: {e}")
                    
        except FileNotFoundError:
            print(f"Error: El fichero '{fichero}' no se encuentra.")
        except json.JSONDecodeError as e:
            print(f"Error: El fichero '{fichero}' no tiene un formato JSON válido: {e}")
        except KeyError as e:
            print(f"Error: El fichero JSON no tiene la estructura esperada: {e}")

    def mostrar_localizaciones(self):
        """Muestra todas las localizaciones almacenadas."""
        print("Localizaciones disponibles:")
        for id_localizacion, coordenadas in self.localizaciones.items():
            print(f"ID: {id_localizacion}, Coordenadas: {coordenadas}")

    def generar_token(self):
        """Genera un token de autenticación de longitud 10."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    def escribir_token_en_fichero(self, id_taxi, token):
        """Escribe el token generado para un taxi en la base de datos."""
        db = mysql.connector.connect(host="localhost", user="root", password="6633", db="sd_bbdd")
        if db.is_connected():
            cursor = db.cursor()
            cursor.execute("INSERT INTO taxis (token) VALUES (%s) where taxi_id=%s",[token],[id_taxi])
            
        """with open(self.fichero_tokens, 'a') as file:
            file.write(f"{token}\n")"""

    def consultar_fichero_tokens(self, token):
        """Consulta el archivo tokens.txt para verificar si el token existe."""
        try:
            with open(self.fichero_tokens, 'r') as file:
                for linea in file:
                    if linea.strip() == token:
                        return True
            return False
        except FileNotFoundError:
            print("Error: El fichero de tokens no existe.")
            return False

    def manejar_solicitud(self, connstream, direccion):
        """Maneja la solicitud de alta y autenticación del taxi."""
        print(f"Conexión establecida desde {direccion}")

        try:
            # Recibir mensaje del taxi
            mensaje = connstream.recv(1024).decode()
            print(f"Mensaje recibido: {mensaje}")

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
        # Recibir mensaje del taxi
        mensaje = connstream.recv(1024).decode()

        """if mensaje == "ALTA":
            # Generar un token para el taxi
            token = self.generar_token()

                # Generar una clave de cifrado para el taxi
                clave_cifrado = Fernet.generate_key().decode()  # Convertir a cadena para enviar

                # Actualizar el diccionario tokens_taxis
                self.tokens_taxis[id_taxi] = {
                    'token': token,
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
                print(f"Token y clave generados y enviados al taxi {id_taxi}, y guardados en la base de datos.")

        except Exception as e:
            print(f"Error al manejar la solicitud: {e}")
        finally:
            connstream.close()


    def procesar_estado_taxi(self, mensaje):
        """Procesa el mensaje de estado cifrado recibido de un taxi."""
        try:
            # Si mensaje es un objeto de Kafka, obtenemos su valor
            if hasattr(mensaje, 'value'):
                mensaje_cifrado = mensaje.value
            else:
                # Si mensaje es una cadena o bytes, lo usamos directamente
                if isinstance(mensaje, str):
                    mensaje_cifrado = mensaje.encode('utf-8')
                else:
                    mensaje_cifrado = mensaje

            # Dividir el mensaje para obtener id_taxi y mensaje cifrado
            partes_mensaje = mensaje_cifrado.split(b'|', 1)
            if len(partes_mensaje) < 2:
                print("Mensaje mal formado: no se encontró el separador '|'")
                return

            id_taxi_bytes, mensaje_cifrado_real = partes_mensaje
            id_taxi = id_taxi_bytes.decode('utf-8')

            # Obtener la clave de cifrado del taxi desde el diccionario tokens_taxis
            datos_taxi = self.tokens_taxis.get(id_taxi)
            if not datos_taxi:
                print(f"No se encontró el id_taxi {id_taxi} en tokens_taxis.")
                return

            clave_cifrado = datos_taxi['clave_cifrado']

            # Crear objeto Fernet con la clave de cifrado
            fernet = Fernet(clave_cifrado.encode('utf-8'))

            # Descifrar el mensaje
            mensaje_descifrado = fernet.decrypt(mensaje_cifrado_real).decode('utf-8')

            # Procesar el mensaje descifrado
            # Formato esperado: "ocupado incidencia Coordenadas: (x,y)"
            partes = mensaje_descifrado.split()

            if len(partes) < 3:
                print(f"Mensaje descifrado mal formado: {mensaje_descifrado}")
                return

            # Extraer los valores
            ocupado_str = partes[0]
            incidencia_str = partes[1]
            coordenadas_str = ' '.join(partes[2:])

            # Convertir a booleanos
            ocupado = ocupado_str.lower() == "true"
            incidencia = incidencia_str.lower() == "true"

            # Extraer las coordenadas
            try:
                coordenadas = coordenadas_str.replace('Coordenadas:', '').strip('() ')
                x_str, y_str = coordenadas.split(',')
                coordenada_x = int(x_str.strip())
                coordenada_y = int(y_str.strip())
            except Exception as e:
                print(f"Error al extraer las coordenadas: {e}")
                return

            # Actualizar el estado del taxi
            estado_anterior = self.estados_taxis.get(id_taxi)
            cambio_detectado = False

            if not estado_anterior:
                # Si es la primera vez, registrar el estado y mostrarlo
                self.estados_taxis[id_taxi] = (ocupado, incidencia, coordenada_x, coordenada_y)
                print(f"Nuevo taxi conectado: {id_taxi}")
                self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y, incidencia)  # Agregar taxi al mapa
            else:
                # Comparar con el estado anterior
                if (estado_anterior[2] != coordenada_x or
                    estado_anterior[3] != coordenada_y or
                    estado_anterior[1] != incidencia or
                    estado_anterior[0] != ocupado):
                    # Actualizar el estado en el mapa
                    self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y, incidencia)
                    cambio_detectado = True

                    # Actualizar el estado en el diccionario
                    self.estados_taxis[id_taxi] = (ocupado, incidencia, coordenada_x, coordenada_y)

        except Exception as e:
            print(f"Error al procesar el mensaje del taxi: {e}")



    def obtener_id_y_clave_de_token(self, token):
        """Obtiene el token y la clave de cifrado asociados a un token."""
        datos = self.tokens_taxis.get(token)
        if datos:
            return datos['token'], datos['clave_cifrado']
        else:
            return None, None


    def asignar_taxi(self, id_cliente, coordenada_cliente, destinos, reintentos=5, espera=3):
        
        # Convertir la lista de destinos (letras) a coordenadas reales
        destinos_coordenadas = []
        for destino in destinos:
            if destino in self.localizaciones:
                destinos_coordenadas.append(self.localizaciones[destino])
            else:
                print(f"Destino {destino} no encontrado en las localizaciones.")
                return

        intentos = 0
        taxi_asignado = False
        self.mapa.agregar_cliente(id_cliente, coordenada_cliente[0], coordenada_cliente[1])  # Agregar cliente al mapa
        while intentos < reintentos and not taxi_asignado:
            for id_taxi, estado in self.estados_taxis.items():
                ocupado, incidencia, _, _ = estado
                if not ocupado:
                    # Encontramos un taxi disponible
                    print(f"Taxi {id_taxi} asignado al cliente {id_cliente}.")
                    

                    # Generar el mensaje de asignación con múltiples destinos
                    mensaje_asignacion = json.dumps({
                        "Taxi": id_taxi,
                        "Cliente": id_cliente,
                        "PosicionCliente": coordenada_cliente,
                        "Destinos": destinos_coordenadas
                    })

                    # Enviar mensaje al topic de Kafka
                    self.producer.send('asignacionCliente', mensaje_asignacion.encode('utf-8'))
                    self.producer.flush()

                    # Actualizar el estado del taxi a ocupado
                    self.estados_taxis[id_taxi] = (True, incidencia, estado[2], estado[3])
                    taxi_asignado = True
                    break  # Salir del bucle si se asignó un taxi

            if not taxi_asignado:
                print(f"No hay taxis disponibles para el cliente {id_cliente}. Reintentando en {espera} segundos...")
                intentos += 1
                time.sleep(espera)  # Esperar antes de intentar nuevamente

        if not taxi_asignado:
            print(f"No se pudo asignar un taxi al cliente {id_cliente} después de {reintentos} intentos.")



    def procesar_solicitud_cliente(self, mensaje_cliente):
        """Procesa el mensaje del cliente y asigna un taxi."""
        # El mensaje del cliente tendrá el formato JSON con ID, coordenadas y lista de destinos
        try:
            data = json.loads(mensaje_cliente)
            id_cliente = data['id_cliente']
            coordenada_cliente = (data['posicion']['x'], data['posicion']['y'])
            destinos = data['destinos']  # Lista de destinos (letras)
            
            print(f"Solicitud recibida del cliente {id_cliente}, coordenadas: {coordenada_cliente}, destinos: {destinos}")
            
            # Asignar taxi y pasarle la lista de destinos
            self.asignar_taxi(id_cliente, coordenada_cliente, destinos)
            
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")

    def imprimir_estado_periodico(self):
        """Imprime el estado de los taxis cada 10 segundos."""
        while True:
            self.imprimir_estados_taxis()
            time.sleep(10)

    def imprimir_estados_taxis(self):
        """Imprime el estado actual de todos los taxis."""
        print("Estados de los taxis:")
        for id_taxi, estado in self.estados_taxis.items():
            ocupado, incidencia, x, y = estado
            print(f"Taxi {id_taxi} - Ocupado: {ocupado}, Incidencia: {incidencia}, Posición: ({x}, {y})")



    def iniciar_consumidor_kafka_taxis(self, tema='solicitud'):
        """Inicia un consumidor de Kafka para recibir el estado de los taxis."""
        servidor_kafka = f"{self.ip_kafka}:{self.puerto_kafka}"
        consumer = KafkaConsumer(tema, bootstrap_servers=servidor_kafka, auto_offset_reset='latest')
        print(f"Esperando mensajes de Kafka en el tema '{tema}' desde {servidor_kafka}...")
        
        for mensaje in consumer:
            estado_taxi = mensaje.value.decode('utf-8')
            self.procesar_estado_taxi(estado_taxi)

    def iniciar_consumidor_kafka_clientes(self, tema='destinos'):
        """Inicia un consumidor de Kafka para recibir las solicitudes de los clientes."""
        servidor_kafka = f"{self.ip_kafka}:{self.puerto_kafka}"
        consumer = KafkaConsumer(tema, bootstrap_servers=servidor_kafka, auto_offset_reset='latest')
        print(f"Esperando mensajes de Kafka en el tema '{tema}' desde {servidor_kafka}...")
        
        for mensaje in consumer:
            solicitud_cliente = mensaje.value.decode('utf-8')
            self.procesar_solicitud_cliente(solicitud_cliente)

    #def peticion_desconexion():
        #Enviara por kafka un mensaje con otro topic
        

    def iniciar(self):
        """Inicia el servidor de sockets y los consumidores de Kafka en hilos separados."""
        # Iniciar los consumidores de Kafka
        threading.Thread(target=self.iniciar_consumidor_kafka_taxis, daemon=True).start()
        threading.Thread(target=self.iniciar_consumidor_kafka_clientes, daemon=True).start()

        # Cuando el usuario quiera debera escribir el id de un taxi para desconectarlo y que vuelva a su posicion original
        """hilo_señal_desconectar_taxi = threading.Thread(target=self.peticion_desconexion, daemon=True)
        hilo_señal_desconectar_taxi.start()"""

        # Crear contexto SSL
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')  # Asegúrate de tener los certificados

        # Iniciar el servidor de sockets
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.puerto))
        servidor.listen(5)
        print(f"EC_Central escuchando en {self.ip}:{self.puerto}...")

        while True:
            conexion, direccion = servidor.accept()
            # Envolver el socket con SSL
            connstream = context.wrap_socket(conexion, server_side=True)
            hilo = threading.Thread(target=self.manejar_solicitud, args=(connstream, direccion))
            hilo.start()

    def imprimir_estado_periodico(self):
        """Imprime el estado de todos los taxis autenticados cada 10 segundos."""
        while True:
            print("\n--- Estado de los taxis autenticados ---")
            if not self.estados_taxis:
                print("No hay taxis autenticados.")
            else:
                for id_taxi, estado in self.estados_taxis.items():
                    ocupado, incidencia, x, y = estado
                    print(f"Taxi {id_taxi}: Ocupado: {ocupado}, Incidencia: {incidencia}, Coordenadas: ({x}, {y})")
            print("---------------------------------------")
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

    # Iniciar el servidor y el mapa de manera concurrente
    threading.Thread(target=central.iniciar, daemon=True).start()
    central.mapa.ejecutar()  # Ejecutar el mapa en el hilo principal
