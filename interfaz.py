import pygame
import time

# Definir constantes para el mapa
WIDTH, HEIGHT = 800, 800
GRID_SIZE = 20
CELL_SIZE = WIDTH // GRID_SIZE
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

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

    def dibujar_cuadricula(self):
        """Dibuja la cuadrícula del mapa."""
        self.screen.fill(BLACK)
        for x in range(0, WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, WHITE, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, WHITE, (0, y), (WIDTH, y))

    def agregar_taxi(self, id_taxi, x, y):
        """Agrega o actualiza la posición de un taxi."""
        self.taxis[id_taxi] = (x, y)

    def remover_cliente(self, id_cliente):
        """Remueve un cliente del mapa."""
        if id_cliente in self.clientes:
            del self.clientes[id_cliente]

    def agregar_destino(self, letra, x, y):
        """Agrega un destino al mapa."""
        self.destinos[letra] = (x, y)

    def agregar_cliente(self, id_cliente, x, y):
        """Agrega o actualiza la posición de un cliente."""
        self.clientes[id_cliente] = (x, y)

    def actualizar_mapa(self):
        """Actualiza el mapa con taxis, clientes y destinos."""
        self.dibujar_cuadricula()

        # Dibujar taxis
        for id_taxi, (x, y) in self.taxis.items():
            pygame.draw.rect(self.screen, GREEN, (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            font = pygame.font.SysFont(None, 24)
            # Mostrar solo las dos primeras letras del ID del taxi
            text = font.render(id_taxi[:2], True, BLACK)
            self.screen.blit(text, (x * CELL_SIZE + CELL_SIZE // 4, y * CELL_SIZE + CELL_SIZE // 4))

        # Dibujar destinos
        for letra, (x, y) in self.destinos.items():
            pygame.draw.rect(self.screen, YELLOW, (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            font = pygame.font.SysFont(None, 24)
            text = font.render(letra, True, BLACK)
            self.screen.blit(text, (x * CELL_SIZE + CELL_SIZE // 4, y * CELL_SIZE + CELL_SIZE // 4))

        # Dibujar clientes
        for id_cliente, (x, y) in self.clientes.items():
            pygame.draw.rect(self.screen, BLUE, (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            font = pygame.font.SysFont(None, 24)
            # Mostrar solo las dos primeras letras del ID del cliente
            text = font.render(id_cliente[:2], True, BLACK)
            self.screen.blit(text, (x * CELL_SIZE + CELL_SIZE // 4, y * CELL_SIZE + CELL_SIZE // 4))

        pygame.display.update()

    def ejecutar(self):
        """Bucle principal para manejar el mapa y la ventana."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.actualizar_mapa()
            time.sleep(1)  # Redibujar el mapa cada segundo

        pygame.quit()

