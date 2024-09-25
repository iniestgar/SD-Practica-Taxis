import socket
import threading
import random
import string
import sys

class EC_Central:
    def __init__(self, ip, puerto, fichero_localizaciones):
        self.ip = ip
        self.puerto = puerto
        self.localizaciones = {}     # Diccionario para almacenar los datos de las localizaciones
        self.fichero_tokens = 'tokens.txt'  # Fichero para almacenar los tokens

        # Cargar las localizaciones desde el fichero
        self.leer_fichero_localizaciones(fichero_localizaciones)
    
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
                        except ValueError:
                            print(f"Error: Coordenadas no son números enteros en la línea: {linea}")
                    else:
                        print(f"Error: Formato de línea incorrecto: {linea}")
        except FileNotFoundError:
            print(f"Error: El fichero '{fichero}' no se encuentra.")
    
    def mostrar_localizaciones(self):
        """Muestra todas las localizaciones almacenadas."""
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

    def iniciar(self):
        """Inicia el servidor y escucha solicitudes de taxis."""
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.puerto))
        servidor.listen(5)
        print(f"EC_Central escuchando en {self.ip}:{self.puerto}...")

        while True:
            conexion, direccion = servidor.accept()
            # Manejar la conexión en un nuevo hilo
            hilo = threading.Thread(target=self.manejar_solicitud, args=(conexion, direccion))
            hilo.start()

# Ejecutar el servidor con IP, Puerto y archivo de localizaciones pasados por consola
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python EC_Central.py <IP> <Puerto> <archivo_de_localizaciones>")
    else:
        ip = sys.argv[1]
        puerto = int(sys.argv[2])
        archivo_localizaciones = sys.argv[3]

        # Crear instancia de EC_Central con IP, Puerto y archivo de localizaciones
        central = EC_Central(ip, puerto, archivo_localizaciones)

        # Mostrar localizaciones antes de iniciar el servidor
        print("Localizaciones cargadas desde el archivo:")
        central.mostrar_localizaciones()

        # Iniciar el servidor
        central.iniciar()
