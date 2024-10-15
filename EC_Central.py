import socket
import threading
import random
import string
from kafka import KafkaProducer, KafkaConsumer
import sys
import time
from interfaz import Mapa  # Importamos la clase Mapa desde el archivo de la interfaz


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
        """Lee el archivo de localizaciones e inicializa la estructura de datos."""
        try:
            with open(fichero, 'r') as file:
                for linea in file:
                    partes = linea.strip().split()
                    if len(partes) == 3:
                        id_localizacion = partes[0]
                        try:
                            cx = int(partes[1])
                            cy = int(partes[2])
                            self.localizaciones[id_localizacion] = (cx, cy)
                            self.mapa.agregar_destino(id_localizacion, cx, cy)  # Agregar destino al mapa
                        except ValueError:
                            print(f"Error: Coordenadas no son números enteros en la línea: {linea}")
                    else:
                        print(f"Error: Formato de línea incorrecto: {linea}")
        except FileNotFoundError:
            print(f"Error: El fichero '{fichero}' no se encuentra.")

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

    def manejar_solicitud(self, conexion, direccion):
        """Maneja la solicitud de alta y autenticación del taxi."""
        print(f"Conexión establecida desde {direccion}")

        # Recibir mensaje del taxi
        mensaje = conexion.recv(1024).decode()

        if mensaje == "ALTA":
            # Generar un token para el taxi
            token = self.generar_token()

            # Escribir el token en el archivo tokens.txt
            self.escribir_token_en_fichero(token)

            # Enviar el token de vuelta al taxi
            conexion.send(token.encode())
            print(f"Token {token} generado y enviado al taxi.")

        elif mensaje.startswith("AUTENTICAR"):
            # Extraer el token del mensaje
            token = mensaje.split(" ")[1]

            # Verificar si el token está en el archivo de tokens
            if self.consultar_fichero_tokens(token):
                conexion.send("Autenticado correctamente".encode())
                print(f"Taxi con token {token} autenticado.")
            else:
                conexion.send("Error: Token inválido".encode())
                print(f"Intento de autenticación fallido con token {token}.")

        conexion.close()

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
            self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y)  # Agregar taxi al mapa
        else:
            # Comparar con el estado anterior
            estado_anterior = self.estados_taxis[id_taxi]
            cambio_detectado = False

            # Verificar si ha habido un cambio en las coordenadas
            if estado_anterior[2] != coordenada_x or estado_anterior[3] != coordenada_y:
                print(f"Taxi {id_taxi} ha cambiado de posición a ({coordenada_x}, {coordenada_y})")
                self.mapa.agregar_taxi(id_taxi, coordenada_x, coordenada_y)  # Actualizar posición del taxi en el mapa
                cambio_detectado = True

            # Verificar si ha ocurrido una incidencia
            if estado_anterior[1] != incidencia:
                print(f"Taxi {id_taxi} ha reportado una incidencia: {incidencia}")
                cambio_detectado = True

            # Verificar si el estado "ocupado" ha cambiado
            if estado_anterior[0] != ocupado:
                print(f"Taxi {id_taxi} ha cambiado su estado de ocupado a: {ocupado}")
                cambio_detectado = True

            # Actualizar el estado solo si ha habido un cambio
            if cambio_detectado:
                self.estados_taxis[id_taxi] = (ocupado, incidencia, coordenada_x, coordenada_y)

    def asignar_taxi(self, id_cliente, coordenada_cliente, destino_cliente):
        """Asigna un taxi disponible para el cliente y convierte el destino a coordenadas."""
        # Convertir el destino de letra a coordenadas reales
        if destino_cliente in self.localizaciones:
            coordenada_destino = self.localizaciones[destino_cliente]  # Obtener las coordenadas del destino
        else:
            print(f"Destino {destino_cliente} no encontrado en las localizaciones.")
            return

        for id_taxi, estado in self.estados_taxis.items():
            ocupado, incidencia, _, _ = estado
            if not ocupado:
                # Encontramos un taxi disponible
                print(f"Taxi {id_taxi} asignado al cliente {id_cliente}.")
                self.mapa.agregar_cliente(id_cliente, coordenada_cliente[0], coordenada_cliente[1])  # Agregar cliente al mapa

                # Generar el mensaje de asignación
                mensaje_asignacion = (
                    f"Taxi: {id_taxi} Cliente: {id_cliente} "
                    f"PosicionCliente: ({coordenada_cliente[0]},{coordenada_cliente[1]}) "
                    f"Destino: ({coordenada_destino[0]},{coordenada_destino[1]})"
                )

                # Enviar mensaje al topic de Kafka
                self.producer.send('asignacionCliente', mensaje_asignacion.encode('utf-8'))
                self.producer.flush()

                # Actualizar el estado del taxi a ocupado
                self.estados_taxis[id_taxi] = (True, incidencia, estado[2], estado[3])
                return

        print(f"No hay taxis disponibles para el cliente {id_cliente}.")

    def procesar_solicitud_cliente(self, mensaje_cliente):
        """Procesa el mensaje del cliente y asigna un taxi."""
        # El mensaje del cliente tendrá el formato "ID Cliente Posicion: (x, y) Destino: D"
        partes = mensaje_cliente.split()
        
        # Extraer los valores
        id_cliente = partes[0]  # ID del cliente
        
        # Extracción correcta de las coordenadas del cliente
        coordenada_cliente = partes[2].strip('(),')
        coordenada_x, coordenada_y = map(int, coordenada_cliente.split(','))

        destino_cliente = partes[-1]  # Destino en formato letra (A, B, etc.)

        print(f"Solicitud recibida del cliente {id_cliente}, coordenadas: {coordenada_x},{coordenada_y}, destino: {destino_cliente}")
        
        # Asignar taxi y convertir el destino en coordenadas
        self.asignar_taxi(id_cliente, (coordenada_x, coordenada_y), destino_cliente)

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
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.puerto))
        servidor.listen(5)
        print(f"EC_Central escuchando en {self.ip}:{self.puerto}...")

        while True:
            conexion, direccion = servidor.accept()
            hilo = threading.Thread(target=self.manejar_solicitud, args=(conexion, direccion))
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
