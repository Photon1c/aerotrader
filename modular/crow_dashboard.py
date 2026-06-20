#!/usr/bin/env python3
import pygame
import random
import math
import sys
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

WIDTH, HEIGHT = 1280, 800
FPS = 60
DAY_LENGTH = 3600

BIOME_WATER_DEEP = 0
BIOME_WATER_SHALLOW = 1
BIOME_BEACH = 2
BIOME_GRASSLAND = 3
BIOME_FOREST = 4
BIOME_MOUNTAIN = 5
BIOME_SNOW = 6

BIOME_NAMES = [
    "Deep Water",
    "Shallow Water",
    "Beach",
    "Grassland",
    "Forest",
    "Mountain",
    "Snow",
]
BIOME_COLORS = [
    (10, 20, 60),
    (25, 60, 120),
    (180, 180, 100),
    (60, 140, 50),
    (30, 90, 30),
    (100, 80, 60),
    (200, 200, 210),
]

FOOD_COLORS = {
    "berry": (200, 60, 80),
    "insect": (140, 100, 60),
    "grain": (220, 200, 80),
    "seed": (180, 150, 70),
    "scrap": (130, 130, 130),
}
FOOD_TYPES = list(FOOD_COLORS.keys())

BIOME_FOOD = {
    BIOME_FOREST: ["berry", "insect"],
    BIOME_GRASSLAND: ["grain", "seed", "insect"],
    BIOME_BEACH: ["seed", "scrap"],
    BIOME_MOUNTAIN: ["scrap"],
    BIOME_WATER_SHALLOW: ["insect"],
}

SIGNAL_FOOD = "food"
SIGNAL_DANGER = "danger"
SIGNAL_ROOST = "roost"
SIGNAL_SCOUT = "scout"
SIGNAL_AFFILIATE = "affiliate"

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (140, 140, 140)
DARK_GRAY = (30, 30, 30)
GREEN = (60, 200, 80)
RED = (220, 60, 60)
AMBER = (240, 180, 40)
BLUE = (60, 140, 240)
CYAN = (60, 220, 220)


@dataclass
class Signal:
    kind: str
    from_id: int
    to_id: Optional[int]
    sx: float
    sy: float
    tx: float
    ty: float
    life: int = 40
    max_life: int = 40

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def progress(self) -> float:
        return 1.0 - self.life / self.max_life

    def color(self):
        return {
            SIGNAL_FOOD: (80, 220, 120),
            SIGNAL_DANGER: (220, 80, 80),
            SIGNAL_ROOST: (60, 140, 240),
            SIGNAL_SCOUT: (240, 190, 50),
            SIGNAL_AFFILIATE: (180, 100, 240),
        }.get(self.kind, (80, 80, 100))


class Terrain:
    OCTAVES = [
        (0.003, 1.3, 0.004, -0.7, 0.50),
        (0.008, 3.1, 0.007, 1.2, 0.25),
        (0.015, 0.5, 0.012, 2.8, 0.125),
        (0.030, 5.2, 0.025, 4.1, 0.062),
        (0.060, 2.4, 0.050, 0.3, 0.031),
    ]

    def __init__(self):
        self.heightmap = [[0.0] * WIDTH for _ in range(HEIGHT)]
        self.biomemap = [[0] * WIDTH for _ in range(HEIGHT)]
        self.surface = None
        self._build()

    def _height(self, x: int, y: int) -> float:
        h = 0.0
        for ax, px, ay, py, amp in self.OCTAVES:
            h += math.sin(x * ax + px) * math.cos(y * ay + py) * amp
        return max(-1.0, min(1.0, h))

    def _biome(self, h: float) -> int:
        if h < -0.35:
            return BIOME_WATER_DEEP
        if h < -0.15:
            return BIOME_WATER_SHALLOW
        if h < -0.05:
            return BIOME_BEACH
        if h < 0.35:
            return BIOME_GRASSLAND
        if h < 0.60:
            return BIOME_FOREST
        if h < 0.80:
            return BIOME_MOUNTAIN
        return BIOME_SNOW

    def _build(self):
        for y in range(HEIGHT):
            for x in range(WIDTH):
                h = self._height(x, y)
                self.heightmap[y][x] = h
                self.biomemap[y][x] = self._biome(h)

    def biome_at(self, x: float, y: float) -> int:
        ix, iy = int(x), int(y)
        if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
            return self.biomemap[iy][ix]
        return BIOME_GRASSLAND

    def height_at(self, x: float, y: float) -> float:
        ix, iy = int(x), int(y)
        if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
            return self.heightmap[iy][ix]
        return 0.0

    def is_walkable(self, x: float, y: float) -> bool:
        b = self.biome_at(x, y)
        return b not in (
            BIOME_WATER_DEEP,
            BIOME_WATER_SHALLOW,
            BIOME_MOUNTAIN,
            BIOME_SNOW,
        )

    def render(self) -> pygame.Surface:
        if self.surface:
            return self.surface
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            for x in range(WIDTH):
                b = self.biomemap[y][x]
                c = BIOME_COLORS[b]
                h = self.heightmap[y][x]
                shade = int((h + 1.0) * 20)
                c = (
                    max(0, min(255, c[0] + shade)),
                    max(0, min(255, c[1] + shade)),
                    max(0, min(255, c[2] + shade)),
                )
                surf.set_at((x, y), c)
        font = pygame.font.SysFont("monospace", 11)
        for b_id, name in enumerate(BIOME_NAMES):
            sx = 10
            sy = HEIGHT - 130 + b_id * 16
            pygame.draw.rect(surf, BIOME_COLORS[b_id], (sx, sy, 12, 12))
            pygame.draw.rect(surf, (200, 200, 200), (sx, sy, 12, 12), 1)
            t = font.render(name, True, (200, 200, 200))
            surf.blit(t, (sx + 16, sy))
        for i in range(0, WIDTH, 200):
            t = font.render(f"{i}px", True, (100, 100, 120))
            surf.blit(t, (i, HEIGHT - 18))
        for i in range(0, HEIGHT, 150):
            t = font.render(f"{i}px", True, (100, 100, 120))
            surf.blit(t, (4, i))
        self.surface = surf
        return surf

    def food_spawn_position(self, rng: random.Random) -> Tuple[float, float, str]:
        for _ in range(200):
            x = rng.uniform(20, WIDTH - 20)
            y = rng.uniform(20, HEIGHT - 40)
            b = self.biome_at(x, y)
            candidates = BIOME_FOOD.get(b, [])
            if candidates:
                return x, y, rng.choice(candidates)
        return rng.uniform(20, WIDTH - 20), rng.uniform(20, HEIGHT - 40), "seed"

    def perch_position(
        self, rng: random.Random
    ) -> Optional[Tuple[float, float, float]]:
        for _ in range(100):
            x = rng.uniform(50, WIDTH - 50)
            y = rng.uniform(100, HEIGHT - 60)
            b = self.biome_at(x, y)
            if b == BIOME_FOREST:
                return x, y, rng.uniform(60, 140)
            if b == BIOME_GRASSLAND and rng.random() < 0.3:
                return x, y, rng.uniform(40, 80)
        return None

    def spawn_position(self, rng: random.Random) -> Tuple[float, float]:
        for _ in range(100):
            x = rng.uniform(50, WIDTH - 50)
            y = rng.uniform(50, HEIGHT - 60)
            if self.is_walkable(x, y):
                return x, y
        return rng.uniform(50, WIDTH - 50), rng.uniform(50, HEIGHT - 60)


