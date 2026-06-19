#!/usr/bin/env python3
import pygame
import random
import math
import sys
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

WIDTH, HEIGHT = 1280, 800
FPS = 60
NUM_CROWS = 40
NUM_FOOD = 18
NUM_PERCHES = 8
DAY_LENGTH = 3600

BLACK = (10, 10, 15)
WHITE = (220, 220, 230)
DARK_GRAY = (30, 30, 40)
GRAY = (80, 80, 100)
GREEN = (80, 220, 120)
RED = (220, 80, 80)
AMBER = (240, 190, 50)
BLUE = (60, 140, 240)
PURPLE = (180, 100, 240)
CYAN = (80, 220, 220)
ORANGE = (240, 160, 60)
PINK = (240, 100, 180)

FOOD_COLORS = {
    "berry": (200, 60, 80),
    "insect": (140, 100, 60),
    "grain": (220, 200, 80),
    "seed": (180, 150, 70),
    "scrap": (130, 130, 130),
}
FOOD_TYPES = list(FOOD_COLORS.keys())

SIGNAL_FOOD = "food"
SIGNAL_DANGER = "danger"
SIGNAL_ROOST = "roost"
SIGNAL_SCOUT = "scout"
SIGNAL_AFFILIATE = "affiliate"


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
            SIGNAL_FOOD: GREEN,
            SIGNAL_DANGER: RED,
            SIGNAL_ROOST: BLUE,
            SIGNAL_SCOUT: AMBER,
            SIGNAL_AFFILIATE: PURPLE,
        }.get(self.kind, GRAY)


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
            gamma=random.uniform(0.0, 0.5)
            if abs(d) > 0.3
            else random.uniform(0.0, 0.15),
            theta=random.uniform(-0.3, 0.0),
            vega=random.uniform(0.0, 0.8),
            rho=random.uniform(-0.1, 0.1),
            position_size=random.uniform(0.5, 3.0),
            pnl_pct=random.uniform(-15.0, 15.0),
            is_option=True,
        )
    return GreekProfile(
        ticker=ticker,
        delta=random.uniform(-0.8, 0.8),
        gamma=random.uniform(0.0, 0.1),
        theta=0.0,
        vega=0.0,
        rho=random.uniform(-0.05, 0.05),
        position_size=random.uniform(1.0, 5.0),
        pnl_pct=random.uniform(-8.0, 8.0),
        is_option=False,
    )


