import socket
import threading
import time
import sys
import msvcrt  # Para capturar pulsaciones de teclas en Windows

class EC_S:
    def __init__(self, ip_taxi, puerto_taxi):
        self.ip_taxi = ip_taxi
        self.puerto_taxi = puerto_taxi
        self.incidencia = False  # Indica si hay una incidencia detectada
        self.taxi_activo = True

    def alternar_incidencia(self):
        """Alterna el estado de la incidencia al pulsar una tecla."""
        while self.taxi_activo:
            if msvcrt.kbhit():  # Si se ha pulsado una tecla
                tecla = msvcrt.getch()  # Leer la tecla presionada
                self.incidencia = not self.incidencia  # Alternar el estado de la incidencia
                estado = "Incidencia detectada" if self.incidencia else "Incidencia resuelta"
                print(estado)
            time.sleep(0.1)  # Evitar uso intensivo de CPU

    def enviar_senal(self):
        """Envía señales al taxi según el estado de la incidencia."""
        contador = 0  # Para contar los segundos
        while self.taxi_activo:
            cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                cliente.connect((self.ip_taxi, self.puerto_taxi))
                if self.incidencia:
                    cliente.send("1".encode())  # Enviar señal de incidencia
                else:
                    cliente.send("0".encode())  # Enviar señal de normalidad

                # Imprimir mensaje de conexión cada 5 segundos
                contador += 1
                if contador == 5:
                    print(f"Sensor conectado al taxi en {self.ip_taxi}:{self.puerto_taxi}")
                    contador = 0  # Reiniciar el contador

            except ConnectionRefusedError:
                print(f"El taxi en {self.ip_taxi}:{self.puerto_taxi} no está disponible.")
            except ConnectionResetError:
                print(f"Conexión restablecida por el taxi en {self.ip_taxi}:{self.puerto_taxi}. Reintentando...")
            except Exception as e:
                print(f"Error en enviar_senal: {e}")
            finally:
                cliente.close()

            time.sleep(1)  # Enviar señal cada segundo

    def iniciar(self):
        """Inicia la detección de incidencias y el envío de señales."""
        hilo_teclado = threading.Thread(target=self.alternar_incidencia, daemon=True)
        hilo_teclado.start()

        self.enviar_senal()

# Menú para el sensor
def menu():
    import sys
    if len(sys.argv) != 3:
        print("Uso: python EC_S.py <IP_Taxi> <Puerto_Taxi>")
        sys.exit(1)

    ip_taxi = sys.argv[1]
    puerto_taxi = int(sys.argv[2])

    sensor = EC_S(ip_taxi, puerto_taxi)
    sensor.iniciar()

if __name__ == "__main__":
    menu()