@dataclass
class GreekProfile:
    ticker: str = "?"
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    position_size: float = 1.0
    pnl_pct: float = 0.0
    is_option: bool = False


def random_greek_profile(ticker: str) -> GreekProfile:
    is_opt = random.random() < 0.4
    if is_opt:
        d = random.uniform(-1.0, 1.0)
        return GreekProfile(
            ticker=ticker,
            delta=d,
            gamma=random.uniform(0, 0.5) if abs(d) > 0.3 else random.uniform(0, 0.15),
            theta=random.uniform(-0.3, 0),
            vega=random.uniform(0, 0.8),
            rho=random.uniform(-0.1, 0.1),
            position_size=random.uniform(0.5, 3.0),
            pnl_pct=random.uniform(-15, 15),
            is_option=True,
        )
    return GreekProfile(
        ticker=ticker,
        delta=random.uniform(-0.8, 0.8),
        gamma=random.uniform(0, 0.1),
        theta=0,
        vega=0,
        rho=random.uniform(-0.05, 0.05),
        position_size=random.uniform(1, 5),
        pnl_pct=random.uniform(-8, 8),
        is_option=False,
    )


class Crow:
    _next_id = 0

    def __init__(
        self, x: float, y: float, mode: str, terrain: Terrain, parent_id: int = -1
    ):
        self.id = Crow._next_id
        Crow._next_id += 1
        self.x = x
        self.y = y
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)
        self.ax = self.ay = 0.0
        self.max_speed = random.uniform(2.5, 4.5)
        self.max_force = 0.08
        self.size = random.uniform(4, 7)
        self.mode = mode
        self.terrain = terrain
        self.wing_angle = random.uniform(-0.3, 0.3)
        self.is_scout = False
        self.scatter_timer = 0
        self.greeks = None
        self.color = random.choice([(40, 40, 50), (50, 45, 55), (35, 35, 45)])
        self.is_asleep = False
        self.roost_id = None
        self.affiliates: List[int] = []

        self.age = 0
        self.max_age = random.randint(18000, 36000)
        self.energy = random.uniform(0.6, 1.0)
        self.hunger = 0.0
        self.food_found = 0
        self.signals_sent = 0
        self.signals_received = 0
        self.signal_queue: List[Signal] = []
        self.emit_cooldown = 0
        self.caw_timer = 0
        self.caw_cooldown = random.randint(120, 400)
        self.mating_cooldown = 0
        self.parent_id = parent_id

        if mode == "financial":
            TICKERS = [
                "SPY",
                "AAPL",
                "MSFT",
                "TSLA",
                "AMZN",
                "GOOGL",
                "META",
                "NVDA",
                "AMD",
                "PLTR",
                "COIN",
                "QQQ",
                "IWM",
                "GLD",
                "HIMS",
                "NOC",
                "LMT",
                "BA",
                "CAT",
                "XOM",
            ]
            t = TICKERS[self.id % len(TICKERS)]
            self.greeks = random_greek_profile(t)
            self.max_speed = random.uniform(1.5, 4.0) * (
                1.0 + abs(self.greeks.delta) * 0.5
            )
            self.size = 4 + self.greeks.position_size * 0.8
            self.color = self._pnl_color()

    def _pnl_color(self) -> Tuple[int, int, int]:
        if self.mode != "financial" or not self.greeks:
            return (40, 40, 50)
        p = self.greeks.pnl_pct
        intensity = min(abs(p) / 15.0, 1.0)
        if p >= 0:
            return (
                int(40 + 40 * intensity),
                int(40 + 180 * intensity),
                int(50 + 70 * intensity),
            )
        return (
            int(40 + 180 * intensity),
            int(40 + 40 * intensity),
            int(45 + 35 * intensity),
        )

    def apply_force(self, fx: float, fy: float):
        self.ax += fx
        self.ay += fy

    def seek(self, tx: float, ty: float, weight: float = 1.0):
        dx = tx - self.x
        dy = ty - self.y
        d = math.hypot(dx, dy)
        if d == 0:
            return
        desired = (dx / d * self.max_speed, dy / d * self.max_speed)
        self.apply_force(
            (desired[0] - self.vx) * weight * self.max_force,
            (desired[1] - self.vy) * weight * self.max_force,
        )

    def separate(self, others: List["Crow"], radius: float = 30.0, weight: float = 1.5):
        fx = fy = count = 0
        for o in others:
            if o is self:
                continue
            dx = self.x - o.x
            dy = self.y - o.y
            d = math.hypot(dx, dy)
            if 0 < d < radius:
                fx += dx / d / d
                fy += dy / d / d
                count += 1
        if count == 0:
            return
        fx /= count
        fy /= count
        d = math.hypot(fx, fy)
        if d == 0:
            return
        fx = fx / d * self.max_speed - self.vx
        fy = fy / d * self.max_speed - self.vy
        self.apply_force(fx * weight * self.max_force, fy * weight * self.max_force)

    def align(self, others: List["Crow"], radius: float = 60.0, weight: float = 1.0):
        fx = fy = count = 0
        for o in others:
            if o is self:
                continue
            d = math.hypot(self.x - o.x, self.y - o.y)
            if 0 < d < radius:
                fx += o.vx
                fy += o.vy
                count += 1
        if count == 0:
            return
        self.apply_force(
            (fx / count - self.vx) * weight * self.max_force,
            (fy / count - self.vy) * weight * self.max_force,
        )

    def cohere(self, others: List["Crow"], radius: float = 80.0, weight: float = 0.8):
        cx = cy = count = 0
        for o in others:
            if o is self:
                continue
            d = math.hypot(self.x - o.x, self.y - o.y)
            if 0 < d < radius:
                cx += o.x
                cy += o.y
                count += 1
        if count > 0:
            self.seek(cx / count, cy / count, weight)

    def flee(self, tx: float, ty: float, radius: float = 80.0, weight: float = 2.0):
        d = math.hypot(self.x - tx, self.y - ty)
        if 0 < d < radius:
            self.seek(
                self.x + (self.x - tx) * 10,
                self.y + (self.y - ty) * 10,
                weight * (1 - d / radius),
            )

    def edges(self):
        margin = 40
        if self.x < margin:
            self.apply_force(self.max_force * (1 - self.x / margin), 0)
        elif self.x > WIDTH - margin:
            self.apply_force(-self.max_force * (1 - (WIDTH - self.x) / margin), 0)
        if self.y < margin:
            self.apply_force(0, self.max_force * (1 - self.y / margin))
        elif self.y > HEIGHT - margin:
            self.apply_force(0, -self.max_force * (1 - (HEIGHT - self.y) / margin))

    def emit_signal(self, kind: str, others: List["Crow"], radius: float = 150.0):
        self.emit_cooldown = 30 + random.randint(0, 60)
        for o in others:
            if o is self:
                continue
            if math.hypot(self.x - o.x, self.y - o.y) < radius:
                self.signal_queue.append(
                    Signal(kind, self.id, o.id, self.x, self.y, o.x, o.y)
                )
                o.signals_received += 1
        self.signals_sent += 1

    def update(self):
        if self.emit_cooldown > 0:
            self.emit_cooldown -= 1
        self.signal_queue = [s for s in self.signal_queue if s.alive]
        for s in self.signal_queue:
            s.life -= 1
        self.age += 1
        if self.mating_cooldown > 0:
            self.mating_cooldown -= 1

        if self.is_asleep:
            self.vx *= 0.9
            self.vy *= 0.9
            self.energy = min(1.0, self.energy + 0.003)
            self.hunger = max(0.0, self.hunger - 0.001)
        else:
            self.energy = max(0.0, self.energy - 0.0003)
            self.hunger = min(1.0, self.hunger + 0.0004)

        self.vx += self.ax
        self.vy += self.ay
        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_speed:
            self.vx = self.vx / speed * self.max_speed
            self.vy = self.vy / speed * self.max_speed
        self.x += self.vx
        self.y += self.vy
        self.ax = self.ay = 0.0
        self.wing_angle = math.sin(pygame.time.get_ticks() * 0.005 + self.id) * 0.3
        self.caw_timer += 1

        b = self.terrain.biome_at(self.x, self.y)
        if b in (BIOME_WATER_DEEP, BIOME_WATER_SHALLOW) and not self.is_asleep:
            self.apply_force(0, -self.max_force * 2)

        if self.greeks and self.mode == "financial":
            self.greeks.pnl_pct += random.gauss(0, 0.05)
            self.greeks.pnl_pct = max(-30, min(30, self.greeks.pnl_pct))
            self.color = self._pnl_color()

    @property
    def is_dead(self) -> bool:
        return self.energy <= 0.0 or self.age >= self.max_age or self.hunger >= 1.0

    def draw(self, screen: pygame.Surface, signals: List[Signal]):
        for s in self.signal_queue:
            Draw.signal_line(screen, s)

        if self.is_asleep:
            pygame.draw.circle(
                screen, (20, 20, 35), (int(self.x), int(self.y)), int(self.size * 1.8)
            )
            pygame.draw.circle(
                screen, GRAY, (int(self.x), int(self.y)), int(self.size * 1.8), 1
            )
            z = pygame.font.SysFont("monospace", 12).render("z", True, GRAY)
            screen.blit(z, (self.x + 8, self.y - 12))
            return

        angle = math.atan2(self.vy, self.vx)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        s = self.size
        wa = self.wing_angle

        body = (int(self.x), int(self.y))
        tail = (
            int(self.x - cos_a * s * 1.8 + sin_a * s * 0.1),
            int(self.y - sin_a * s * 1.8 - cos_a * s * 0.1),
        )
        beak = (int(self.x + cos_a * s * 1.2), int(self.y + sin_a * s * 1.2))
        wing_l = (
            int(self.x - cos_a * s * 0.3 + sin_a * s * (1 + wa)),
            int(self.y - sin_a * s * 0.3 - cos_a * s * (1 + wa)),
        )
        wing_r = (
            int(self.x - cos_a * s * 0.3 - sin_a * s * (1 + wa)),
            int(self.y - sin_a * s * 0.3 + cos_a * s * (1 + wa)),
        )

        dim = 0.6 + 0.4 * self.energy
        c = tuple(int(ch * dim) for ch in self.color)
        pygame.draw.polygon(screen, c, [body, tail, wing_l, wing_r], 0)
        pygame.draw.circle(
            screen, WHITE if self.is_scout else c, body, max(2, int(s * 0.4))
        )
        pygame.draw.circle(screen, BLACK, body, max(1, int(s * 0.2)))
        eye_c = AMBER if self.energy < 0.25 else WHITE
        pygame.draw.circle(screen, eye_c, beak, max(1, int(s * 0.3)))

        ew = int(s * 2)
        eh = 2
        ex = self.x - ew / 2
        ey = self.y - s - 6
        pygame.draw.rect(screen, DARK_GRAY, (ex, ey, ew, eh))
        pygame.draw.rect(
            screen,
            GREEN if self.energy > 0.5 else AMBER if self.energy > 0.2 else RED,
            (ex, ey, int(ew * self.energy), eh),
        )

        if self.greeks and self.mode == "financial":
            lbl = pygame.font.SysFont("monospace", 10).render(
                self.greeks.ticker, True, WHITE
            )
            screen.blit(lbl, (self.x - 12, self.y - s - 14))

        if self.parent_id >= 0:
            par = pygame.font.SysFont("monospace", 8).render(
                f"c{self.parent_id}", True, GRAY
            )
            screen.blit(par, (self.x + 6, self.y - s - 8))

        if self.caw_timer > self.caw_cooldown:
            self.caw_timer = 0
            self.caw_cooldown = random.randint(180, 600)
            txt = pygame.font.SysFont("monospace", 16).render(
                random.choice(["CAW!", "caw", "CaW!", "!CAW"]),
                True,
                AMBER if self.is_scout else GRAY,
            )
            screen.blit(txt, (self.x + 10, self.y - 15))


