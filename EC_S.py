import socket
import threading
import time
import msvcrt  # Para capturar teclas en Windows (si usas otro SO, puede requerir modificación)

class EC_S:
    def __init__(self, ip_taxi, puerto_taxi):
        self.ip_taxi = ip_taxi
        self.puerto_taxi = puerto_taxi
        self.anomalia_detectada = False
        self.thread_activo = True

    def enviar_senal(self, senal):
        """Envia la señal al taxi."""
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            cliente.connect((self.ip_taxi, self.puerto_taxi))
            cliente.send(senal.encode())
            cliente.close()
        except Exception as e:
            print(f"Error al enviar la señal: {e}")
            cliente.close()

    def monitorear_sistema(self):
        """Monitorea y envía una señal cada segundo."""
        while self.thread_activo:
            # Enviar señal de "taxi continua" (sin problemas)
            if self.anomalia_detectada:
                self.enviar_senal("1")  # Enviar señal de problema
                print("Anomalía detectada: Taxi debe detenerse.")
                self.thread_activo = False  # Termina el hilo si hay anomalía
            else:
                self.enviar_senal("0")  # Enviar señal normal (sin problemas)
                print("No hay anomalías. Taxi continúa.")

            # Esperar un segundo
            time.sleep(1)

    def escuchar_teclas(self):
        """Detecta cuando se presiona una tecla y activa una anomalía."""
        print("Presiona cualquier tecla para detener el taxi debido a una anomalía.")
        while self.thread_activo:
            if msvcrt.kbhit():
                msvcrt.getch()  # Capturar la tecla, no importa cuál
                self.anomalia_detectada = True
                print("Tecla presionada: Se ha detectado una anomalía.")

    def iniciar(self):
        """Inicia el monitoreo y la escucha de teclas."""
        # Hilo para monitorear y enviar señales cada segundo
        hilo_monitoreo = threading.Thread(target=self.monitorear_sistema)
        hilo_monitoreo.start()

        # Hilo para escuchar teclas
        hilo_teclas = threading.Thread(target=self.escuchar_teclas)
        hilo_teclas.start()

        # Esperar a que ambos hilos terminen
        hilo_monitoreo.join()
        hilo_teclas.join()

# Ejecutar el programa del sensor EC_S
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Uso: python EC_S.py <IP_Taxi> <Puerto_Taxi>")
    else:
        ip_taxi = sys.argv[1]
        puerto_taxi = int(sys.argv[2])
        sensor = EC_S(ip_taxi, puerto_taxi)
        sensor.iniciar()
