import pygame
import time
import requests
import os

# Definir constantes para el mapa
WIDTH, HEIGHT = 800, 800
GRID_SIZE = 20
CELL_SIZE = WIDTH // GRID_SIZE
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# Clase Mapa para manejar la visualización con Pygame
class Mapa:
    def __init__(self):
        # Inicializar Pygame y la ventana del mapa
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Mapa de Taxis")

        # Diccionarios para almacenar taxis, clientes y destinos
        self.taxis = {}
        self.destinos = {}
        self.clientes = {}

        # URL del servidor Node.js para recibir mapas
        self.api_url = "http://localhost:3001/map"

    def dibujar_cuadricula(self):
        """Dibuja la cuadrícula del mapa empezando en (1,1) y terminando en (20,20)."""
        self.screen.fill(BLACK)
        for x in range(CELL_SIZE, WIDTH + CELL_SIZE, CELL_SIZE):
            pygame.draw.line(self.screen, WHITE, (x, 0), (x, HEIGHT))
        for y in range(CELL_SIZE, HEIGHT + CELL_SIZE, CELL_SIZE):
            pygame.draw.line(self.screen, WHITE, (0, y), (WIDTH, y))

    def agregar_taxi(self, id_taxi, x, y,incidencia=False):
        """Agrega o actualiza la posición de un taxi."""
        self.taxis[id_taxi] = ((x, y), incidencia)

    def remover_cliente(self, id_cliente):
        """Remueve un cliente del mapa."""
        if id_cliente in self.clientes:
            del self.clientes[id_cliente]

    def agregar_destino(self, letra, x, y):
        """Agrega un destino al mapa."""
        if (x, y) not in self.destinos:
            self.destinos[(x, y)] = []
        self.destinos[(x, y)].append(letra)

    def agregar_cliente(self, id_cliente, x, y):
        """Agrega o actualiza la posición de un cliente."""
        self.clientes[id_cliente] = (x, y)

    def eliminar_cliente(self, id_cliente):
        """Elimina un cliente del mapa."""
        if id_cliente in self.clientes:
            del self.clientes[id_cliente]
            self.actualizar_mapa()  # Actualizar la visualización del mapa

    def actualizar_mapa(self):
        """Actualiza el mapa con taxis, clientes y destinos."""
        self.dibujar_cuadricula()

        # Dibujar taxis
        for id_taxi, ((x, y), incidencia) in self.taxis.items():
            color = GREEN
            if incidencia:
                color = RED

            pygame.draw.rect(self.screen, color, ((x-1) * CELL_SIZE, (y-1) * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            font = pygame.font.SysFont(None, 24)
            # Mostrar solo las dos primeras letras del ID del taxi
            text = font.render(id_taxi[:2], True, BLACK)
            self.screen.blit(text, ((x-1) * CELL_SIZE + CELL_SIZE // 4, (y-1) * CELL_SIZE + CELL_SIZE // 4))

        # Dibujar destinos
        for (x, y), letras in self.destinos.items():
            pygame.draw.rect(self.screen, YELLOW, ((x-1) * CELL_SIZE, (y-1) * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            font = pygame.font.SysFont(None, 24)
            text = font.render(','.join(letras), True, BLACK)
            self.screen.blit(text, ((x-1) * CELL_SIZE + CELL_SIZE // 4, (y-1) * CELL_SIZE + CELL_SIZE // 4))

        # Dibujar clientes
        for id_cliente, (x, y) in self.clientes.items():
            pygame.draw.rect(self.screen, BLUE, ((x-1) * CELL_SIZE, (y-1) * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            font = pygame.font.SysFont(None, 24)
            # Mostrar solo las dos primeras letras del ID del cliente
            text = font.render(id_cliente[:2], True, BLACK)
            self.screen.blit(text, ((x-1) * CELL_SIZE + CELL_SIZE // 4, (y-1) * CELL_SIZE + CELL_SIZE // 4))

        pygame.display.update()

    def capturar_mapa(self, output_path="mapa.png"):
        """Captura el mapa en formato PNG."""
        pygame.image.save(self.screen, output_path)
        return output_path

    def enviar_mapa(self):
        """Captura el mapa y lo envía al servidor."""
        try:
            # Capturar el mapa como un archivo PNG
            mapa_path = self.capturar_mapa()

            # Enviar la imagen al servidor
            with open(mapa_path, "rb") as file:
                response = requests.post(self.api_url, files={"map": file})

            if response.status_code == 200:
                print("Mapa enviado correctamente al servidor.")
            else:
                print(f"Error al enviar el mapa: {response.status_code} - {response.text}")

            # Eliminar el archivo temporal después del envío
            os.remove(mapa_path)
        except Exception as e:
            print(f"Error al capturar o enviar el mapa: {e}")

    def ejecutar(self):
        """Bucle principal para manejar el mapa y enviar capturas periódicamente."""
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.actualizar_mapa()  # Actualizar el contenido del mapa
            self.enviar_mapa()  # Capturar y enviar el mapa al servidor
            clock.tick(1)  # Actualizar cada segundo

        pygame.quit()