class Draw:
    @staticmethod
    def signal_line(screen: pygame.Surface, s: Signal):
        if not s.alive:
            return
        p = s.progress
        cx = s.sx + (s.tx - s.sx) * p
        cy = s.sy + (s.ty - s.sy) * p
        c = s.color()
        alpha = int(180 * (1 - p))
        for off in (-4, 0, 4):
            for i in range(3):
                t0 = i / 3
                t1 = (i + 0.5) / 3
                p0x = cx + (s.tx - s.sx) * 0.15 * (t0 - 0.5) + off
                p0y = cy + (s.ty - s.sy) * 0.15 * (t0 - 0.5) + off
                p1x = cx + (s.tx - s.sx) * 0.15 * (t1 - 0.5) + off
                p1y = cy + (s.ty - s.sy) * 0.15 * (t1 - 0.5) + off
                try:
                    pygame.draw.line(
                        screen, c, (int(p0x), int(p0y)), (int(p1x), int(p1y)), 1
                    )
                except Exception:
                    pass

    @staticmethod
    def pressure_heatmap(screen: pygame.Surface, grid: List[List[float]]):
        cw = WIDTH // len(grid[0])
        ch = HEIGHT // len(grid)
        for gy, row in enumerate(grid):
            for gx, val in enumerate(row):
                if val < 0.02:
                    continue
                intensity = min(val * 2, 1)
                surf = pygame.Surface((cw, ch))
                surf.set_alpha(int(35 * intensity))
                surf.fill(
                    (
                        int(200 * intensity),
                        int(100 * (1 - intensity)),
                        int(200 * (1 - intensity)),
                    )
                )
                screen.blit(surf, (gx * cw, gy * ch))

    @staticmethod
    def convex_hull(points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        pts = sorted(set(points))
        if len(pts) <= 1:
            return pts

        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        lower = []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        upper = []
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        return lower[:-1] + upper[:-1]


@dataclass
class FoodSource:
    x: float
    y: float
    amount: float = 1.0
    kind: str = "berry"
    regrow_timer: int = 0
    depleted: bool = False

    def draw(self, screen: pygame.Surface):
        if self.depleted:
            if self.regrow_timer > 0:
                pygame.draw.circle(screen, (35, 35, 35), (int(self.x), int(self.y)), 2)
            return
        bc = FOOD_COLORS.get(self.kind, (80, 220, 120))
        r = max(2, int(4 * self.amount))
        bright = int(200 + 55 * self.amount)
        c = (min(bc[0] + 30, bright), min(bc[1] + 30, bright), min(bc[2] + 30, bright))
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), r)
        pygame.draw.circle(screen, (40, 40, 40), (int(self.x), int(self.y)), r, 1)