class Crow:
    def __init__(self, x: float, y: float, crow_id: int, mode: str):
        self.id = crow_id
        self.x = x
        self.y = y
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)
        self.ax = 0.0
        self.ay = 0.0
        self.max_speed = random.uniform(2.5, 4.5)
        self.max_force = 0.08
        self.size = random.uniform(4, 7)
        self.color = random.choice([(40, 40, 50), (50, 45, 55), (35, 35, 45)])
        self.mode = mode
        self.wing_angle = random.uniform(-0.3, 0.3)
        self.is_scout = False
        self.scatter_timer = 0
        self.greeks = None

        self.energy = random.uniform(0.6, 1.0)
        self.is_asleep = False
        self.food_found = 0
        self.signals_sent = 0
        self.signals_received = 0
        self.roost_id: Optional[int] = None
        self.affiliates: List[int] = field(default_factory=list)
        self.signal_queue: List[Signal] = []
        self.caw_timer = 0
        self.caw_cooldown = random.randint(120, 400)
        self.emit_cooldown = 0

        if mode == "financial":
            tickers = [
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
            t = tickers[crow_id % len(tickers)]
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
        if count > 0:
            fx /= count
            fy /= count
            d = math.hypot(fx, fy)
            if d > 0:
                fx = fx / d * self.max_speed - self.vx
                fy = fy / d * self.max_speed - self.vy
                fx *= weight * self.max_force
                fy *= weight * self.max_force
            self.apply_force(fx, fy)

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
        if count > 0:
            fx = fx / count - self.vx
            fy = fy / count - self.vy
            self.apply_force(fx * weight * self.max_force, fy * weight * self.max_force)

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
        dx = self.x - tx
        dy = self.y - ty
        d = math.hypot(dx, dy)
        if 0 < d < radius:
            self.seek(self.x + dx * 10, self.y + dy * 10, weight * (1 - d / radius))

    def edges(self):
        margin = 80
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
            d = math.hypot(self.x - o.x, self.y - o.y)
            if d < radius:
                sig = Signal(kind, self.id, o.id, self.x, self.y, o.x, o.y)
                self.signal_queue.append(sig)
                o.signals_received += 1
        self.signals_sent += 1

    def update(self):
        if self.emit_cooldown > 0:
            self.emit_cooldown -= 1
        self.signal_queue = [s for s in self.signal_queue if s.alive]
        for s in self.signal_queue:
            s.life -= 1

        if self.is_asleep:
            self.vx *= 0.9
            self.vy *= 0.9
            self.energy = min(1.0, self.energy + 0.002)
        else:
            self.energy = max(0.0, self.energy - 0.0003)

        self.vx += self.ax
        self.vy += self.ay
        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_speed:
            self.vx = self.vx / speed * self.max_speed
            self.vy = self.vy / speed * self.max_speed
        self.x += self.vx
        self.y += self.vy
        self.ax *= 0
        self.ay *= 0
        self.wing_angle = math.sin(pygame.time.get_ticks() * 0.005 + self.id) * 0.3
        self.caw_timer += 1

        if self.greeks and self.mode == "financial":
            self.greeks.pnl_pct += random.gauss(0, 0.05)
            self.greeks.pnl_pct = max(-30, min(30, self.greeks.pnl_pct))
            self.color = self._pnl_color()

    def draw(self, screen: pygame.Surface, signals: List[Signal]):
        for s in self.signal_queue:
            Draw.signal_line(screen, s)

        if self.is_asleep:
            sleep_color = (20, 20, 35)
            pygame.draw.circle(
                screen, sleep_color, (int(self.x), int(self.y)), int(self.size * 1.8)
            )
            pygame.draw.circle(
                screen, GRAY, (int(self.x), int(self.y)), int(self.size * 1.8), 1
            )
            zzz = pygame.font.SysFont("monospace", 12)
            z = zzz.render("z", True, GRAY)
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
            int(self.x - cos_a * s * 0.3 + sin_a * s * (1.0 + wa)),
            int(self.y - sin_a * s * 0.3 - cos_a * s * (1.0 + wa)),
        )
        wing_r = (
            int(self.x - cos_a * s * 0.3 - sin_a * s * (1.0 + wa)),
            int(self.y - sin_a * s * 0.3 + cos_a * s * (1.0 + wa)),
        )

        body_color = self.color
        dim = 0.6 + 0.4 * self.energy
        body_color = tuple(int(c * dim) for c in body_color)

        pygame.draw.polygon(screen, body_color, [body, tail, wing_l, wing_r], 0)
        pygame.draw.circle(
            screen, WHITE if self.is_scout else body_color, body, max(2, int(s * 0.4))
        )
        pygame.draw.circle(screen, BLACK, body, max(1, int(s * 0.2)))
        eye_c = AMBER if self.energy < 0.25 else WHITE
        pygame.draw.circle(screen, eye_c, beak, max(1, int(s * 0.3)))

        energy_bar_w = int(s * 2)
        energy_bar_h = 2
        ex = self.x - energy_bar_w / 2
        ey = self.y - s - 6
        pygame.draw.rect(screen, DARK_GRAY, (ex, ey, energy_bar_w, energy_bar_h))
        ew = int(energy_bar_w * self.energy)
        ec = GREEN if self.energy > 0.5 else AMBER if self.energy > 0.2 else RED
        pygame.draw.rect(screen, ec, (ex, ey, ew, energy_bar_h))

        if self.greeks and self.mode == "financial":
            label_font = pygame.font.SysFont("monospace", 10)
            txt = label_font.render(self.greeks.ticker, True, WHITE)
            screen.blit(txt, (self.x - 12, self.y - s - 14))

        if self.caw_timer > self.caw_cooldown:
            self.caw_timer = 0
            self.caw_cooldown = random.randint(180, 600)
            caw_font = pygame.font.SysFont("monospace", 16)
            caw_text = random.choice(["CAW!", "caw", "CaW!", "!CAW"])
            c = AMBER if self.is_scout else GRAY
            txt = caw_font.render(caw_text, True, c)
            screen.blit(txt, (self.x + 10, self.y - 15))


