import random
import string
import sys
import json
from kafka import KafkaProducer

class Cliente:
    def __init__(self):
        # Generar ID aleatorio para el cliente
        self.id_cliente = self.generar_id()
        
        # Coordenadas aleatorias del cliente (entre 1 y 20 para x e y)
        self.coordenada_x = random.randint(1, 20)
        self.coordenada_y = random.randint(1, 20)

    def generar_id(self):
        """Genera un ID aleatorio de 6 caracteres alfanuméricos."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def leer_fichero_destinos(self, archivo_destinos):
        """Lee el archivo JSON con los destinos del cliente."""
        try:
            with open(archivo_destinos, 'r') as file:
                data = json.load(file)
                destinos = [request['Id'] for request in data['Requests']]
                return destinos
        except FileNotFoundError:
            print(f"Error: El fichero '{archivo_destinos}' no se encuentra.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: El fichero '{archivo_destinos}' no tiene un formato JSON válido.")
            sys.exit(1)

    def generar_cadena(self, destinos):
        """Genera la cadena de texto que contiene ID, coordenadas y la lista de destinos del cliente."""
        return json.dumps({
            "id_cliente": self.id_cliente,
            "posicion": {"x": self.coordenada_x, "y": self.coordenada_y},
            "destinos": destinos
        })

    def enviar_mensaje_kafka(self, cadena, ip_kafka, puerto_kafka, tema='destinos'):
        """Envía la cadena generada por el cliente a Kafka."""
        servidor_kafka = f"{ip_kafka}:{puerto_kafka}"
        producer = KafkaProducer(bootstrap_servers=servidor_kafka)
        producer.send(tema, cadena.encode('utf-8'))
        producer.flush()  # Asegura que el mensaje se envíe
        print(f"Cadena enviada a Kafka: {cadena}")

# Ejemplo de uso de la clase Cliente
def main():
    if len(sys.argv) != 4:
        print("Uso: python EC_Customer.py <IP_Kafka> <Puerto_Kafka> <archivo_destinos>")
        sys.exit(1)

    ip_kafka = sys.argv[1]
    puerto_kafka = sys.argv[2]
    archivo_destinos = sys.argv[3]
    
    # Crear cliente
    cliente = Cliente()  
    print(f"Cliente creado con ID: {cliente.id_cliente}")
    print(f"Posición del cliente: ({cliente.coordenada_x}, {cliente.coordenada_y})")
    
    # Leer los destinos desde el archivo JSON
    destinos = cliente.leer_fichero_destinos(archivo_destinos)
    print(f"Destinos leídos: {destinos}")

    # Generar la cadena que contiene todos los destinos
    cadena = cliente.generar_cadena(destinos)
    print(f"Cadena generada: {cadena}")

    # Enviar la cadena a Kafka
    cliente.enviar_mensaje_kafka(cadena, ip_kafka, puerto_kafka)

if __name__ == "__main__":
    main()