@dataclass
class Perch:
    x: float
    y: float
    height: float

    def draw(self, screen: pygame.Surface):
        pygame.draw.line(
            screen,
            (60, 40, 20),
            (int(self.x), int(self.y)),
            (int(self.x), int(self.y - self.height)),
            3,
        )
        for dx in (-10, 0, 10):
            bx = self.x + dx
            by = self.y - self.height
            pygame.draw.line(
                screen,
                (50, 80, 30),
                (int(bx), int(by)),
                (int(bx + dx * 0.5), int(by + 10)),
                2,
            )
        pygame.draw.circle(
            screen, (40, 60, 20), (int(self.x), int(self.y - self.height - 4)), 4
        )


@dataclass
class RoostCluster:
    id: int
    perch_idx: int
    members: List[int]
    center_x: float = 0.0
    center_y: float = 0.0

    def update_center(self, crows: List[Crow]):
        xs = [crows[m].x for m in self.members if m < len(crows)]
        ys = [crows[m].y for m in self.members if m < len(crows)]
        if xs:
            self.center_x = sum(xs) / len(xs)
            self.center_y = sum(ys) / len(ys)

    def draw(self, screen: pygame.Surface, crows: List[Crow]):
        if len(self.members) < 2:
            return
        pts = [
            (int(crows[m].x), int(crows[m].y))
            for m in self.members
            if m < len(crows) and crows[m].is_asleep
        ]
        if len(pts) < 2:
            return
        hull = Draw.convex_hull(pts) if len(pts) > 2 else pts
        if len(hull) > 2:
            pygame.draw.polygon(screen, (30, 30, 60), hull, 1)
        cx, cy = int(self.center_x), int(self.center_y)
        screen.blit(
            pygame.font.SysFont("monospace", 10).render(
                f"R{self.id}:{len(self.members)}", True, BLUE
            ),
            (cx - 15, cy - 10),
        )


