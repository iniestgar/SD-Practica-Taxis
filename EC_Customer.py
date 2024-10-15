import random
import string
from kafka import KafkaProducer
import sys

class Cliente:
    def __init__(self):
        # Generar ID aleatorio para el cliente
        self.id_cliente = self.generar_id()
        
        # Coordenadas aleatorias del cliente (entre 1 y 20 para x e y)
        self.coordenada_x = random.randint(1, 20)
        self.coordenada_y = random.randint(1, 20)

        # Inicialmente el destino no está asignado
        self.destino = None

    def generar_id(self):
        """Genera un ID aleatorio de 6 caracteres alfanuméricos."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def elegir_destino(self):
        """Permite al cliente elegir un destino (letra mayúscula) por consola."""
        destinos_validos = string.ascii_uppercase  # Todas las letras mayúsculas
        while True:
            destino = input("Introduce el destino del cliente (letra mayúscula): ").strip().upper()
            if destino in destinos_validos:
                self.destino = destino
                break
            else:
                print("Destino inválido. Debe ser una letra mayúscula.")

    def generar_cadena(self):
        """Genera la cadena de texto que contiene ID, coordenadas del cliente, y destino."""
        if self.destino:
            return (f"{self.id_cliente} Posicion: ({self.coordenada_x},{self.coordenada_y}) "
                    f"Destino: {self.destino}")
        else:
            return "Destino no asignado."

    def enviar_mensaje_kafka(self, cadena, ip_kafka, puerto_kafka, tema='destinos'):
        """Envía la cadena generada por el cliente a Kafka."""
        servidor_kafka = f"{ip_kafka}:{puerto_kafka}"
        producer = KafkaProducer(bootstrap_servers=servidor_kafka)
        producer.send(tema, cadena.encode('utf-8'))
        producer.flush()  # Asegura que el mensaje se envíe
        print(f"Cadena enviada a Kafka: {cadena}")

# Ejemplo de uso de la clase Cliente
def main():
    if len(sys.argv) != 3:
        print("Uso: python EC_Customer.py <IP_Kafka> <Puerto_Kafka>")
        sys.exit(1)

    ip_kafka = sys.argv[1]
    puerto_kafka = sys.argv[2]
    
    # Crear cliente
    cliente = Cliente()  
    print(f"Cliente creado con ID: {cliente.id_cliente}")
    print(f"Posición del cliente: ({cliente.coordenada_x}, {cliente.coordenada_y})")
    
    # El cliente elige su destino
    cliente.elegir_destino()
    
    # Generar y mostrar la cadena con los datos del cliente
    cadena = cliente.generar_cadena()
    print(f"Cadena generada: {cadena}")

    # Enviar la cadena a Kafka
    cliente.enviar_mensaje_kafka(cadena, ip_kafka, puerto_kafka)

if __name__ == "__main__":
    main()
