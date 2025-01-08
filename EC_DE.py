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
from cryptography.fernet import Fernet

# Deshabilitar las advertencias de certificados autofirmados (solo para desarrollo)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EC_DE:
    def __init__(self, ip_servidor, puerto_servidor, ip_registry, puerto_registry, puerto_local, ip_kafka, puerto_kafka, auto_mode=False):
        # Inicialización de atributos
        self.ip_servidor = ip_servidor
        self.puerto_servidor = puerto_servidor
        self.ip_registry = ip_registry
        self.puerto_registry = puerto_registry
        self.puerto_local = puerto_local
        self.id_taxi = None
        self.token = None
        self.taxi_activo = True
        self.ocupado = False
        self.incidencia = False
        self.incidencia_climatica = False  # Incidencia climática gestionada por la central
        self.coordenada_x = 1
        self.coordenada_y = 1
        self.autenticado = False
        self.id_cliente = None  # Inicializa cliente asignado como None
        self.auto_mode = auto_mode
        self.clave_cifrado = None

        # Inicialización de Kafka
        self.ip_kafka = ip_kafka
        self.puerto_kafka = puerto_kafka
        self.producer = KafkaProducer(bootstrap_servers=f'{ip_kafka}:{puerto_kafka}')

        # Iniciar hilos para escuchar señales y asignaciones de cliente
        threading.Thread(target=self.escuchar_senales, daemon=True).start()
        threading.Thread(target=self.escuchar_asignacion_cliente, daemon=True).start()

        # Iniciar hilo para escuchar incidencias
        threading.Thread(target=self.escuchar_incidencias, daemon=True).start()
        threading.Thread(target=self.escuchar_desconexión, daemon=True).start()

        # Si está en modo automático, darse de alta y autenticarse automáticamente
        if self.auto_mode:
            self.darse_de_alta()
            self.autenticar()

    def darse_de_alta(self):
        """Conectar con EC_Registry para darse de alta y recibir confirmación."""
        if self.id_taxi is not None:
            print("Ya se ha dado de alta.")
            return

        url = f'https://{self.ip_registry}:{self.puerto_registry}/taxis'
        cert_path = 'cert.pem'  # Si estás verificando el certificado
        # Solicitar el id_taxi al usuario
        id_taxi = input("Ingrese el ID del taxi: ")

        data = {
            'id_taxi': id_taxi,
            'nombre': input("Ingrese el nombre del taxi: "),
            'ciudad': input("Ingrese la ciudad del taxi: ")
        }

        try:
            response = requests.post(url, json=data, cert=('cert.pem', 'key.pem'), verify=cert_path)  # O verify=cert_path
            if response.status_code == 201:
                self.id_taxi = id_taxi
                print(f"Taxi registrado con ID: {self.id_taxi}")
            elif response.status_code == 409:
                print(f"Error: El ID '{id_taxi}' ya está en uso.")
            else:
                print(f"Error al registrar el taxi: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con EC_Registry: {e}")




    def autenticar(self):
        """Autenticarse en EC_Central y recibir el token y la clave de cifrado."""
        if self.id_taxi is None:
            print("Debe darse de alta en el registro antes de autenticarse.")
            return  # No puede autenticarse sin estar dado de alta

        try:
            #context = ssl.create_default_context()
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations("cert.pem")  # Cargar el certificado de la CA o el cert autofirmado de la central
            #context.check_hostname = True
            #context.verify_mode = ssl.CERT_REQUIRED  # Requerir verificación del certificado del servidor


            # Crear socket y envolverlo con SSL
            cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #conn = context.wrap_socket(cliente, server_hostname=self.ip_servidor)
            conn = context.wrap_socket(cliente,server_hostname=self.ip_servidor)
            conn.connect((self.ip_servidor, self.puerto_servidor))

            # Enviar el mensaje "ALTA {id_taxi}" para solicitar autenticación
            mensaje_alta = f"ALTA {self.id_taxi}"
            conn.send(mensaje_alta.encode())

            # Recibir respuesta de la central
            respuesta = conn.recv(4096).decode()

        
            # Intentar decodificar la respuesta como JSON
            datos = json.loads(respuesta)
            self.token = datos['token']
            clave_cifrado = datos['clave']

            # Guardar la clave de cifrado
            self.clave_cifrado = clave_cifrado.encode('utf-8')

            print(f"Autenticado correctamente. Token recibido: {self.token}")

            self.autenticado = True  # Ahora puede enviar mensajes a la central

            # Iniciar el envío periódico del estado en un hilo separado
            self.iniciar_envio_estado_periodico_en_hilo()

        except json.JSONDecodeError:
            print(f"Error en la extracción de datos: {respuesta}")
        except Exception as e:
            print(f"Error en la conexión con la central: {e}")  

        conn.close()


    def obtener_info_taxi(self):
        if self.id_taxi is None:
            print("No se ha registrado aún.")
            return

        url = f'https://{self.ip_registry}:{self.puerto_registry}/taxis/{self.id_taxi}'
        cert_path = 'cert.pem'  # Si estás verificando el certificado

        try:
            response = requests.get(url, verify=cert_path)  # O verify=cert_path
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
            response = requests.put(url, json=data, verify=cert_path)  # O verify=cert_path
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
        cert_path = 'cert.pem' 

        confirmacion = input("¿Estás seguro de que deseas eliminar este taxi del registro? (s/n): ")
        if confirmacion.lower() == 's':
            try:
                response = requests.delete(url, verify=cert_path)  # O verify=cert_path
                if response.status_code == 200:
                    print("Taxi eliminado correctamente del registro.")
                    self.id_taxi = None
                    self.token = None
                    self.autenticado = False
                else:
                    print(f"Error al eliminar el taxi: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"Error de conexión con EC_Registry: {e}")
        else:
            return




    def iniciar_envio_estado_periodico_en_hilo(self):
        """Inicia el envío periódico del estado en un hilo separado."""
        hilo = threading.Thread(target=self._enviar_estado_periodico, daemon=True)
        hilo.start()

    def _enviar_estado_periodico(self):
        """Envía el estado del taxi a Kafka cada segundo en un hilo separado."""
        if self.autenticado:
            while True:
                self.enviar_estado_kafka()
                time.sleep(1)


    def enviar_estado_kafka(self):
        if not self.autenticado or not hasattr(self, 'clave_cifrado'):
            return

        fernet = Fernet(self.clave_cifrado)

        # El mensaje descifrado contendrá: id, ocupado, incidencia, coordenadas
        mensaje_estado = {
            "id": self.id_taxi,
            "ocupado": self.ocupado,
            "incidencia": self.incidencia,
            "coordenadas": [self.coordenada_x, self.coordenada_y]
        }

        mensaje_json = json.dumps(mensaje_estado)
        mensaje_cifrado = fernet.encrypt(mensaje_json.encode('utf-8'))

        # Enviar: token|mensaje_cifrado
        mensaje_final = f"{self.token}|".encode('utf-8') + mensaje_cifrado

        self.producer.send('solicitud', mensaje_final)
        self.producer.flush()



    def escuchar_senales(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.settimeout(5)
        servidor.bind(("0.0.0.0", self.puerto_local))
        servidor.listen(5)

        while self.taxi_activo:
            try: 
                conexion, direccion = servidor.accept()
                # Recibir la señal del sensor
                senal = conexion.recv(1024).decode()

                if senal == "1":
                    # Señal de anomalía: Incidencia detectada
                    incidencia_sensor = True
                elif senal == "0":
                    # Señal de normalidad: No hay incidencias
                    incidencia_sensor = False
                else:
                    # Señal desconocida, mantener el estado actual
                    incidencia_sensor = self.incidencia

                # Actualizar el estado solo si no hay incidencia climática
                if not self.incidencia_climatica:
                    if incidencia_sensor != self.incidencia:
                        self.incidencia = incidencia_sensor
                        print(f"Incidencia por sensor actualizada: {self.incidencia}")
                        self.enviar_estado_kafka()

                conexion.close()
            except socket.timeout:
                # Si hay un timeout, asumimos que hay una incidencia del sensor
                incidencia_sensor = True
                if not self.incidencia_climatica and incidencia_sensor != self.incidencia:
                    self.incidencia = incidencia_sensor
                    print("No se recibe señal del sensor. Marcando incidencia por sensor.")
                    self.enviar_estado_kafka()
            except Exception as e:
                print(f"Error en escuchar_senales: {e}")



            
                
    def escuchar_asignacion_cliente(self, tema='asignacionCliente'):
        """Escucha el topic de Kafka para recibir asignaciones de clientes."""
        consumer = KafkaConsumer(tema, bootstrap_servers=f'{self.ip_kafka}:{self.puerto_kafka}', auto_offset_reset='latest')

        for mensaje in consumer:
            asignacion_cifrada = mensaje.value  # mensaje en bytes
            print(f"Mensaje cifrado recibido: {asignacion_cifrada}")

            try:
                # Separar el token del mensaje cifrado
                partes = asignacion_cifrada.split(b'|', 1)
                if len(partes) < 2:
                    print("Mensaje mal formado: no se encontró el separador '|'")
                    continue

                token_bytes, mensaje_cifrado_real = partes
                token_recibido = token_bytes.decode('utf-8')

                # Verificar que el token recibido es el mismo que el taxi obtuvo durante la autenticación
                # Suponemos que el taxi ya tiene self.token y self.clave_cifrado (asignadas tras la autenticación)
                if token_recibido != self.token:
                    print(f"El token {token_recibido} no coincide con el token del taxi.")
                    continue

                # Crear objeto Fernet con la clave de cifrado
                fernet = Fernet(self.clave_cifrado)

                # Descifrar el mensaje
                mensaje_descifrado = fernet.decrypt(mensaje_cifrado_real).decode('utf-8')
                print(f"Mensaje descifrado: {mensaje_descifrado}")

                # Procesar el mensaje descifrado (JSON)
                datos_asignacion = json.loads(mensaje_descifrado)

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

            except (IndexError, ValueError, KeyError, json.JSONDecodeError) as e:
                print(f"Error al procesar el mensaje: {e}.")
            except Exception as e:
                print(f"Error general al procesar el mensaje del taxi: {e}")



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
            self.notificar_recogida_cliente(self.id_cliente)  # Notificar recogida

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

    def notificar_recogida_cliente(self, id_cliente):
        """Notifica la recogida de un cliente a la central usando Kafka."""
        mensaje = {"tipo": "recogida_cliente", "id_cliente": id_cliente}
        self.producer.send('recogidaCliente', json.dumps(mensaje).encode('utf-8'))
        self.producer.flush()
        print(f"Notificado recogida del cliente {id_cliente} a la central.")


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

    #Modulo de desconexión y vuelta al inicio
    def escuchar_desconexión(self,tema='desconexion'):
        consumer = KafkaConsumer(tema, bootstrap_servers=f'{self.ip_kafka}:{self.puerto_kafka}', auto_offset_reset='latest')

        for mensaje in consumer:
            try:
                # Separar token y mensaje cifrado
                partes = mensaje.value.split(b'|', 1)
                if len(partes) < 2:
                    print("Mensaje mal formado: no se encontró el separador '|'")
                    continue

                token_recibido, mensaje_cifrado = partes
                if token_recibido.decode('utf-8') != self.token:
                    continue  # El mensaje no es para este taxi

                # Descifrar el mensaje
                fernet = Fernet(self.clave_cifrado)
                mensaje_descifrado = fernet.decrypt(mensaje_cifrado).decode('utf-8')
                datos = json.loads(mensaje_descifrado)

                # Manejar incidencia climática
                if datos.get("tipo") == "desconexion":
                    self.taxi_activo = False
                    self.mover_hacia(1,1)
                    print(f"Taxi {self.id_taxi}: Se ha desconectado de la central.")
                    break
            except Exception as e:
                print(f"Error al procesar mensaje de desconexión: {e}")

    def escuchar_incidencias(self, tema='incidenciaClima'):
        """Escucha mensajes de incidencia climática desde Kafka."""
        consumer = KafkaConsumer(tema, bootstrap_servers=f'{self.ip_kafka}:{self.puerto_kafka}', auto_offset_reset='latest')

        for mensaje in consumer:
            try:
                # Separar token y mensaje cifrado
                partes = mensaje.value.split(b'|', 1)
                if len(partes) < 2:
                    print("Mensaje mal formado: no se encontró el separador '|'")
                    continue

                token_recibido, mensaje_cifrado = partes
                if token_recibido.decode('utf-8') != self.token:
                    continue  # El mensaje no es para este taxi

                # Descifrar el mensaje
                fernet = Fernet(self.clave_cifrado)
                mensaje_descifrado = fernet.decrypt(mensaje_cifrado).decode('utf-8')
                datos = json.loads(mensaje_descifrado)

                # Manejar incidencia climática
                if datos.get("tipo") == "incidencia_climatologica":
                    print("Taxi volviendo a base")
                    self.mover_hacia(1,1)
                    print("Taxi ya esta en la base (1,1)")
                    self.incidencia_climatica = datos["incidencia"]
                    print(f"Taxi {self.id_taxi}: Incidencia climática {'detectada' if self.incidencia_climatica else 'resuelta'}.")

                    # Actualizar el estado general del taxi
                    self.incidencia = self.incidencia_climatica or self.incidencia
                    self.enviar_estado_kafka()
            except Exception as e:
                print(f"Error al procesar mensaje de incidencia: {e}")





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