class Draw:
    @staticmethod
    def signal_line(screen: pygame.Surface, s: Signal):
        if not s.alive:
            return
        progress = s.progress
        cx = s.sx + (s.tx - s.sx) * progress
        cy = s.sy + (s.ty - s.sy) * progress
        color = s.color()
        alpha = int(180 * (1 - progress))

        offsets = [-4, 0, 4]
        for off in offsets:
            segs = 3
            for i in range(segs):
                t0 = i / segs
                t1 = (i + 0.5) / segs
                p0x = cx + (s.tx - s.sx) * 0.15 * (t0 - 0.5) + off
                p0y = cy + (s.ty - s.sy) * 0.15 * (t0 - 0.5) + off
                p1x = cx + (s.tx - s.sx) * 0.15 * (t1 - 0.5) + off
                p1y = cy + (s.ty - s.sy) * 0.15 * (t1 - 0.5) + off
                dash_c = (color[0], color[1], color[2], alpha)
                try:
                    pygame.draw.line(
                        screen,
                        dash_c[:3],
                        (int(p0x), int(p0y)),
                        (int(p1x), int(p1y)),
                        1,
                    )
                except Exception:
                    pass

    @staticmethod
    def pressure_heatmap(
        screen: pygame.Surface, density_grid: List[List[float]], night_factor: float
    ):
        if night_factor < 0:
            return
        cell_w = WIDTH // len(density_grid[0])
        cell_h = HEIGHT // len(density_grid)
        for gy, row in enumerate(density_grid):
            for gx, val in enumerate(row):
                if val < 0.02:
                    continue
                intensity = min(val * 2.0, 1.0)
                r = int(200 * intensity)
                g = int(100 * (1 - intensity))
                b = int(200 * (1 - intensity))
                overlay = pygame.Surface((cell_w, cell_h))
                overlay.set_alpha(int(40 * intensity))
                overlay.fill((r, g, b))
                screen.blit(overlay, (gx * cell_w, gy * cell_h))

    @staticmethod
    def pulse_ring(
        screen: pygame.Surface,
        x: float,
        y: float,
        radius: float,
        color: Tuple,
        life: int,
        max_life: int,
    ):
        progress = 1.0 - life / max_life
        r = radius * progress
        alpha = int(100 * (1 - progress))
        pygame.draw.circle(screen, color, (int(x), int(y)), int(r), 1)


@dataclass
class FoodSource:
    x: float
    y: float
    amount: float = 1.0
    kind: str = "berry"
    regrow_timer: int = 0
    depleted: bool = False

    def draw(self, screen: pygame.Surface):
        if self.depleted and self.regrow_timer > 0:
            r = 2
            c = (40, 40, 40)
            pygame.draw.circle(screen, c, (int(self.x), int(self.y)), r)
            return
        if self.depleted:
            return
        base_color = FOOD_COLORS.get(self.kind, GREEN)
        r = max(2, int(4 * self.amount))
        bright = int(200 + 55 * self.amount)
        c = (
            min(base_color[0] + 30, bright),
            min(base_color[1] + 30, bright),
            min(base_color[2] + 30, bright),
        )
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
        for dx in [-10, 0, 10]:
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
        if not self.members:
            return
        xs = [crows[mid].x for mid in self.members if mid < len(crows)]
        ys = [crows[mid].y for mid in self.members if mid < len(crows)]
        if xs:
            self.center_x = sum(xs) / len(xs)
            self.center_y = sum(ys) / len(ys)

    def draw(self, screen: pygame.Surface, crows: List[Crow]):
        if len(self.members) < 2:
            return
        pts = []
        for mid in self.members:
            if mid < len(crows):
                c = crows[mid]
                if c.is_asleep:
                    pts.append((int(c.x), int(c.y)))
        if len(pts) < 2:
            return
            hull = RoostCluster.convex_hull(pts) if len(pts) > 2 else pts
        if len(hull) > 2:
            pygame.draw.polygon(screen, (30, 30, 60), hull, 1)
        cx = int(self.center_x)
        cy = int(self.center_y)
        label_font = pygame.font.SysFont("monospace", 10)
        txt = label_font.render(f"R{self.id}:{len(self.members)}", True, BLUE)
        screen.blit(txt, (cx - 15, cy - 10))

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


