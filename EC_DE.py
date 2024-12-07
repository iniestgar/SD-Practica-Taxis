import socket
import threading
from kafka import KafkaProducer, KafkaConsumer
import random
import string
import time
import json
import requests
import urllib3
import ssl

# Deshabilitar las advertencias de certificados autofirmados (solo para desarrollo)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EC_DE:
    def __init__(self, ip_servidor, puerto_servidor, ip_registry, puerto_registry, puerto_local, ip_kafka, puerto_kafka, auto_mode=False):
        # Atributos existentes
        self.ip_servidor = ip_servidor
        self.puerto_servidor = puerto_servidor
        self.ip_registry = ip_registry  # Nuevo atributo
        self.puerto_registry = puerto_registry  # Nuevo atributo
        self.puerto_local = puerto_local
        self.id_taxi = None
        self.token = None
        self.taxi_activo = True
        self.ocupado = False
        self.incidencia = False
        self.coordenada_x = 1
        self.coordenada_y = 1
        self.autenticado = False
        self.auto_mode = auto_mode

        # Guardar las IP y el puerto de Kafka
        self.ip_kafka = ip_kafka
        self.puerto_kafka = puerto_kafka

        # Conexión al servidor Kafka
        self.producer = KafkaProducer(bootstrap_servers=f'{ip_kafka}:{puerto_kafka}')
        threading.Thread(target=self.escuchar_senales, daemon=True).start()
        threading.Thread(target=self.escuchar_asignacion_cliente, daemon=True).start()

        # Si está en modo automático, darse de alta y autenticarse automáticamente
        if self.auto_mode:
            self.darse_de_alta()
            self.autenticar()

    def darse_de_alta(self):
        """Conectar con EC_Registry para darse de alta y recibir un token."""
        if self.id_taxi is not None:
            print("Ya se ha dado de alta.")
            return

        url = f'https://{self.ip_registry}:{self.puerto_registry}/taxis'

        data = {
            'nombre': input("Ingrese el nombre del taxi: "),
            'ciudad': input("Ingrese la ciudad del taxi: ")
        }

        try:
            # Agregar verify=False aquí
            response = requests.post(url, json=data, verify=False)
            if response.status_code == 200:
                respuesta = response.json()
                self.id_taxi = respuesta['id_taxi']
                self.token = respuesta['token']
                print(f"Taxi registrado con ID: {self.id_taxi}")
            else:
                print(f"Error al registrar el taxi: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con EC_Registry: {e}")



    def autenticar(self):
        """Autenticarse en EC_Central usando el token recibido."""
        if self.id_taxi is None:
            return  # No puede autenticarse sin estar dado de alta
        
        context = ssl.create_default_context()
        context.load_verify_locations('certServ.pem')
        respuesta = ''
        with socket.create_connection((self.ip_servidor, self.puerto_servidor)) as sock:
            with context.wrap_socket(sock, self.ip_servidor) as ssock:
                mensaje = f"AUTENTICAR {self.id_taxi}"
                ssock.send(mensaje.encode())
                respuesta = ssock.recv(1024).decode()
        #cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #cliente.connect((self.ip_servidor, self.puerto_servidor))

        # Enviar el token para autenticarse
        

        # Recibir respuesta de autenticación
        #respuesta = cliente.recv(1024).decode()

        #cliente.close()

        # Verificar la autenticación
        if "Autenticado correctamente" in respuesta:
            self.autenticado = True  # Solo ahora puede enviar mensajes a la central
            print(f"ID {self.id_taxi}")
            self.iniciar_envio_estado_periodico()
        else:
            print("Error en la autenticacion")

    def obtener_info_taxi(self):
        if self.id_taxi is None:
            print("No se ha registrado aún.")
            return

        url = f'https://{self.ip_registry}:{self.puerto_registry}/taxis/{self.id_taxi}'
        cert_path = 'cert.pem'  # Si estás verificando el certificado

        try:
            response = requests.get(url, verify=False)  # O verify=cert_path
            if response.status_code == 200:
                taxi_info = response.json()
                print("Información del taxi:", taxi_info)
            else:
                print(f"Error al obtener información del taxi: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con EC_Registry: {e}")

    def actualizar_info_taxi(self):
        if self.id_taxi is None:
            print("No se ha registrado aún.")
            return

        url = f'https://{self.ip_registry}:{self.puerto_registry}/taxis/{self.id_taxi}'
        cert_path = 'cert.pem'  # Si estás verificando el certificado

        nombre = input("Ingrese el nuevo nombre del taxi: ")
        ciudad = input("Ingrese la nueva ciudad del taxi: ")

        data = {
            'nombre': nombre,
            'ciudad': ciudad
        }

        try:
            response = requests.put(url, json=data, verify=False)  # O verify=cert_path
            if response.status_code == 200:
                print("Información del taxi actualizada correctamente.")
            else:
                print(f"Error al actualizar información del taxi: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con EC_Registry: {e}")

    def eliminar_taxi(self):
        if self.id_taxi is None:
            print("No se ha registrado aún.")
            return

        url = f'https://{self.ip_registry}:{self.puerto_registry}/taxis/{self.id_taxi}'
        cert_path = 'cert.pem'  # Si estás verificando el certificado

        confirmacion = input("¿Estás seguro de que deseas eliminar este taxi del registro? (s/n): ")
        if confirmacion.lower() != 's':
            return

        try:
            response = requests.delete(url, verify=False)  # O verify=cert_path
            if response.status_code == 200:
                print("Taxi eliminado correctamente del registro.")
                self.id_taxi = None
                self.token = None
                self.autenticado = False
            else:
                print(f"Error al eliminar el taxi: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con EC_Registry: {e}")




    def iniciar_envio_estado_periodico(self):
        """Envía el estado del taxi a Kafka cada segundo."""
        if self.autenticado:
            while True:
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
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.settimeout(5)
        servidor.bind(("0.0.0.0", self.puerto_local))
        servidor.listen(5)
        # print(f"Taxi escuchando señales en el puerto {self.puerto_local}")

        while self.taxi_activo:
            try: 
                conexion, direccion = servidor.accept()
                # Recibir la señal del sensor
                senal = conexion.recv(1024).decode()

                if senal == "1":
                    # Señal de anomalía: Incidencia detectada
                    nuevo_estado = True
                elif senal == "0":
                    # Señal de normalidad: No hay incidencias
                    nuevo_estado = False
                else:
                    # Señal desconocida, mantener el estado actual
                    nuevo_estado = self.incidencia

                # Solo actualizar y mostrar mensaje si el estado cambia
                if nuevo_estado != self.incidencia:
                    self.incidencia = nuevo_estado
                    if self.incidencia:
                        print("Incidencia detectada por el sensor.")
                    else:
                        print("Incidencia resuelta.")
                    self.enviar_estado_kafka()
                # Si el estado no cambia, no hacemos nada
                conexion.close()
            except socket.timeout:
                # Si hay un timeout, asumimos que hay una incidencia
                nuevo_estado = True
                if nuevo_estado != self.incidencia:
                    self.incidencia = nuevo_estado
                    # Puedes descomentar el siguiente print si deseas
                    # print("No se recibe señal del sensor. Marcando incidencia.")
                    self.enviar_estado_kafka()
                # Si el estado no cambia, no hacemos nada
            except Exception as e:
                print(f"Error en escuchar_senales: {e}")


            
                
    def escuchar_asignacion_cliente(self, tema='asignacionCliente'):
        """Escucha el topic de Kafka para recibir asignaciones de clientes."""
        consumer = KafkaConsumer(tema, bootstrap_servers=f'{self.ip_kafka}:{self.puerto_kafka}', auto_offset_reset='latest')

        for mensaje in consumer:
            asignacion = mensaje.value.decode('utf-8')

            # Imprimir el mensaje recibido para verificar su formato
            print(f"Mensaje recibido: {asignacion}")

            try:
                # Procesar el mensaje JSON con múltiples destinos
                datos_asignacion = json.loads(asignacion)
                
                # Extraer ID del taxi, cliente, coordenadas del cliente y lista de destinos
                id_taxi = datos_asignacion["Taxi"]
                id_cliente = datos_asignacion["Cliente"]
                coordenada_cliente = datos_asignacion["PosicionCliente"]
                destinos = datos_asignacion["Destinos"]

                # Verificar si el ID del taxi en el mensaje coincide con el ID del taxi actual
                if id_taxi == self.id_taxi:
                    # Convertir las coordenadas del cliente
                    cliente_x, cliente_y = coordenada_cliente

                    print(f"Taxi {self.id_taxi}: Asignación recibida. Dirigiéndose al cliente en ({cliente_x}, {cliente_y}) y luego a los destinos: {destinos}.")
                    
                    # Realizar el viaje al cliente y luego a los múltiples destinos
                    self.realizar_viaje(f"{cliente_x},{cliente_y}", destinos)
                else:
                    print(f"Taxi {self.id_taxi}: El mensaje no es para este taxi (ID en mensaje: {id_taxi}). Ignorando.")

            except (IndexError, ValueError, KeyError) as e:
                print(f"Error al procesar el mensaje: {e}. Mensaje: {asignacion}")


    def realizar_viaje(self, coordenada_cliente, destinos):
        try:
            # El taxi comienza un viaje, marcarlo como ocupado
            self.ocupado = True
            self.enviar_estado_kafka()  # Enviar el estado actualizado a Kafka

            # Separar correctamente las coordenadas del cliente
            cliente_x, cliente_y = map(int, coordenada_cliente.split(','))

            # Movimiento hacia el cliente
            self.mover_hacia(cliente_x, cliente_y)
            print(f"Taxi {self.id_taxi} ha recogido al cliente.")

            # Recorrer todos los destinos secuencialmente
            for destino in destinos:
                destino_x, destino_y = destino
                self.mover_hacia(destino_x, destino_y)
                if not self.incidencia:  # Solo se imprime el mensaje si no hay incidencia
                    print(f"Taxi {self.id_taxi} ha llegado al destino en ({destino_x}, {destino_y}).")

            # Actualizar el estado a no ocupado inmediatamente después de finalizar todos los viajes
            self.ocupado = False
            self.enviar_estado_kafka()  # Enviar el estado actualizado a Kafka
            self.producer.flush()  # Asegurar que el mensaje se envíe inmediatamente

        except ValueError as e:
            print(f"Error al procesar las coordenadas: {e}")

    def mover_hacia(self, objetivo_x, objetivo_y):
        """Mueve el taxi hacia una coordenada en dos ejes, primero X luego Y."""
        # Mover en el eje X
        while self.coordenada_x != objetivo_x:
            # Mientras el taxi tenga una incidencia, no se moverá
            if self.incidencia:
                print(f"Taxi {self.id_taxi} detenido por una incidencia. Esperando resolución...")
                while self.incidencia:
                    time.sleep(1.5)  # Espera hasta que la incidencia sea resuelta
            # Continuar movimiento si no hay incidencia
            self.coordenada_x += 1 if self.coordenada_x < objetivo_x else -1
            print(f"Taxi {self.id_taxi} moviéndose en X: {self.coordenada_x}")
            time.sleep(1.5)

        # Mover en el eje Y
        while self.coordenada_y != objetivo_y:
            if self.incidencia:
                print(f"Taxi {self.id_taxi} detenido por una incidencia. Esperando resolución...")
                while self.incidencia:
                    time.sleep(1.5)  # Espera hasta que la incidencia sea resuelta
            # Continuar movimiento si no hay incidencia
            self.coordenada_y += 1 if self.coordenada_y < objetivo_y else -1
            print(f"Taxi {self.id_taxi} moviéndose en Y: {self.coordenada_y}")
            time.sleep(1.5)

        print(f"Taxi {self.id_taxi} ha llegado a la posición: ({self.coordenada_x}, {self.coordenada_y})")


