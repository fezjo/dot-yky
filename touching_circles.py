from __future__ import annotations
import math
import time
import pygame
import random
from dataclasses import dataclass, field
from typing import Iterable
import threading

SHOW_COMPONENTS = True


@dataclass
class Pos:
    x: float
    y: float

    def __add__(self, other: Pos) -> Pos:
        return Pos(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Pos) -> Pos:
        return Pos(self.x - other.x, self.y - other.y)

    def __abs__(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5

    def norm(self) -> float:
        return self.x**2 + self.y**2


def random_color() -> tuple[int, int, int]:
    return random.randint(120, 160), random.randint(100, 200), random.randint(160, 255)


@dataclass
class Circle:
    center: Pos
    radius: float
    color: tuple[int, int, int] = field(default_factory=random_color)
    instability: int = 0
    creation_time: float = field(init=False)
    maturity_time: float = field(init=False)
    render_radius: float = field(init=False)
    id: int = field(init=False, default_factory=lambda: random.randint(0, 2**32))

    def __post_init__(self):
        self.render_radius = self.radius
        self.setup_time()

    def __repr__(self):
        return f"Circ({self.center}, {round(self.radius)})"

    def __hash__(self):
        return hash((self.id, self.center.x, self.center.y))

    def setup_time(self):
        self.creation_time = time.time()
        self.maturity_time = self.creation_time + 2 + 3 * random.random()


def add_circle(
    circles: Iterable[Circle], center: Pos, bounds: Pos, max_radius: float = 100
) -> Circle | None:
    max_radius = min(
        max_radius, center.x, center.y, bounds.x - center.x, bounds.y - center.y
    )
    closest: tuple[float, Circle | None] = (max_radius, None)
    for circle in circles:
        dist = abs(circle.center - center) - circle.radius
        if dist < 0:
            return None
        closest = min(closest, (dist, circle), key=lambda x: x[0])
    max_radius = closest[0]
    return (
        Circle(center, max_radius, closest[1].color)
        if SHOW_COMPONENTS and closest[1]
        else Circle(center, max_radius)
    )


pygame.init()
W, H = pygame.display.Info().current_w, pygame.display.Info().current_h
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Touching circles")
clock = pygame.time.Clock()
FPS = 60

USER_INSTABILITY = 69
ADD_TIMEOUT, REMOVE_TIMEOUT = 1 / 32, 1 / 6
MAX_RADIUS = min(W, H) // 3
Circles = set[Circle]
circles: Circles = set()
unstable_circles: Circles = set()
last_added, last_removed = time.time(), time.time()
paused = False


def modify_circles():
    global circles, unstable_circles
    global last_added, last_removed, paused

    while True:
        now = time.time()
        if not paused:
            if now - last_added > ADD_TIMEOUT:
                circle = None
                while not circle:
                    circle = add_circle(
                        circles,
                        Pos(random.randint(0, W), random.randint(0, H)),
                        Pos(W, H),
                        MAX_RADIUS,
                    )
                circle.instability = 1
                unstable_circles.add(circle)
                circles.add(circle)
                last_added += ADD_TIMEOUT
            if len(circles) > 100 and now - last_removed > REMOVE_TIMEOUT:
                stable_circles = tuple(filter(lambda c: c.instability == 0, circles))
                if stable_circles:
                    circle = random.choice(stable_circles)
                    circle.setup_time()
                    circle.instability = -1
                    unstable_circles.add(circle)
                last_removed += REMOVE_TIMEOUT

        for circle in unstable_circles:
            stage = min(
                1,
                (now - circle.creation_time)
                / (circle.maturity_time - circle.creation_time),
            )
            circle.render_radius = circle.radius * (
                stage if circle.instability == 1 else 1 - stage
            )
            if circle.instability != USER_INSTABILITY and now >= circle.maturity_time:
                if circle.instability == -1:
                    circles.remove(circle)
                circle.instability = 0
        unstable_circles = {c for c in unstable_circles if c.instability}
        time.sleep(max(0, min(ADD_TIMEOUT, REMOVE_TIMEOUT) - (time.time() - now)))


def pygame_loop():
    global circles, unstable_circles
    global last_added, paused

    user_circle: Circle = Circle(Pos(0, 0), 0)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                user_circle = Circle(Pos(*event.pos), 0)
                user_circle.instability = USER_INSTABILITY
                circles.add(user_circle)
                unstable_circles.add(user_circle)
            elif event.type == pygame.MOUSEBUTTONUP:
                user_circle.instability = 0
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_r:
                    circles = set()
                    unstable_circles = set()
                    last_added = time.time()
                if event.key == pygame.K_p:
                    paused = not paused
                    last_added = time.time()

        user_circle.radius = abs(user_circle.center - Pos(*pygame.mouse.get_pos()))

        screen.fill((200, 220, 250))
        for circle in tuple(circles):
            r = circle.render_radius
            rect = pygame.Rect(
                math.floor(circle.center.x - r),
                math.floor(circle.center.y - r),
                math.ceil(r * 2),
                math.ceil(r * 2),
            )
            pygame.draw.ellipse(screen, circle.color, rect)

        pygame.display.flip()
        clock.tick(FPS)
        print(clock.get_fps(), len(circles), len(unstable_circles))


# launch threads

threading.Thread(target=modify_circles, daemon=True).start()
pygame_loop()
