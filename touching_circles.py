from __future__ import annotations
import math
import time
import pygame
import random
from dataclasses import dataclass, field
from typing import Iterable
import threading

FPS = 60
SHOW_COMPONENTS = True
ADD_TIMEOUT, REMOVE_TIMEOUT = 1 / 32, 1 / 6


pygame.init()
W, H = pygame.display.Info().current_w, pygame.display.Info().current_h
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Touching circles")
clock = pygame.time.Clock()
MAX_RADIUS = min(W, H) // 3

Color = tuple[int, int, int]
BG_COLOR: Color = (200, 220, 250)


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


def random_color() -> Color:
    return random.randint(120, 160), random.randint(100, 200), random.randint(160, 255)


@dataclass
class Circle:
    center: Pos
    radius: float
    color: Color = field(default_factory=random_color)
    instability: int = 0
    creation_time: float = field(init=False)
    maturity_time: float = field(init=False)
    render_radius: float = 0
    id: int = field(init=False, default_factory=lambda: random.randint(0, 1 << 63))

    def __post_init__(self):
        self.setup_time()

    def __repr__(self):
        return f"Circ({self.center}, {round(self.radius)})"

    def __hash__(self):
        return self.id

    def setup_time(self):
        self.creation_time = time.time()
        self.maturity_time = self.creation_time + 2 + 3 * random.random()


def add_circle(
    circles: Iterable[Circle], center: Pos, bounds: Pos, max_radius: float | None = None
) -> Circle | None:
    try:
        pixel = screen.get_at((round(center.x), round(center.y)))
        if pixel[:3] != BG_COLOR:
            return None
    except:
        pass
    max_radius = min(
        (center.x, center.y, bounds.x - center.x, bounds.y - center.y)
        + ((max_radius,) if max_radius else ())
    )
    closest: tuple[float, Circle | None] = (max_radius, None)
    for circle in circles:
        dist = abs(circle.center - center) - circle.radius
        if dist < 0:
            return None
        k = (dist, circle)
        closest = min(closest, k, key=lambda x: x[0])
    max_radius = closest[0]
    return (
        Circle(center, max_radius, closest[1].color)
        if SHOW_COMPONENTS and closest[1]
        else Circle(center, max_radius)
    )


USER_INSTABILITY = 69


class Circles(set[Circle]):
    def __iter__(self):
        return iter(tuple(super().__iter__()))


class State:
    circles: Circles = Circles()
    unstable_circles: Circles = Circles()
    last_added: float = time.time()
    last_removed = time.time()
    paused = False


def draw_int_circle(center: Pos, radius: float, color: Color, stroke: float = 0):
    rect = pygame.Rect(
        math.floor(center.x - radius),
        math.floor(center.y - radius),
        math.ceil(radius * 2),
        math.ceil(radius * 2),
    )
    pygame.draw.ellipse(screen, color, rect, math.ceil(stroke))


def iteration_modify_circles() -> None:
    now = time.time()
    if now - State.last_added > ADD_TIMEOUT:
        circle = None
        while not circle:
            circle = add_circle(
                State.circles,
                Pos(random.randint(0, W), random.randint(0, H)),
                Pos(W, H),
                MAX_RADIUS,
            )
        circle.instability = 1
        State.unstable_circles.add(circle)
        State.circles.add(circle)
        State.last_added += ADD_TIMEOUT
    if len(State.circles) > 100 and now - State.last_removed > REMOVE_TIMEOUT:
        stable_circles = tuple(filter(lambda c: c.instability == 0, State.circles))
        if stable_circles:
            circle = random.choice(stable_circles)
            circle.setup_time()
            circle.instability = -1
            State.unstable_circles.add(circle)
        State.last_removed += REMOVE_TIMEOUT


def update_unstable_radii() -> None:
    now = time.time()
    for circle in State.unstable_circles:
        if circle.instability == USER_INSTABILITY:
            circle.render_radius = circle.radius
            continue
        stage = min(
            1,
            (now - circle.creation_time)
            / (circle.maturity_time - circle.creation_time),
        )
        stage = (stage if circle.instability == 1 else 1 - stage) ** 0.5
        circle.render_radius = circle.radius * stage
        if now >= circle.maturity_time:
            if circle.instability == -1:
                State.circles.remove(circle)
            circle.instability = 0
    State.unstable_circles = Circles(
        {c for c in State.unstable_circles if c.instability}
    )


def thread_modify_circles():
    time.sleep(0.1)

    while True:
        start_time = time.time()
        if not State.paused:
            iteration_modify_circles()
        update_unstable_radii()
        time.sleep(
            max(0, min(ADD_TIMEOUT, REMOVE_TIMEOUT) - (time.time() - start_time))
        )


def find_circle(pos: Pos) -> Circle | None:
    for circle in State.circles:
        dist = abs(pos - circle.center)
        if dist < circle.radius:
            return circle
    return None


def pygame_loop():
    NONE_CIRCLE = Circle(Pos(0, 0), 0)
    user_circle: Circle = NONE_CIRCLE
    while True:
        user_circle.radius = abs(user_circle.center - Pos(*pygame.mouse.get_pos()))
        user_circle.maturity_time = time.time() + 10
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    user_circle = Circle(Pos(*event.pos), 0)
                    user_circle.instability = USER_INSTABILITY
                    State.circles.add(user_circle)
                    State.unstable_circles.add(user_circle)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == pygame.BUTTON_LEFT:
                    user_circle.instability = 1
                    user_circle.render_radius = user_circle.radius
                    user_circle.maturity_time = time.time()
                    user_circle = NONE_CIRCLE
                elif event.button == pygame.BUTTON_RIGHT:
                    circle = find_circle(Pos(*event.pos))
                    if circle is not None:
                        State.circles.remove(circle)
                        if circle in State.unstable_circles:
                            State.unstable_circles.remove(circle)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_r:
                    State.circles.clear()
                    State.unstable_circles.clear()
                    State.last_added = time.time()
                if event.key == pygame.K_p:
                    State.paused = not State.paused
                    State.last_added = time.time()

        screen.fill(BG_COLOR)
        for circle in State.circles:
            draw_int_circle(circle.center, circle.render_radius, circle.color)
            draw_int_circle(circle.center, circle.radius, circle.color, 1)

        pygame.display.flip()
        clock.tick(FPS)
        print(clock.get_fps(), len(State.circles), len(State.unstable_circles))


# launch threads
threading.Thread(target=thread_modify_circles, daemon=True).start()
pygame_loop()