# Menú para el taxi
def menu():
    import sys
    if len(sys.argv) != 9:
        print("Uso: python EC_DE.py <IP_Central> <Puerto_Central> <IP_Registry> <Puerto_Registry> <Puerto_Local> <IP_Kafka> <Puerto_Kafka> <auto|noauto>")
        sys.exit(1)

    ip_servidor = sys.argv[1]
    puerto_servidor = int(sys.argv[2])
    ip_registry = sys.argv[3]
    puerto_registry = int(sys.argv[4])
    puerto_local = int(sys.argv[5])
    ip_kafka = sys.argv[6]
    puerto_kafka = sys.argv[7]
    modo_auto = sys.argv[8].lower() == 'auto'

    taxi = EC_DE(ip_servidor, puerto_servidor, ip_registry, puerto_registry, puerto_local, ip_kafka, puerto_kafka, auto_mode=modo_auto)

    if not modo_auto:
        while True:
            print("\nMenú Taxi:")
            print("1. Darse de alta")
            print("2. Autenticarse")
            print("3. Obtener información del taxi")
            print("4. Actualizar información del taxi")
            print("5. Eliminar taxi del registro")
            print("6. Salir")
            opcion = input("Elige una opción: ")

            if opcion == '1':
                taxi.darse_de_alta()
            elif opcion == '2':
                taxi.autenticar()
            elif opcion == '3':
                taxi.obtener_info_taxi()
            elif opcion == '4':
                taxi.actualizar_info_taxi()
            elif opcion == '5':
                taxi.eliminar_taxi()
            elif opcion == '6':
                print("Saliendo...")
                break
            else:
                print("Opción no válida, intenta de nuevo.")


# Ejecutar el menú del taxi
if __name__ == "__main__":
    menu()