class Ecosystem:
    def __init__(self, mode: str):
        self.mode = mode
        self.rng = random.Random()
        self.terrain = Terrain()
        self.crows: List[Crow] = []
        self.foods: List[FoodSource] = []
        self.perches: List[Perch] = []
        self.roost_clusters: List[RoostCluster] = []
        self.signals: List[Signal] = []
        self.tick = 0
        self.time_of_day = 0.25
        self.day_count = 0
        self.density_grid = [[0.0] * 16 for _ in range(10)]
        self.night_factor = 0.0
        self.birth_count = 0
        self.death_count = 0
        Crow._next_id = 0

        for _ in range(5):
            pos = self.terrain.perch_position(self.rng)
            if pos:
                self.perches.append(Perch(*pos))
        for i in range(max(6, len(self.perches))):
            self.roost_clusters.append(
                RoostCluster(i, i if i < len(self.perches) else 0, [])
            )

        starting_crows = 30
        for _ in range(starting_crows):
            x, y = self.terrain.spawn_position(self.rng)
            c = Crow(x, y, mode, self.terrain)
            self.crows.append(c)

        for _ in range(25):
            pos = self.terrain.food_spawn_position(self.rng)
            if pos:
                self.foods.append(
                    FoodSource(pos[0], pos[1], random.uniform(0.5, 1.5), pos[2])
                )

        if mode == "natural":
            scout_count = max(2, len(self.crows) // 8)
            for i in range(scout_count):
                self.crows[i].is_scout = True

        if mode == "financial":
            self.crows.sort(
                key=lambda c: abs(c.greeks.delta) if c.greeks else 0, reverse=True
            )

    def update(self):
        self.tick += 1
        self.time_of_day = (self.tick % DAY_LENGTH) / DAY_LENGTH
        self.night_factor = math.sin(self.time_of_day * 2 * math.pi)
        if self.tick % DAY_LENGTH == 0:
            self.day_count += 1

        self._update_density()

        if self.mode == "natural":
            self._update_natural()
        else:
            self._update_financial()

        for c in self.crows:
            c.update()
            if not c.is_asleep:
                c.edges()

        self._update_roosts()
        self.signals = [s for s in self.signals if s.alive]
        for s in self.signals:
            s.life -= 1
        self._handle_birth_death()

        if self.mode == "natural":
            if self.tick % 90 == 0:
                fx, fy, fkind = self.terrain.food_spawn_position(self.rng)
                self.foods.append(FoodSource(fx, fy, random.uniform(0.3, 1.0), fkind))

        for f in self.foods:
            if f.depleted:
                f.regrow_timer -= 1
                if f.regrow_timer <= 0:
                    f.amount = random.uniform(0.3, 1.0)
                    f.depleted = False
                    b = self.terrain.biome_at(f.x, f.y)
                    candidates = BIOME_FOOD.get(b, ["seed"])
                    f.kind = self.rng.choice(candidates)

    def _update_density(self):
        for gy in range(len(self.density_grid)):
            for gx in range(len(self.density_grid[0])):
                self.density_grid[gy][gx] *= 0.95
        for c in self.crows:
            if c.is_asleep or c.is_dead:
                continue
            gx = int(c.x / WIDTH * len(self.density_grid[0]))
            gy = int(c.y / HEIGHT * len(self.density_grid))
            gx = max(0, min(len(self.density_grid[0]) - 1, gx))
            gy = max(0, min(len(self.density_grid) - 1, gy))
            self.density_grid[gy][gx] = min(1.0, self.density_grid[gy][gx] + 0.05)

    def _update_roosts(self):
        for rc in self.roost_clusters:
            rc.members.clear()
        for i, c in enumerate(self.crows):
            if (
                c.is_asleep
                and c.roost_id is not None
                and c.roost_id < len(self.roost_clusters)
            ):
                self.roost_clusters[c.roost_id].members.append(i)
        for rc in self.roost_clusters:
            rc.update_center(self.crows)

    def _handle_birth_death(self):
        dead = [c for c in self.crows if c.is_dead]
        for c in dead:
            self.crows.remove(c)
            self.death_count += 1

        if self.mode != "natural":
            return

        food_density = sum(1 for f in self.foods if not f.depleted) / max(
            len(self.crows), 1
        )
        if food_density < 0.3:
            return

        mating_pairs = []
        for i, a in enumerate(self.crows):
            if a.is_asleep or a.mating_cooldown > 0 or a.energy < 0.6:
                continue
            for b in self.crows[i + 1 :]:
                if b.is_asleep or b.mating_cooldown > 0 or b.energy < 0.6:
                    continue
                if math.hypot(a.x - b.x, a.y - b.y) < 35 and self.rng.random() < 0.001:
                    mating_pairs.append((a, b))
                    a.mating_cooldown = 600 + self.rng.randint(0, 300)
                    b.mating_cooldown = 600 + self.rng.randint(0, 300)

        for parent_a, parent_b in mating_pairs:
            x, y = self.terrain.spawn_position(self.rng)
            if x is None:
                continue
            chick = Crow(x, y, self.mode, self.terrain, parent_id=parent_a.id)
            chick.max_speed = (
                (parent_a.max_speed + parent_b.max_speed) / 2 * random.uniform(0.9, 1.1)
            )
            chick.size = (parent_a.size + parent_b.size) / 2 * random.uniform(0.8, 1.2)
            chick.energy = 0.8
            if self.rng.random() < 0.3:
                chick.is_scout = parent_a.is_scout or parent_b.is_scout
            self.crows.append(chick)
            self.birth_count += 1

        max_crows = 20 + int(sum(1 for f in self.foods if not f.depleted) * 1.5)
        if len(self.crows) > max_crows:
            sorted_crows = sorted(self.crows, key=lambda c: c.energy)
            for c in sorted_crows[: max(0, len(self.crows) - max_crows)]:
                c.energy = -0.01

    def _is_night(self) -> bool:
        return self.night_factor < -0.3

    def _is_dawn(self) -> bool:
        return -0.3 <= self.night_factor < 0.0

    def _is_dusk(self) -> bool:
        return 0.0 < self.night_factor <= 0.3

    def _is_day(self) -> bool:
        return self.night_factor > 0.3

    def _update_natural(self):
        is_night = self._is_night()
        for c in self.crows:
            if c.is_dead:
                continue
            if is_night:
                c.is_asleep = c.energy < 0.85
                if c.is_asleep:
                    if c.roost_id is None:
                        c.roost_id = min(
                            range(len(self.perches)),
                            key=lambda i: math.hypot(
                                c.x - self.perches[i].x, c.y - self.perches[i].y
                            ),
                        )
                    p = (
                        self.perches[c.roost_id]
                        if c.roost_id < len(self.perches)
                        else self.perches[0]
                    )
                    c.seek(p.x, p.y - p.height * 0.3, 1.2)
                    c.max_speed = 1.5
                continue
            else:
                c.is_asleep = False
                c.max_speed = random.uniform(2.5, 4.5)

            c.separate(self.crows, 25, 1.8)
            c.align(self.crows, 60, 1.0)
            c.cohere(self.crows, 80, 0.6)

            if c.is_scout:
                c.scatter_timer += 1
                if c.scatter_timer > 300:
                    c.is_scout = False
                    c.scatter_timer = 0
                    pool = [x for x in self.crows if not x.is_scout and not x.is_dead]
                    if pool:
                        random.choice(pool).is_scout = True
                if random.random() < 0.008:
                    c.seek(
                        random.uniform(50, WIDTH - 50),
                        random.uniform(50, HEIGHT - 50),
                        1.5,
                    )
                if c.emit_cooldown == 0 and c.signals_sent < 10:
                    c.emit_signal(SIGNAL_SCOUT, self.crows, 200)
                    self.signals.extend(c.signal_queue[-3:])
                continue

            if c.hunger > 0.3 or c.energy < 0.5:
                active = [f for f in self.foods if not f.depleted]
                if active:
                    closest = min(
                        active, key=lambda f: math.hypot(c.x - f.x, c.y - f.y)
                    )
                    d = math.hypot(c.x - closest.x, c.y - closest.y)
                    if d < 300:
                        c.seek(closest.x, closest.y, 1.2 if d < 80 else 0.6)
                        if d < 12:
                            closest.amount -= 0.03
                            c.energy = min(1.0, c.energy + 0.12)
                            c.hunger = max(0.0, c.hunger - 0.15)
                            c.food_found += 1
                            if closest.amount <= 0:
                                closest.depleted = True
                                closest.regrow_timer = 400 + random.randint(0, 300)
                            if c.emit_cooldown == 0 and c.signals_sent < 20:
                                c.emit_signal(SIGNAL_FOOD, self.crows, 120)
                                self.signals.extend(c.signal_queue[-2:])

            for p in self.perches:
                d = math.hypot(c.x - p.x, c.y - p.y)
                if d < 60:
                    c.seek(p.x, p.y - p.height * 0.3, 0.2)
                    if d < 15:
                        c.vx *= 0.95
                        c.vy *= 0.95

            if random.random() < 0.004:
                c.seek(
                    random.uniform(50, WIDTH - 50), random.uniform(50, HEIGHT - 50), 0.8
                )

            if c.energy > 0.7 and random.random() < 0.002:
                nearby = [
                    o
                    for o in self.crows
                    if o is not c
                    and not o.is_dead
                    and math.hypot(c.x - o.x, c.y - o.y) < 100
                ]
                if nearby and c.emit_cooldown == 0:
                    c.emit_signal(SIGNAL_AFFILIATE, nearby[:3], 100)
                    self.signals.extend(c.signal_queue[-1:])

    def _update_financial(self):
        ms = abs(sum(c.greeks.delta for c in self.crows if c.greeks)) / max(
            len(self.crows), 1
        )
        for c in self.crows:
            if c.is_dead:
                continue
            c.is_asleep = False
            g = c.greeks
            if not g:
                continue
            c.separate(
                self.crows, 25 + abs(g.delta) * 10, max(0.5, 1.8 - abs(g.delta) * 0.5)
            )
            c.align(self.crows, 60 + abs(g.delta) * 20, 0.6 + abs(g.delta) * 0.4)
            c.cohere(self.crows, 80, 0.4 + abs(g.delta) * 0.3)
            c.apply_force(g.delta * 0.5, (g.gamma * 2 - 1) * 0.15)
            c.apply_force(-c.vx * abs(g.theta) * 0.05, -c.vy * abs(g.theta) * 0.05)
            if g.vega > 0:
                c.apply_force(
                    random.gauss(0, g.vega * 0.3), random.gauss(0, g.vega * 0.3)
                )
            c.apply_force(0, g.rho * 0.1)
            if g.theta < -0.1:
                cx = sum(o.x for o in self.crows if o is not c) / max(
                    len(self.crows) - 1, 1
                )
                cy = sum(o.y for o in self.crows if o is not c) / max(
                    len(self.crows) - 1, 1
                )
                c.seek(cx, cy, abs(g.theta) * 0.5)
            for attr in ["delta", "gamma", "theta", "vega"]:
                v = getattr(g, attr)
                v += random.gauss(0, 0.005)
                if attr == "delta":
                    v = max(-1, min(1, v))
                elif attr == "gamma":
                    v = max(0, min(1, v))
                elif attr == "theta":
                    v = max(-0.5, min(0, v))
                elif attr == "vega":
                    v = max(0, min(1, v))
                setattr(g, attr, v)
            scale = 1 + ms * 0.3
            c.max_speed = (1.5 + abs(g.delta) * 2) * scale
            g.pnl_pct += g.delta * 0.01 + random.gauss(0, 0.03)
            g.pnl_pct = max(-30, min(30, g.pnl_pct))
            c.color = c._pnl_color()
        for i, c in enumerate(self.crows):
            c.is_scout = i < max(1, int(len(self.crows) * 0.1))

    def draw(self, screen: pygame.Surface):
        screen.blit(self.terrain.render(), (0, 0))
        Draw.pressure_heatmap(screen, self.density_grid)
        for p in self.perches:
            p.draw(screen)
        for f in self.foods:
            f.draw(screen)
        for rc in self.roost_clusters:
            rc.draw(screen, self.crows)
        for s in self.signals:
            Draw.signal_line(screen, s)
        for c in self.crows:
            c.draw(screen, self.signals)


class Dashboard:
    def __init__(self, mode: str):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(f"Crow Ecosystem — {mode.title()} Mode")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 13)
        self.title_font = pygame.font.SysFont("monospace", 18)
        self.mode = mode
        self.eco = Ecosystem(mode)
        self.running = True
        self.paused = False
        self.selected_crow: Optional[Crow] = None
        self.show_info = True
        self.show_roost_panel = False
        self.hovered_crow: Optional[Crow] = None

    def handle_events(self):
        mx, my = pygame.mouse.get_pos()
        self.hovered_crow = None
        for c in self.eco.crows:
            if math.hypot(c.x - mx, c.y - my) < 15:
                self.hovered_crow = c
                break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_i:
                    self.show_info = not self.show_info
                elif event.key == pygame.K_r:
                    self.eco = Ecosystem(self.mode)
                elif event.key == pygame.K_c:
                    self.show_roost_panel = not self.show_roost_panel
            elif event.type == pygame.MOUSEBUTTONDOWN:
                closest = (
                    min(self.eco.crows, key=lambda c: math.hypot(c.x - mx, c.y - my))
                    if self.eco.crows
                    else None
                )
                if closest and math.hypot(closest.x - mx, closest.y - my) < 20:
                    self.selected_crow = (
                        closest if self.selected_crow is not closest else None
                    )
                else:
                    self.selected_crow = None

    def draw_hud(self):
        overlay = pygame.Surface((WIDTH, 36))
        overlay.set_alpha(170)
        overlay.fill(DARK_GRAY)
        self.screen.blit(overlay, (0, 0))

        hour = int(self.eco.time_of_day * 24)
        minute = int((self.eco.time_of_day * 24 - hour) * 60)
        phase = (
            "NIGHT"
            if self.eco._is_night()
            else "DAWN"
            if self.eco._is_dawn()
            else "DUSK"
            if self.eco._is_dusk()
            else "DAY"
        )

        parts = [
            f"MODE: {self.mode.upper()}",
            " [PAUSED]" if self.paused else "",
            f"Crows: {len(self.eco.crows)}",
            f"Births: {self.eco.birth_count} Deaths: {self.eco.death_count}",
            f"Food: {sum(1 for f in self.eco.foods if not f.depleted)}"
            if self.mode == "natural"
            else "",
            f"Day {self.eco.day_count}",
            f"Tick: {self.eco.tick}",
            f"| {hour:02d}:{minute:02d} {phase}",
        ]
        x = 12
        for s in parts:
            if not s:
                continue
            t = self.font.render(s, True, AMBER if "PAUSED" in s else WHITE)
            self.screen.blit(t, (x, 10))
            x += t.get_width() + 12

        hints = "[SPC] pause [I] info [C] roosts [R] reset [ESC] quit"
        t = self.font.render(hints, True, GRAY)
        self.screen.blit(t, (WIDTH - t.get_width() - 12, 10))

        if self.eco._is_night():
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(int(min(100, abs(self.eco.night_factor) * 140)))
            overlay.fill((10, 5, 30))
            self.screen.blit(overlay, (0, 0))

    def draw_info_panel(self):
        if not self.show_info:
            return
        pw, ph, px, py = 280, HEIGHT - 50, WIDTH - 290, 42
        overlay = pygame.Surface((pw, ph))
        overlay.set_alpha(200)
        overlay.fill(DARK_GRAY)
        self.screen.blit(overlay, (px, py))
        pygame.draw.rect(self.screen, GRAY, (px, py, pw, ph), 1)

        y = py + 12
        c = self.selected_crow

        if c and self.mode == "financial" and c.greeks:
            g = c.greeks
            self.screen.blit(
                self.title_font.render(f"  {g.ticker}", True, AMBER), (px + 10, y)
            )
            y += 28
            for line in [
                f"Delta:   {g.delta:+.3f}",
                f"Gamma:   {g.gamma:.3f}",
                f"Theta:   {g.theta:+.3f}",
                f"Vega:    {g.vega:.3f}",
                f"Rho:     {g.rho:+.3f}",
                f"Type:    {'OPTION' if g.is_option else 'EQUITY'}",
                f"Size:    {g.position_size:.1f}x",
                f"P&L:     {g.pnl_pct:+.1f}%",
            ]:
                col = (
                    GREEN
                    if line.startswith("P&L:") and g.pnl_pct >= 0
                    else RED
                    if line.startswith("P&L:")
                    else WHITE
                )
                self.screen.blit(self.font.render(line, True, col), (px + 15, y))
                y += 20
            y += 8
            ms = sum(abs(c2.greeks.delta) for c2 in self.eco.crows if c2.greeks) / max(
                len(self.eco.crows), 1
            )
            self.screen.blit(
                self.font.render(f"Market Sync: {ms:.3f}", True, CYAN), (px + 15, y)
            )
            y += 20
        elif c and self.mode == "natural":
            role = "SCOUT" if c.is_scout else "FORAGER"
            spd = math.hypot(c.vx, c.vy)
            self.screen.blit(
                self.title_font.render(f"  Crow #{c.id}", True, AMBER), (px + 10, y)
            )
            y += 28
            for line in [
                f"Age:     {c.age} / {c.max_age}",
                f"Role:    {role}",
                f"Energy:  {c.energy:.2f}",
                f"Hunger:  {c.hunger:.2f}",
                f"Speed:   {spd:.1f}",
                f"Food:    {c.food_found}",
                f"Signals: {c.signals_sent} s / {c.signals_received} r",
                f"Asleep:  {'YES' if c.is_asleep else 'no'}",
            ]:
                self.screen.blit(self.font.render(line, True, WHITE), (px + 15, y))
                y += 20
            if c.parent_id >= 0:
                self.screen.blit(
                    self.font.render(f"Parent:  #{c.parent_id}", True, GRAY),
                    (px + 15, y),
                )
                y += 20
            y += 8
            b = (
                self.eco.terrain.biome_name_at(c.x, c.y)
                if hasattr(self.eco.terrain, "biome_name_at")
                else ""
            )
            self.screen.blit(self.font.render(f"Biome: {b}", True, CYAN), (px + 15, y))
            y += 18
            self.screen.blit(
                self.font.render(f"Pos: ({c.x:.0f},{c.y:.0f})", True, GRAY),
                (px + 15, y),
            )
        else:
            lines = (
                [
                    "Click a crow.",
                    "",
                    "Realistic terrain map:",
                    "- Biome-based food & perches",
                    "- Birth/death dynamics",
                    "- Energy & hunger drive",
                    "  survival & reproduction",
                    "- Crows die of starvation,",
                    "  old age, or exhaustion",
                    "",
                ]
                if self.mode == "natural"
                else [
                    "Click a crow.",
                    "",
                    "Financial ecosystem:",
                    "- Crows = portfolio positions",
                    "- Greeks drive behavior",
                    "- Green = profitable",
                    "- Red = losing position",
                ]
            )
            for line in lines:
                col = (
                    GRAY
                    if (not line or line.startswith("-") or line.startswith("  "))
                    else WHITE
                )
                self.screen.blit(self.font.render(line, True, col), (px + 15, y))
                y += 17

    def draw_roost_panel(self):
        if not self.show_roost_panel:
            return
        pw, ph, px, py = 220, 200, 10, HEIGHT - 210
        overlay = pygame.Surface((pw, ph))
        overlay.set_alpha(210)
        overlay.fill(DARK_GRAY)
        self.screen.blit(overlay, (px, py))
        pygame.draw.rect(self.screen, BLUE, (px, py, pw, ph), 1)
        self.screen.blit(
            self.font.render("Roost Clusters", True, BLUE), (px + 8, py + 6)
        )
        y = py + 24
        for rc in self.eco.roost_clusters:
            if not rc.members:
                continue
            self.screen.blit(
                self.font.render(
                    f"R{rc.id}: {len(rc.members)} @({int(rc.center_x)},{int(rc.center_y)})",
                    True,
                    WHITE,
                ),
                (px + 10, y),
            )
            y += 16
            for mid in rc.members[:6]:
                if mid >= len(self.eco.crows):
                    continue
                c2 = self.eco.crows[mid]
                self.screen.blit(
                    self.font.render(
                        f"  #{mid} e={c2.energy:.2f} h={c2.hunger:.2f}", True, GRAY
                    ),
                    (px + 16, y),
                )
                y += 13
            if len(rc.members) > 6:
                self.screen.blit(
                    self.font.render(f"  ... +{len(rc.members) - 6} more", True, GRAY),
                    (px + 16, y),
                )
                y += 13

    def draw_telemetry(self):
        if not self.eco.crows:
            return
        avg_spd = sum(math.hypot(c.vx, c.vy) for c in self.eco.crows) / len(
            self.eco.crows
        )
        lines = [
            f"Avg speed: {avg_spd:.1f}",
            f"Signals: {len(self.eco.signals)} active",
            f"Food: {sum(1 for f in self.eco.foods if not f.depleted)}/{len(self.eco.foods)}",
            f"Roosts: {sum(1 for rc in self.eco.roost_clusters if rc.members)} active",
        ]
        x, y = 10, 44
        for line in lines:
            self.screen.blit(self.font.render(line, True, GRAY), (x, y))
            y += 14

    def run(self):
        while self.running:
            self.handle_events()
            if not self.paused:
                self.eco.update()
            self.screen.fill(BLACK)
            self.eco.draw(self.screen)
            self.draw_hud()
            self.draw_info_panel()
            self.draw_roost_panel()
            self.draw_telemetry()
            if self.selected_crow:
                mx, my = pygame.mouse.get_pos()
                pygame.draw.line(
                    self.screen,
                    AMBER,
                    (int(self.selected_crow.x), int(self.selected_crow.y)),
                    (mx, my),
                    1,
                )
            if self.hovered_crow and self.hovered_crow is not self.selected_crow:
                pygame.draw.circle(
                    self.screen,
                    AMBER,
                    (int(self.hovered_crow.x), int(self.hovered_crow.y)),
                    int(self.hovered_crow.size) + 4,
                    1,
                )
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Crow Ecosystem 2D Dashboard")
    parser.add_argument(
        "--crow",
        type=str,
        default="natural",
        choices=["natural", "financial"],
        help="natural (realistic terrain, birth/death) or financial (portfolio Greeks)",
    )
    args = parser.parse_args()
    print(f"Launching Crow Ecosystem — {args.crow.title()} Mode")
    print("Controls: [SPC] pause [I] info [C] roosts [R] reset [ESC] quit")
    print("Click a crow to inspect; hover for highlight.")
    Dashboard(args.crow).run()


if __name__ == "__main__":
    main()
