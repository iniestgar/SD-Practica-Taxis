import socket
import threading
from kafka import KafkaProducer, KafkaConsumer
import random
import string
import time

class EC_DE:
    def __init__(self, ip_servidor, puerto_servidor, puerto_local, ip_kafka, puerto_kafka):
        self.ip_servidor = ip_servidor
        self.puerto_servidor = puerto_servidor
        self.puerto_local = puerto_local
        self.id_taxi = None
        self.taxi_activo = True
        self.ocupado = False  # El taxi inicialmente no está ocupado (no está en un servicio)
        self.incidencia = False  # No hay incidencias al inicio
        self.coordenada_x = 1  # Coordenada inicial del taxi en x
        self.coordenada_y = 1  # Coordenada inicial del taxi en y
        self.autenticado = False  # Indica si el taxi ha sido autenticado con la central

        # Guardar las IP y el puerto de Kafka
        self.ip_kafka = ip_kafka
        self.puerto_kafka = puerto_kafka

        # Conexión al servidor Kafka
        self.producer = KafkaProducer(bootstrap_servers=f'{ip_kafka}:{puerto_kafka}')
        threading.Thread(target=self.escuchar_senales, daemon=True).start()
        threading.Thread(target=self.escuchar_asignacion_cliente, daemon=True).start()

    def darse_de_alta(self):
        """Conectar con EC_Central para darse de alta y recibir un token."""
        if self.id_taxi is not None:
            return  # Ya se ha dado de alta

        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((self.ip_servidor, self.puerto_servidor))

        # Enviar mensaje de alta
        cliente.send("ALTA".encode())

        # Recibir el token de vuelta
        token = cliente.recv(1024).decode()

        # Guardar el token como ID del taxi
        self.id_taxi = token

        cliente.close()

    def autenticar(self):
        """Autenticarse en EC_Central usando el token recibido."""
        if self.id_taxi is None:
            return  # No puede autenticarse sin estar dado de alta

        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((self.ip_servidor, self.puerto_servidor))

        # Enviar el token para autenticarse
        mensaje = f"AUTENTICAR {self.id_taxi}"
        cliente.send(mensaje.encode())

        # Recibir respuesta de autenticación
        respuesta = cliente.recv(1024).decode()

        cliente.close()

        # Verificar la autenticación
        if "Autenticado correctamente" in respuesta:
            self.autenticado = True  # Solo ahora puede enviar mensajes a la central
            print(f"ID {self.id_taxi}")
            self.iniciar_envio_estado_periodico()

    def iniciar_envio_estado_periodico(self):
        """Envía el estado del taxi a Kafka cada segundo, durante 2 segundos."""
        if self.autenticado:
            while True:  # Enviará mensajes 2 veces, una cada segundo
                self.enviar_estado_kafka()
                time.sleep(1)

    def enviar_estado_kafka(self):
        """Envía el estado del taxi a Kafka con True/False para los campos ocupado e incidencia."""
        if not self.autenticado:
            return  # Solo enviar mensajes si el taxi está autenticado

        # Enviar mensaje con el formato correcto
        mensaje = (f"{self.id_taxi} {self.ocupado} {self.incidencia} "
                f"Coordenadas: ({self.coordenada_x},{self.coordenada_y})")

        # Enviar el mensaje a Kafka
        self.producer.send('solicitud', mensaje.encode('utf-8'))
        self.producer.flush()  # Asegurar que el mensaje se envíe inmediatamente


    def escuchar_senales(self):
        """El taxi escucha continuamente las señales del sensor."""
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind(("0.0.0.0", self.puerto_local))
        servidor.listen(5)

        while self.taxi_activo:
            conexion, direccion = servidor.accept()

            # Recibir la señal del sensor
            senal = conexion.recv(1024).decode()

            if senal == "1":
                # Señal de anomalía: Incidencia detectada (semaforo, peaton, etc.)
                self.incidencia = True
                self.enviar_estado_kafka()

            elif senal == "0":
                # Señal de normalidad: No hay incidencias
                self.incidencia = False
                self.enviar_estado_kafka()

            conexion.close()

            
    def escuchar_asignacion_cliente(self, tema='asignacionCliente'):
        """Escucha el topic de Kafka para recibir asignaciones de clientes."""
        consumer = KafkaConsumer(tema, bootstrap_servers=f'{self.ip_kafka}:{self.puerto_kafka}', auto_offset_reset='latest')
        
        for mensaje in consumer:
            asignacion = mensaje.value.decode('utf-8')

            # Imprimir el mensaje recibido para verificar su formato
            print(f"Mensaje recibido: {asignacion}")

            try:
                # Extraer ID del taxi, cliente, coordenadas del cliente y destino
                id_taxi = asignacion.split("Taxi:")[1].split()[0]
                id_cliente = asignacion.split("Cliente:")[1].split()[0]
                coordenada_cliente = asignacion.split("PosicionCliente:")[1].split()[0].strip('(),')
                coordenada_destino = asignacion.split("Destino:")[1].split()[0].strip('(),')

                # Verificar si el ID del taxi en el mensaje coincide con el ID del taxi actual
                if id_taxi == self.id_taxi:
                    # Convertir las coordenadas en listas para poder separarlas y mover el taxi
                    cliente_x, cliente_y = map(int, coordenada_cliente.split(','))
                    destino_x, destino_y = map(int, coordenada_destino.split(','))

                    print(f"Taxi {self.id_taxi}: Asignación recibida. Dirigiéndose al cliente en ({cliente_x}, {cliente_y}) y luego al destino en ({destino_x}, {destino_y}).")
                    self.realizar_viaje(f"{cliente_x},{cliente_y}", f"{destino_x},{destino_y}")
                else:
                    print(f"Taxi {self.id_taxi}: El mensaje no es para este taxi (ID en mensaje: {id_taxi}). Ignorando.")

            except (IndexError, ValueError) as e:
                print(f"Error al procesar el mensaje: {e}. Mensaje: {asignacion}")


    def realizar_viaje(self, coordenada_cliente, destino_cliente):
        """Simula el viaje del taxi hacia el cliente y luego hacia el destino."""
        try:
            # El taxi comienza un viaje, marcarlo como ocupado
            self.ocupado = True
            self.enviar_estado_kafka()  # Enviar el estado actualizado a Kafka

            # Separar correctamente las coordenadas del cliente
            cliente_x, cliente_y = map(int, coordenada_cliente.split(','))

            # Separar correctamente las coordenadas del destino
            destino_x, destino_y = map(int, destino_cliente.split(','))

            # Movimiento hacia el cliente
            self.mover_hacia(cliente_x, cliente_y)
            print(f"Taxi {self.id_taxi} ha recogido al cliente.")

            # Movimiento hacia el destino
            self.mover_hacia(destino_x, destino_y)
            print(f"Taxi {self.id_taxi} ha llegado al destino.")

            # Actualizar el estado a no ocupado inmediatamente después de finalizar el viaje
            self.ocupado = False
            self.enviar_estado_kafka()  # Enviar el estado actualizado a Kafka
            self.producer.flush()  # Asegurar que el mensaje se envíe inmediatamente

        except ValueError as e:
            print(f"Error al procesar las coordenadas: {e}")




    def mover_hacia(self, objetivo_x, objetivo_y):
        """Mueve el taxi hacia una coordenada en dos ejes, primero X luego Y."""
        # Mover en el eje X
        while self.coordenada_x != objetivo_x:
            self.coordenada_x += 1 if self.coordenada_x < objetivo_x else -1
            print(f"Taxi {self.id_taxi} moviéndose en X: {self.coordenada_x}")
            time.sleep(1)

        # Mover en el eje Y
        while self.coordenada_y != objetivo_y:
            self.coordenada_y += 1 if self.coordenada_y < objetivo_y else -1
            print(f"Taxi {self.id_taxi} moviéndose en Y: {self.coordenada_y}")
            time.sleep(1)

# Menú para el taxi
def menu():
    import sys
    if len(sys.argv) != 6:
        print("Uso: python EC_DE.py <IP_Servidor> <Puerto_Servidor> <Puerto_Local> <IP_Kafka> <Puerto_Kafka>")
        sys.exit(1)

    ip_servidor = sys.argv[1]
    puerto_servidor = int(sys.argv[2])
    puerto_local = int(sys.argv[3])
    ip_kafka = sys.argv[4]
    puerto_kafka = sys.argv[5]

    # Inicializar el taxi antes de mostrar el menú
    taxi = EC_DE(ip_servidor, puerto_servidor, puerto_local, ip_kafka, puerto_kafka)

    while True:
        print("\nMenú Taxi:")
        print("1. Darse de alta")
        print("2. Autenticarse")
        print("3. Salir")
        opcion = input("Elige una opción: ")

        if opcion == '1':
            taxi.darse_de_alta()
        elif opcion == '2':
            taxi.autenticar()
        elif opcion == '3':
            print("Saliendo...")
            break
        else:
            print("Opción no válida, intenta de nuevo.")

# Ejecutar el menú del taxi
if __name__ == "__main__":
    menu()