class Ecosystem:
    def __init__(self, mode: str):
        self.mode = mode
        self.crows: List[Crow] = []
        self.foods: List[FoodSource] = []
        self.perches: List[Perch] = []
        self.roost_clusters: List[RoostCluster] = []
        self.signals: List[Signal] = []
        self.tick = 0
        self.time_of_day = 0.25
        self.day_count = 0
        self.density_grid: List[List[float]] = [[0.0] * 16 for _ in range(10)]
        self.night_factor = 0.0

        for i in range(NUM_CROWS):
            self.crows.append(
                Crow(
                    random.uniform(100, WIDTH - 100),
                    random.uniform(100, HEIGHT - 100),
                    i,
                    mode,
                )
            )

        for _ in range(NUM_PERCHES):
            p = Perch(
                random.uniform(100, WIDTH - 100),
                random.uniform(500, HEIGHT - 50),
                random.uniform(60, 140),
            )
            self.perches.append(p)
            self.roost_clusters.append(
                RoostCluster(len(self.roost_clusters), len(self.perches) - 1, [])
            )

        if mode == "natural":
            for _ in range(NUM_FOOD):
                self._spawn_food()
            scout_count = max(2, NUM_CROWS // 8)
            for i in range(scout_count):
                self.crows[i].is_scout = True

        if mode == "financial":
            self.crows.sort(
                key=lambda c: abs(c.greeks.delta) if c.greeks else 0, reverse=True
            )

    def _spawn_food(self):
        kind = random.choice(FOOD_TYPES)
        self.foods.append(
            FoodSource(
                random.uniform(50, WIDTH - 50),
                random.uniform(50, HEIGHT - 100),
                random.uniform(0.5, 1.5),
                kind,
            )
        )

    def update(self):
        self.tick += 1
        self.time_of_day = (self.tick % DAY_LENGTH) / DAY_LENGTH
        self.night_factor = math.sin(self.time_of_day * 2 * math.pi)

        if self.tick % DAY_LENGTH == 0:
            self.day_count += 1

        self._update_density_grid()

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

        if self.mode == "natural" and self.tick % 180 == 0:
            self._spawn_food()

        for f in self.foods:
            if f.depleted:
                f.regrow_timer -= 1
                if f.regrow_timer <= 0:
                    f.amount = random.uniform(0.3, 1.0)
                    f.depleted = False
                    f.kind = random.choice(FOOD_TYPES)

    def _update_density_grid(self):
        for gy in range(len(self.density_grid)):
            for gx in range(len(self.density_grid[0])):
                self.density_grid[gy][gx] *= 0.95
        for c in self.crows:
            if c.is_asleep:
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
            if c.is_asleep and c.roost_id is not None:
                if c.roost_id < len(self.roost_clusters):
                    self.roost_clusters[c.roost_id].members.append(i)
        for rc in self.roost_clusters:
            rc.update_center(self.crows)

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
        is_dusk = self._is_dusk()

        for c in self.crows:
            if is_night:
                c.is_asleep = c.energy < 0.8
                if c.is_asleep:
                    if c.roost_id is None:
                        closest_perch = min(
                            range(len(self.perches)),
                            key=lambda i: math.hypot(
                                c.x - self.perches[i].x, c.y - self.perches[i].y
                            ),
                        )
                        c.roost_id = closest_perch
                    p = self.perches[c.roost_id]
                    c.seek(p.x, p.y - p.height * 0.3, 1.2)
                    c.max_speed = 1.5
                continue
            else:
                c.is_asleep = False
                c.roost_id = None
                c.max_speed = random.uniform(2.5, 4.5)

            c.separate(self.crows, 25, 1.8)
            c.align(self.crows, 60, 1.0)
            c.cohere(self.crows, 80, 0.6)

            if c.is_scout:
                c.scatter_timer += 1
                if c.scatter_timer > 300:
                    c.is_scout = False
                    c.scatter_timer = 0
                    pool = [x for x in self.crows if not x.is_scout]
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

            if c.energy < 0.4 and self.foods:
                active_foods = [f for f in self.foods if not f.depleted]
                if active_foods:
                    closest = min(
                        active_foods, key=lambda f: math.hypot(c.x - f.x, c.y - f.y)
                    )
                    d = math.hypot(c.x - closest.x, c.y - closest.y)
                    if d < 300:
                        c.seek(closest.x, closest.y, 1.2 if d < 80 else 0.6)
                        if d < 12:
                            closest.amount -= 0.03
                            c.energy = min(1.0, c.energy + 0.15)
                            c.food_found += 1
                            if closest.amount <= 0:
                                closest.depleted = True
                                closest.regrow_timer = 600 + random.randint(0, 300)
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
                others_nearby = [
                    o
                    for o in self.crows
                    if o is not c and math.hypot(c.x - o.x, c.y - o.y) < 100
                ]
                if others_nearby and c.emit_cooldown == 0:
                    c.emit_signal(SIGNAL_AFFILIATE, others_nearby[:3], 100)
                    self.signals.extend(c.signal_queue[-1:])

        if is_dusk:
            for c in self.crows:
                if c.energy < 0.6:
                    closest_perch = min(
                        range(len(self.perches)),
                        key=lambda i: math.hypot(
                            c.x - self.perches[i].x, c.y - self.perches[i].y
                        ),
                    )
                    p = self.perches[closest_perch]
                    c.seek(p.x, p.y - p.height * 0.3, 0.6)

    def _update_financial(self):
        market_sync = abs(sum(c.greeks.delta for c in self.crows if c.greeks)) / max(
            len(self.crows), 1
        )
        for c in self.crows:
            c.is_asleep = False
            g = c.greeks
            if not g:
                continue
            sep_weight = 1.8 - abs(g.delta) * 0.5
            c.separate(self.crows, 25 + abs(g.delta) * 10, max(0.5, sep_weight))
            align_weight = 0.6 + abs(g.delta) * 0.4
            c.align(self.crows, 60 + abs(g.delta) * 20, align_weight)
            cohere_weight = 0.4 + abs(g.delta) * 0.3
            c.cohere(self.crows, 80, cohere_weight)
            c.apply_force(g.delta * 0.5, (g.gamma * 2.0 - 1.0) * 0.15)
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
            g.delta += random.gauss(0, 0.01) * (1 + g.vega * 0.5)
            g.delta = max(-1.0, min(1.0, g.delta))
            g.gamma += random.gauss(0, 0.005)
            g.gamma = max(0, min(1.0, g.gamma))
            g.theta += random.gauss(0, 0.002)
            g.theta = max(-0.5, min(0, g.theta))
            g.vega += random.gauss(0, 0.005)
            g.vega = max(0, min(1.0, g.vega))
            scale = 1.0 + market_sync * 0.3
            c.max_speed = (1.5 + abs(g.delta) * 2.0) * scale
            g.pnl_pct += g.delta * 0.01 + random.gauss(0, 0.03)
            g.pnl_pct = max(-30, min(30, g.pnl_pct))
            c.color = c._pnl_color()
        for i, c in enumerate(self.crows):
            c.is_scout = i < max(1, int(len(self.crows) * 0.1))

    def draw(self, screen: pygame.Surface):
        Draw.pressure_heatmap(screen, self.density_grid, self.night_factor)
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
        self._draw_ground(screen)

    def _draw_ground(self, screen: pygame.Surface):
        ground_y = HEIGHT - 10
        for x in range(0, WIDTH, 20):
            h = random.randint(2, 5)
            pygame.draw.line(screen, (30, 35, 25), (x, ground_y), (x, ground_y + h), 1)


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
                closest = min(
                    self.eco.crows, key=lambda c: math.hypot(c.x - mx, c.y - my)
                )
                if math.hypot(closest.x - mx, closest.y - my) < 20:
                    self.selected_crow = (
                        closest if self.selected_crow is not closest else None
                    )
                elif self.show_roost_panel:
                    for rc in self.eco.roost_clusters:
                        if math.hypot(rc.center_x - mx, rc.center_y - my) < 30:
                            print(
                                f"[ROOST {rc.id}] {len(rc.members)} members, "
                                f"pos=({int(rc.center_x)},{int(rc.center_y)})"
                            )
                else:
                    self.selected_crow = None

    def draw_hud(self):
        overlay = pygame.Surface((WIDTH, 40))
        overlay.set_alpha(160)
        overlay.fill(DARK_GRAY)
        self.screen.blit(overlay, (0, 0))

        hour = int(self.eco.time_of_day * 24)
        min_ = int((self.eco.time_of_day * 24 - hour) * 60)
        time_str = f"{hour:02d}:{min_:02d}"
        phase_str = (
            "NIGHT"
            if self.eco._is_night()
            else "DAWN"
            if self.eco._is_dawn()
            else "DUSK"
            if self.eco._is_dusk()
            else "DAY"
        )

        mode_str = f"MODE: {self.mode.upper()}"
        paused_str = " [PAUSED]" if self.paused else ""
        crow_count = f"Crows: {len(self.eco.crows)}"
        awake = sum(1 for c in self.eco.crows if not c.is_asleep)
        asleep = len(self.eco.crows) - awake
        sleep_str = f"Awake: {awake}  Asleep: {asleep}"
        food_str = (
            f"Food: {sum(1 for f in self.eco.foods if not f.depleted)}"
            if self.mode == "natural"
            else ""
        )
        day_str = f"Day {self.eco.day_count}"
        tick_str = f"Tick: {self.eco.tick}"

        x = 15
        for s in [
            mode_str,
            paused_str,
            crow_count,
            sleep_str,
            food_str,
            day_str,
            tick_str,
            f"| {time_str} {phase_str}",
        ]:
            if s:
                c = AMBER if "PAUSED" in s else WHITE
                txt = self.font.render(s, True, c)
                self.screen.blit(txt, (x, 12))
                x += txt.get_width() + 14

        hints = "[SPC] pause [I] info [C] roosts [R] reset [ESC] quit"
        txt = self.font.render(hints, True, GRAY)
        self.screen.blit(txt, (WIDTH - txt.get_width() - 15, 12))

        if self.eco._is_night():
            overlay = pygame.Surface((WIDTH, HEIGHT))
            alpha = int(min(100, abs(self.eco.night_factor) * 140))
            overlay.set_alpha(alpha)
            overlay.fill((10, 5, 30))
            self.screen.blit(overlay, (0, 0))

    def draw_info_panel(self):
        if not self.show_info:
            return

        panel_w = 280
        panel_h = HEIGHT - 50
        panel_x = WIDTH - panel_w - 10
        panel_y = 50

        overlay = pygame.Surface((panel_w, panel_h))
        overlay.set_alpha(200)
        overlay.fill(DARK_GRAY)
        self.screen.blit(overlay, (panel_x, panel_y))
        pygame.draw.rect(self.screen, GRAY, (panel_x, panel_y, panel_w, panel_h), 1)

        y = panel_y + 15
        scroll = 0

        if (
            self.mode == "financial"
            and self.selected_crow
            and self.selected_crow.greeks
        ):
            g = self.selected_crow.greeks
            title = self.title_font.render(f"  {g.ticker}  ", True, AMBER)
            self.screen.blit(title, (panel_x + 10, y))
            y += 30
            lines = [
                f"Delta:   {g.delta:+.3f}  (thrust/direction)",
                f"Gamma:   {g.gamma:.3f}   (acceleration/energy)",
                f"Theta:   {g.theta:+.3f}   (time decay/drift)",
                f"Vega:    {g.vega:.3f}   (volatility/noise)",
                f"Rho:     {g.rho:+.3f}   (rate sensitivity)",
                f"Type:    {'OPTION' if g.is_option else 'EQUITY'}",
                f"Size:    {g.position_size:.1f}x",
                f"P&L:     {g.pnl_pct:+.1f}%",
            ]
            for line in lines:
                c = (
                    GREEN
                    if line.startswith("P&L:") and g.pnl_pct >= 0
                    else RED
                    if line.startswith("P&L:")
                    else WHITE
                )
                txt = self.font.render(line, True, c)
                self.screen.blit(txt, (panel_x + 15, y))
                y += 22
            y += 10
            flock_val = sum(
                abs(c.greeks.delta) for c in self.eco.crows if c.greeks
            ) / max(len(self.eco.crows), 1)
            txt = self.font.render(f"Market Sync: {flock_val:.3f}", True, CYAN)
            self.screen.blit(txt, (panel_x + 15, y))
            y += 22
            delta_sign = (
                "LONG" if g.delta > 0.1 else "SHORT" if g.delta < -0.1 else "NEUTRAL"
            )
            gamma_note = "HIGH CONVEXITY" if g.gamma > 0.3 else "LOW CONVEXITY"
            theta_note = "TIME DECAY" if g.theta < -0.05 else "TIME NEUTRAL"
            y += 10
            for note in [delta_sign, gamma_note, theta_note]:
                txt = self.font.render(f"> {note}", True, PURPLE)
                self.screen.blit(txt, (panel_x + 15, y))
                y += 20
            # comm stats
            y += 10
            txt = self.font.render(
                f"Signals sent: {self.selected_crow.signals_sent}", True, CYAN
            )
            self.screen.blit(txt, (panel_x + 15, y))
            y += 18
            txt = self.font.render(
                f"Signals rcvd: {self.selected_crow.signals_received}", True, CYAN
            )
            self.screen.blit(txt, (panel_x + 15, y))
            y += 18

        elif self.mode == "natural" and self.selected_crow:
            c = self.selected_crow
            title = self.title_font.render(f"  Crow #{c.id}", True, AMBER)
            self.screen.blit(title, (panel_x + 10, y))
            y += 30
            role = "SCOUT" if c.is_scout else "FORAGER"
            spd = math.hypot(c.vx, c.vy)
            lines = [
                f"Role:    {role}",
                f"Energy:  {c.energy:.2f}",
                f"Speed:   {spd:.1f} px/t",
                f"Pos:     ({c.x:.0f}, {c.y:.0f})",
                f"Food found: {c.food_found}",
                f"Signals sent: {c.signals_sent}",
                f"Signals rcvd: {c.signals_received}",
                f"Asleep:  {'YES' if c.is_asleep else 'no'}",
            ]
            for line in lines:
                txt = self.font.render(line, True, WHITE)
                self.screen.blit(txt, (panel_x + 15, y))
                y += 20

        else:
            lines = []
            if self.mode == "natural":
                lines = [
                    "Click a crow to inspect.",
                    "",
                    "Natural ecosystem:",
                    "- Crows flock, forage, roost",
                    "- Scouts explore & signal",
                    "- Night: sleep in roosts",
                    "- Dawn: wake up, forage",
                    "- Food types: berry, insect,",
                    "  grain, seed, scrap",
                    "- Colored lines = signals",
                    "- Green=food, Red=danger",
                    "- Blue=roost, Purple=social",
                ]
            else:
                lines = [
                    "Click a crow to inspect.",
                    "",
                    "Financial ecosystem:",
                    "- Each crow = position",
                    "- Delta = thrust/direction",
                    "- Gamma = acceleration",
                    "- Theta = mean reversion",
                    "- Vega = volatility noise",
                    "- Rho = drift bias",
                    "",
                    "Green = profitable",
                    "Red = losing position",
                ]
            for line in lines:
                c = (
                    GRAY
                    if (line.startswith("-") or line == "" or line.startswith("  "))
                    else WHITE
                )
                txt = self.font.render(line, True, c)
                self.screen.blit(txt, (panel_x + 15, y))
                y += 18

    def draw_roost_panel(self):
        if not self.show_roost_panel:
            return
        pw, ph = 200, 200
        px, py = 10, HEIGHT - ph - 10
        overlay = pygame.Surface((pw, ph))
        overlay.set_alpha(210)
        overlay.fill(DARK_GRAY)
        self.screen.blit(overlay, (px, py))
        pygame.draw.rect(self.screen, BLUE, (px, py, pw, ph), 1)
        title = self.font.render("Roost Clusters", True, BLUE)
        self.screen.blit(title, (px + 8, py + 6))
        y = py + 24
        for rc in self.eco.roost_clusters:
            if not rc.members:
                continue
            label = f"R{rc.id}: {len(rc.members)} crows @({int(rc.center_x)},{int(rc.center_y)})"
            txt = self.font.render(label, True, WHITE)
            self.screen.blit(txt, (px + 10, y))
            y += 16
            for mid in rc.members[:5]:
                if mid < len(self.eco.crows):
                    c = self.eco.crows[mid]
                    e = c.energy
                    sub = f"  #{mid} energy={e:.2f}"
                    txt = self.font.render(sub, True, GRAY)
                    self.screen.blit(txt, (px + 16, y))
                    y += 13
            if len(rc.members) > 5:
                txt = self.font.render(f"  ... +{len(rc.members) - 5} more", True, GRAY)
                self.screen.blit(txt, (px + 16, y))
                y += 13

    def draw_telemetry_overlay(self):
        lines = [
            f"Avg speed: {sum(math.hypot(c.vx, c.vy) for c in self.eco.crows) / max(len(self.eco.crows), 1):.1f}",
            f"Total sig: {len(self.eco.signals)} active",
            f"Food avail: {sum(1 for f in self.eco.foods if not f.depleted)}/{len(self.eco.foods)}",
            f"Roosts: {sum(1 for rc in self.eco.roost_clusters if rc.members)} active",
        ]
        x, y = 10, 48
        for line in lines:
            txt = self.font.render(line, True, GRAY)
            self.screen.blit(txt, (x, y))
            y += 15

    def run(self):
        while self.running:
            self.handle_events()
            if not self.paused:
                self.eco.update()

            self.screen.fill(BLACK)
            stars = [
                (hash(str(i) + "x") % WIDTH, hash(str(i) + "y") % HEIGHT)
                for i in range(60)
            ]
            for sx, sy in stars:
                b = int(40 + 20 * math.sin(self.eco.tick * 0.01 + sx * 0.1))
                self.screen.set_at((sx, sy), (b, b, b + 10))

            self.eco.draw(self.screen)
            self.draw_hud()
            self.draw_info_panel()
            self.draw_roost_panel()
            self.draw_telemetry_overlay()

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
        help="natural (biological flocking) or financial (portfolio positions with Greeks)",
    )
    args = parser.parse_args()

    print(f"Launching Crow Ecosystem — {args.crow.title()} Mode")
    print("Controls: [SPC] pause  [I] info  [C] roost clusters  [R] reset  [ESC] quit")
    print("Click a crow to inspect; hover for highlight.")

    dash = Dashboard(args.crow)
    dash.run()


if __name__ == "__main__":
    main()
