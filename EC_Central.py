import socket
import threading
import random
import string
from kafka import KafkaProducer, KafkaConsumer
import sys
import time
from interfaz import Mapa  # Importamos la clase Mapa desde el archivo de la interfaz
import json
import ssl


class EC_Central:
    def __init__(self, ip, puerto, fichero_localizaciones, ip_kafka, puerto_kafka):
        self.ip = ip
        self.puerto = puerto
        self.localizaciones = {}
        self.estados_taxis = {}  # Diccionario para almacenar el estado actual de cada taxi
        self.fichero_tokens = 'tokens.txt'
        self.ip_kafka = ip_kafka
        self.puerto_kafka = puerto_kafka
        self.producer = KafkaProducer(bootstrap_servers=f'{ip_kafka}:{puerto_kafka}')  # Productor Kafka
        self.mapa = Mapa()  # Inicializamos la clase Mapa para manejar la visualización

        # Cargar las localizaciones desde el fichero
        self.leer_fichero_localizaciones(fichero_localizaciones)

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

    def escribir_token_en_fichero(self, token):
        """Escribe el token generado para un taxi en el archivo tokens.txt."""
        with open(self.fichero_tokens, 'a') as file:
            file.write(f"{token}\n")

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

        # Recibir mensaje del taxi
        mensaje = connstream.recv(1024).decode()

        if mensaje == "ALTA":
            # Generar un token para el taxi
            token = self.generar_token()

            # Escribir el token en el archivo tokens.txt
            self.escribir_token_en_fichero(token)

            # Enviar el token de vuelta al taxi
            connstream.send(token.encode())
            print(f"Token {token} generado y enviado al taxi.")

        elif mensaje.startswith("AUTENTICAR"):
            # Extraer el token del mensaje
            token = mensaje.split(" ")[1]

            # Verificar si el token está en el archivo de tokens
            if self.consultar_fichero_tokens(token):
                connstream.send("Autenticado correctamente".encode())
                print(f"Taxi con token {token} autenticado.")
            else:
                connstream.send("Error: Token inválido".encode())
                print(f"Intento de autenticación fallido con token {token}.")
        
        connstream.shutdown(socket.SHUT_RDWR)   
        connstream.close()

    def procesar_estado_taxi(self, estado_taxi):
        """Procesa el estado recibido del taxi y convierte ocupado/incidencia a True/False."""
        # Supongamos que el formato de estado_taxi es "ID True/False True/False Coordenadas: (x, y)"
        partes = estado_taxi.split()

        # Extraer los valores
        id_taxi = partes[0]  # ID del taxi
        ocupado = partes[1] == "True"  # Convertir a booleano
        incidencia = partes[2] == "True"  # Convertir a booleano

        # Buscar las coordenadas en la parte final de la cadena
        coordenadas = partes[-1].replace('Coordenadas:', '').strip('()').split(',')

        try:
            coordenada_x = int(coordenadas[0])
            coordenada_y = int(coordenadas[1])
        except ValueError as e:
            print(f"Error al convertir las coordenadas: {e}")
            return

        # Verificar si el taxi ya está registrado en el diccionario de estados
        if id_taxi not in self.estados_taxis:
            # Si es la primera vez, registrar el estado y mostrarlo
            self.estados_taxis[id_taxi] = (ocupado, incidencia, coordenada_x, coordenada_y)
            print(f"Nuevo taxi conectado: {estado_taxi}")
            self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y, False)  # Agregar taxi al mapa
        else:
            # Comparar con el estado anterior
            estado_anterior = self.estados_taxis[id_taxi]
            cambio_detectado = False

            # Verificar si ha habido un cambio en las coordenadas
            if estado_anterior[2] != coordenada_x or estado_anterior[3] != coordenada_y:
                print(f"Taxi {id_taxi} ha cambiado de posición a ({coordenada_x}, {coordenada_y})")
                self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y, False)  # Actualizar posición del taxi en el mapa
                cambio_detectado = True

            # Verificar si ha ocurrido una incidencia
            if estado_anterior[1] != incidencia:
                print(f"Taxi {id_taxi} ha reportado una incidencia: {incidencia}")
                self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y, True)  # Agregar taxi al mapa
                cambio_detectado = True

            # Verificar si el estado "ocupado" ha cambiado
            if estado_anterior[0] != ocupado:
                print(f"Taxi {id_taxi} ha cambiado su estado de ocupado a: {ocupado}")
                cambio_detectado = True

            # Actualizar el estado solo si ha habido un cambio
            if cambio_detectado:
                self.estados_taxis[id_taxi] = (ocupado, incidencia, coordenada_x, coordenada_y)

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

    def iniciar(self):
        """Inicia el servidor de sockets y los consumidores de Kafka en hilos separados."""
        # Iniciar el consumidor de Kafka para los taxis en un hilo separado
        hilo_kafka_taxis = threading.Thread(target=self.iniciar_consumidor_kafka_taxis, daemon=True)
        hilo_kafka_taxis.start()

        # Iniciar el consumidor de Kafka para los clientes en un hilo separado
        hilo_kafka_clientes = threading.Thread(target=self.iniciar_consumidor_kafka_clientes, daemon=True)
        hilo_kafka_clientes.start()

        # Iniciar el servidor de sockets para manejar las solicitudes de taxis
        cert = 'certServ.pem'
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, cert)
        #context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        #context.load_cert_chain(certfile="mycertfile", keyfile="mykeyfile")
        
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.puerto))
        servidor.listen(5)
        print(f"EC_Central escuchando en {self.ip}:{self.puerto}...")

        while True:
            conexion, direccion = servidor.accept()
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
