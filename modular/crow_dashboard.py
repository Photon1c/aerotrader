#!/usr/bin/env python3
import pygame
import random
import math
import sys
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Optional

WIDTH, HEIGHT = 1280, 800
FPS = 60
NUM_CROWS = 40
NUM_FOOD = 30
NUM_PERCHES = 6

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

CROW_COLORS = [
    (40, 40, 50),
    (50, 45, 55),
    (35, 35, 45),
    (55, 50, 60),
    (45, 40, 50),
]


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
        self.color = random.choice(CROW_COLORS)
        self.mode = mode
        self.wing_angle = random.uniform(-0.3, 0.3)
        self.caw_timer = 0
        self.caw_cooldown = random.randint(180, 600)

        self.is_scout = False
        self.scatter_timer = 0

        self.greeks = None
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
            self.max_speed = random.uniform(1.5, 4.0)
            self.max_speed *= 1.0 + abs(self.greeks.delta) * 0.5
            self.size = 4 + self.greeks.position_size * 0.8
            self.color = self._pnl_color()

    def _pnl_color(self) -> Tuple[int, int, int]:
        if self.mode != "financial" or not self.greeks:
            return random.choice(CROW_COLORS)
        p = self.greeks.pnl_pct
        intensity = min(abs(p) / 15.0, 1.0)
        if p >= 0:
            return (
                int(40 * (1 - intensity) + 80 * intensity),
                int(40 * (1 - intensity) + 220 * intensity),
                int(50 * (1 - intensity) + 120 * intensity),
            )
        return (
            int(40 * (1 - intensity) + 220 * intensity),
            int(40 * (1 - intensity) + 80 * intensity),
            int(45 * (1 - intensity) + 80 * intensity),
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

    def update(self):
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

    def draw(self, screen):
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

        pygame.draw.polygon(screen, self.color, [body, tail, wing_l, wing_r], 0)
        pygame.draw.circle(
            screen, WHITE if self.is_scout else self.color, body, max(2, int(s * 0.4))
        )
        pygame.draw.circle(screen, BLACK, body, max(1, int(s * 0.2)))
        pygame.draw.circle(
            screen, AMBER if self.is_scout else BLACK, beak, max(1, int(s * 0.3))
        )

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


@dataclass
class Food:
    x: float
    y: float
    amount: float = 1.0

    def draw(self, screen):
        if self.amount > 0:
            r = max(2, int(4 * self.amount))
            pygame.draw.circle(screen, GREEN, (int(self.x), int(self.y)), r)
            pygame.draw.circle(screen, (40, 120, 60), (int(self.x), int(self.y)), r, 1)


@dataclass
class Perch:
    x: float
    y: float
    height: float

    def draw(self, screen):
        pygame.draw.line(
            screen,
            (60, 40, 20),
            (int(self.x), int(self.y)),
            (int(self.x), int(self.y - self.height)),
            3,
        )
        for dx in [-8, 0, 8]:
            pygame.draw.line(
                screen,
                (50, 80, 30),
                (int(self.x + dx), int(self.y - self.height)),
                (int(self.x + dx * 0.5), int(self.y - self.height + 15)),
                2,
            )


class Ecosystem:
    def __init__(self, mode: str):
        self.mode = mode
        self.crows: List[Crow] = []
        self.foods: List[Food] = []
        self.perches: List[Perch] = []
        self.tick = 0
        self.time_of_day = 0.0

        for i in range(NUM_CROWS):
            self.crows.append(
                Crow(
                    random.uniform(100, WIDTH - 100),
                    random.uniform(100, HEIGHT - 100),
                    i,
                    mode,
                )
            )

        if mode == "natural":
            self.foods = [
                Food(random.uniform(50, WIDTH - 50), random.uniform(50, HEIGHT - 50))
                for _ in range(NUM_FOOD)
            ]
            self.perches = [
                Perch(
                    random.uniform(100, WIDTH - 100),
                    random.uniform(500, HEIGHT - 50),
                    random.uniform(60, 120),
                )
                for _ in range(NUM_PERCHES)
            ]
            scout_count = max(2, NUM_CROWS // 8)
            for i in range(scout_count):
                self.crows[i].is_scout = True

        if mode == "financial":
            self.crows.sort(
                key=lambda c: abs(c.greeks.delta) if c.greeks else 0, reverse=True
            )

    def update(self):
        self.tick += 1
        self.time_of_day = (self.tick % 3600) / 3600.0

        if self.mode == "natural":
            self._update_natural()
        else:
            self._update_financial()

        for c in self.crows:
            c.edges()
            c.update()

        if self.mode == "natural" and self.tick % 120 == 0:
            self.foods.append(
                Food(random.uniform(50, WIDTH - 50), random.uniform(50, HEIGHT - 50))
            )

    def _update_natural(self):
        for c in self.crows:
            c.separate(self.crows, 25, 1.8)
            c.align(self.crows, 60, 1.0)
            c.cohere(self.crows, 80, 0.6)

            if c.is_scout:
                c.scatter_timer += 1
                if c.scatter_timer > 300:
                    c.is_scout = False
                    c.scatter_timer = 0
                    new_scout = random.choice([x for x in self.crows if not x.is_scout])
                    new_scout.is_scout = True
                if random.random() < 0.01:
                    c.seek(
                        random.uniform(50, WIDTH - 50),
                        random.uniform(50, HEIGHT - 50),
                        1.5,
                    )
                continue

            if self.foods:
                closest = min(
                    self.foods, key=lambda f: math.hypot(c.x - f.x, c.y - f.y)
                )
                d = math.hypot(c.x - closest.x, c.y - closest.y)
                if closest.amount > 0 and d < 300:
                    c.seek(closest.x, closest.y, 1.2 if d < 80 else 0.6)
                    if d < 12:
                        closest.amount -= 0.02
                        if closest.amount <= 0:
                            self.foods.remove(closest)

            for p in self.perches:
                d = math.hypot(c.x - p.x, c.y - p.y)
                if d < 60:
                    c.seek(p.x, p.y - p.height * 0.3, 0.3)
                    if d < 15:
                        c.vx *= 0.95
                        c.vy *= 0.95

            if random.random() < 0.005:
                c.seek(
                    random.uniform(50, WIDTH - 50), random.uniform(50, HEIGHT - 50), 0.8
                )

        night_factor = math.sin(self.time_of_day * 2 * math.pi)
        if night_factor < -0.3:
            for c in self.crows:
                c.max_speed = 1.5
                if not c.is_scout:
                    closest_perch = min(
                        self.perches, key=lambda p: math.hypot(c.x - p.x, c.y - p.y)
                    )
                    c.seek(
                        closest_perch.x,
                        closest_perch.y - closest_perch.height * 0.3,
                        1.0,
                    )

    def _update_financial(self):
        market_sync = abs(sum(c.greeks.delta for c in self.crows if c.greeks)) / max(
            len(self.crows), 1
        )

        for c in self.crows:
            g = c.greeks
            if not g:
                continue

            sep_weight = 1.8 - abs(g.delta) * 0.5
            c.separate(self.crows, 25 + abs(g.delta) * 10, max(0.5, sep_weight))

            align_weight = 0.6 + abs(g.delta) * 0.4
            c.align(self.crows, 60 + abs(g.delta) * 20, align_weight)

            cohere_weight = 0.4 + abs(g.delta) * 0.3
            c.cohere(self.crows, 80, cohere_weight)

            thrust_x = g.delta * 0.5
            thrust_y = (g.gamma * 2.0 - 1.0) * 0.3
            c.apply_force(thrust_x, thrust_y * 0.5)

            c.apply_force(-c.vx * abs(g.theta) * 0.05, -c.vy * abs(g.theta) * 0.05)

            if g.vega > 0:
                c.apply_force(
                    random.gauss(0, g.vega * 0.3),
                    random.gauss(0, g.vega * 0.3),
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
            if i < max(1, int(len(self.crows) * 0.1)):
                c.is_scout = True
            else:
                c.is_scout = False

    def draw(self, screen):
        for p in self.perches:
            p.draw(screen)
        for f in self.foods:
            f.draw(screen)
        for c in self.crows:
            c.draw(screen)


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

    def handle_events(self):
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
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                closest = min(
                    self.eco.crows, key=lambda c: math.hypot(c.x - mx, c.y - my)
                )
                if math.hypot(closest.x - mx, closest.y - my) < 20:
                    self.selected_crow = (
                        closest if self.selected_crow is not closest else None
                    )
                else:
                    self.selected_crow = None

    def draw_hud(self):
        overlay = pygame.Surface((WIDTH, 40))
        overlay.set_alpha(160)
        overlay.fill(DARK_GRAY)
        self.screen.blit(overlay, (0, 0))

        mode_str = f"MODE: {self.mode.upper()}"
        paused_str = " [PAUSED]" if self.paused else ""
        crow_count = f"Crows: {len(self.eco.crows)}"
        food_count = f"Food: {len(self.eco.foods)}" if self.mode == "natural" else ""
        tick_str = f"Tick: {self.eco.tick}"

        x = 15
        for s in [mode_str, paused_str, crow_count, food_count, tick_str]:
            if s:
                c = AMBER if "PAUSED" in s else WHITE
                txt = self.font.render(s, True, c)
                self.screen.blit(txt, (x, 12))
                x += txt.get_width() + 20

        hints = "[SPC] pause  [I] info  [R] reset  [ESC] quit"
        txt = self.font.render(hints, True, GRAY)
        self.screen.blit(txt, (WIDTH - txt.get_width() - 15, 12))

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

        elif self.mode == "natural" and self.selected_crow:
            c = self.selected_crow
            txt = self.title_font.render(f"  Crow #{c.id}", True, AMBER)
            self.screen.blit(txt, (panel_x + 10, y))
            y += 30

            role = "SCOUT" if c.is_scout else "FORAGER"
            spd = math.hypot(c.vx, c.vy)
            lines = [
                f"Role:    {role}",
                f"Speed:   {spd:.1f} px/tick",
                f"Pos:     ({c.x:.0f}, {c.y:.0f})",
                f"Size:    {c.size:.1f}",
                f"Food:    {len(self.eco.foods)} sources",
                f"Perches: {len(self.eco.perches)} trees",
            ]
            for line in lines:
                txt = self.font.render(line, True, WHITE)
                self.screen.blit(txt, (panel_x + 15, y))
                y += 22

            y += 10
            txt = self.font.render(
                f"Time: {int(self.eco.time_of_day * 24):02d}:00", True, CYAN
            )
            self.screen.blit(txt, (panel_x + 15, y))

        else:
            lines = []
            if self.mode == "natural":
                lines = [
                    "Click a crow to inspect.",
                    "",
                    "Natural ecosystem:",
                    "- Crows flock, forage, roost",
                    "- Scouts explore new areas",
                    "- Night = slow, seek perches",
                    "- Food spawns periodically",
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
                c = GRAY if line.startswith("-") or line == "" else WHITE
                txt = self.font.render(line, True, c)
                self.screen.blit(txt, (panel_x + 15, y))
                y += 20

    def run(self):
        while self.running:
            self.handle_events()
            if not self.paused:
                self.eco.update()

            self.screen.fill(BLACK)

            star_color = (60, 60, 80)
            for _ in range(80):
                sx = hash(str(_) + "x") % WIDTH
                sy = hash(str(_) + "y") % HEIGHT
                self.screen.set_at((sx, sy), star_color)

            if self.mode == "natural":
                night_factor = math.sin(self.eco.time_of_day * 2 * math.pi)
                if night_factor < 0:
                    overlay = pygame.Surface((WIDTH, HEIGHT))
                    alpha = int(min(80, abs(night_factor) * 120))
                    overlay.set_alpha(alpha)
                    overlay.fill((10, 5, 30))
                    self.screen.blit(overlay, (0, 0))

            self.eco.draw(self.screen)
            self.draw_hud()
            self.draw_info_panel()

            if self.selected_crow:
                mx, my = pygame.mouse.get_pos()
                pygame.draw.line(
                    self.screen,
                    AMBER,
                    (int(self.selected_crow.x), int(self.selected_crow.y)),
                    (mx, my),
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
        help="Simulation mode: natural (biological) or financial (portfolio positions)",
    )
    args = parser.parse_args()

    print(f"Launching Crow Ecosystem — {args.crow.title()} Mode")
    print("Controls: [SPC] pause  [I] toggle info panel  [R] reset  [ESC] quit")
    print("Click a crow to inspect its details.")

    dash = Dashboard(args.crow)
    dash.run()


if __name__ == "__main__":
    main()
