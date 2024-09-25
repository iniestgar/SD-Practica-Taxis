import socket
import threading

class EC_DE:
    def __init__(self, ip_servidor, puerto_servidor, puerto_local):
        self.ip_servidor = ip_servidor
        self.puerto_servidor = puerto_servidor
        self.puerto_local = puerto_local  # El puerto donde el taxi escuchará al sensor
        self.id_taxi = None  # Almacenar el token (ID) después de registrarse
        self.taxi_activo = True  # Indica si el taxi está activo o detenido

    def darse_de_alta(self):
        """Conectar con EC_Central para darse de alta y recibir un token."""
        if self.id_taxi is not None:
            print("Ya estás dado de alta con el token:", self.id_taxi)
            return

        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((self.ip_servidor, self.puerto_servidor))
        
        # Enviar mensaje de alta
        cliente.send("ALTA".encode())
        
        # Recibir el token de vuelta
        token = cliente.recv(1024).decode()
        print(f"Taxi ha recibido el token: {token}")
        
        # Guardar el token como ID del taxi
        self.id_taxi = token
        print(f"Token guardado en el taxi: {self.id_taxi}")
        
        cliente.close()

    def autenticar(self):
        """Autenticarse en EC_Central usando el token recibido."""
        if self.id_taxi is None:
            print("Error: El taxi no tiene un token. Debes darte de alta primero.")
            return
        
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((self.ip_servidor, self.puerto_servidor))
        
        # Enviar el token para autenticarse
        mensaje = f"AUTENTICAR {self.id_taxi}"
        cliente.send(mensaje.encode())
        
        # Recibir respuesta de autenticación
        respuesta = cliente.recv(1024).decode()
        print(f"Respuesta de la central: {respuesta}")
        
        cliente.close()

        # Si la autenticación fue exitosa, empezar a escuchar señales del sensor
        if "Autenticado correctamente" in respuesta:
            print("Esperando señales del sensor...")
            self.escuchar_senales()

    def escuchar_senales(self):
        """El taxi escucha continuamente las señales del sensor."""
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind(("0.0.0.0", self.puerto_local))
        servidor.listen(5)
        print(f"Taxi está escuchando señales en el puerto {self.puerto_local}...")

        while self.taxi_activo:
            conexion, direccion = servidor.accept()
            print(f"Señal recibida desde {direccion}")
            
            # Recibir la señal del sensor
            senal = conexion.recv(1024).decode()
            
            if senal == "1":
                # Señal de anomalía: Detener el taxi
                print("¡Anomalía detectada! El taxi se detiene.")
                self.taxi_activo = False
            else:
                print("Todo está bien. El taxi continúa.")

            conexion.close()

# Menú para el taxi
def menu():
    import sys
    if len(sys.argv) != 4:
        print("Uso: python EC_DE.py <IP_Servidor> <Puerto_Servidor> <Puerto_Local>")
    else:
        ip_servidor = sys.argv[1]
        puerto_servidor = int(sys.argv[2])
        puerto_local = int(sys.argv[3])
        taxi = EC_DE(ip_servidor, puerto_servidor, puerto_local)

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
