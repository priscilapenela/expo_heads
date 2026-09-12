"""Expo Heads UNO — jugador (cabeza + pie).
Estructura de pie IDÉNTICA al juego de referencia (nogica.py).

Boot sprite (nogica1.png) apunta a la DERECHA →

P1 (za_koga==1, lado izquierdo, mira →):
  - Init: flip horizontal → boot apunta ← (punta atrás)
  - IDLE: midbottom de la cabeza, colgando abajo
  - KICK: rotate(90°), posicionar en rect.right+7

P2 (za_koga==2, lado derecho, mira ←):
  - Init: sin flip → boot apunta → (punta atrás)
  - IDLE: midbottom de la cabeza, colgando abajo
  - KICK: rotate(-90°), posicionar en rect.left-7
"""

import pygame
import math
import os
import config as C


class Player:
    def __init__(self, player_num: int, head_color: tuple = None):
        self.num = player_num       # 1=izq, 2=der
        self.radius = C.PLAYER_HEAD_RADIUS

        if player_num == 1:
            self.start_x = C.WINDOW_W * 0.25
        else:
            self.start_x = C.WINDOW_W * 0.75

        # Física
        self.ACC = 0.6
        self.SKOK = 10.0
        self.FRIC = -0.12

        # Pie (proporcional a la cabeza)
        self.boot_w = int(self.radius * 1.3)
        self.boot_h = int(self.radius * 0.65)
        self.kick_delay = 0
        self.KICK_DURATION = 12

        self.reset()
        self.head_surface = self._build_head(head_color)
        self._setup_boot()

    def reset(self):
        self.x = self.start_x
        self.y = C.GROUND_Y - self.radius
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.kick_delay = 0
        self._ax = 0

    # ── HEAD (placeholder) ──────────────────────────────────
    def _build_head(self, color=None):
        size = self.radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)

        skin = color or ((210,170,130) if self.num == 1 else (225,185,145))
        hair = (25,20,15) if self.num == 1 else (95,65,30)

        pygame.draw.circle(surf, skin, (self.radius, self.radius), self.radius-1)

        # Pelo
        for y in range(5, self.radius-10):
            w = int(math.sqrt(max(0, self.radius**2 - (y-self.radius)**2)))
            if y < self.radius//2:
                pygame.draw.line(surf, hair, (self.radius-w+2,y), (self.radius+w-2,y))

        # Ojos 3/4
        off = 8 if self.num == 1 else -8
        sign = 1 if self.num == 1 else -1
        # Ojo cercano
        pygame.draw.circle(surf, (240,240,240), (self.radius+off+10*sign, self.radius-5), 6)
        pygame.draw.circle(surf, (20,20,20), (self.radius+off+12*sign, self.radius-5), 3)
        # Ojo lejano
        pygame.draw.circle(surf, (240,240,240), (self.radius+off-8*sign, self.radius-5), 5)
        pygame.draw.circle(surf, (20,20,20), (self.radius+off-6*sign, self.radius-5), 3)
        # Oreja
        ear_x = 8 if self.num == 1 else size-8
        pygame.draw.circle(surf, (190,150,110), (ear_x, self.radius+2), 6)
        pygame.draw.circle(surf, (170,130,95), (ear_x, self.radius+2), 4)
        # Boca
        mx = self.radius + 6*sign
        pygame.draw.line(surf, (150,80,60), (mx-6, self.radius+14), (mx+6, self.radius+14), 2)
        # Contorno
        pygame.draw.circle(surf, (15,15,15), (self.radius, self.radius), self.radius-1, 2)
        return surf

    # ── BOOT SETUP (idéntico a nogica.py) ────────────────────
    def _setup_boot(self):
        """Prepara los sprites del botín exactamente como la referencia."""
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "assets", "sprites", "boot.png")

        try:
            raw = pygame.image.load(path).convert_alpha()
        except Exception:
            raw = pygame.Surface((80, 45), pygame.SRCALPHA)
            pygame.draw.ellipse(raw, (25,25,25), raw.get_rect())

        # El sprite original apunta a la DERECHA →

        if self.num == 1:
            # P1: flip horizontal → apunta a la IZQUIERDA ←
            self.boot_img = pygame.transform.flip(raw, True, False)
        else:
            # P2: sin flip → apunta a la DERECHA →
            self.boot_img = raw

        # Escalar al tamaño correcto
        self.boot_img = pygame.transform.smoothscale(
            self.boot_img, (self.boot_w, self.boot_h)
        )

        # Pre-calcular versión idle y kick
        self.boot_idle_img = self.boot_img.copy()

        if self.num == 1:
            # P1 kick: rotar 90° (CCW en pygame)
            self.boot_kick_img = pygame.transform.rotate(self.boot_img, 90)
        else:
            # P2 kick: rotar -90° (CW en pygame)
            self.boot_kick_img = pygame.transform.rotate(self.boot_img, -90)

    # ── INPUT ────────────────────────────────────────────────
    def handle_input(self, keys):
        self._ax = 0
        if self.num == 1:
            if keys[pygame.K_a]: self._ax = -self.ACC
            if keys[pygame.K_d]: self._ax = self.ACC
            if keys[pygame.K_w] and self.on_ground:
                self.vy = -self.SKOK
                self.on_ground = False
            if keys[pygame.K_s] and self.kick_delay == 0:
                self.kick_delay = 1
        else:
            if keys[pygame.K_LEFT]: self._ax = -self.ACC
            if keys[pygame.K_RIGHT]: self._ax = self.ACC
            if keys[pygame.K_UP] and self.on_ground:
                self.vy = -self.SKOK
                self.on_ground = False
            if keys[pygame.K_DOWN] and self.kick_delay == 0:
                self.kick_delay = 1

    # ── UPDATE ───────────────────────────────────────────────
    def update(self):
        gravity = C.GRAVITY + 0.07
        ax = self._ax + self.vx * self.FRIC

        self.vx += ax
        self.vy += gravity
        self.x += self.vx + 0.5 * ax
        self.y += self.vy + 0.5 * gravity

        # Límites cancha
        if self.x - self.radius < C.GOAL_WIDTH:
            self.x = C.GOAL_WIDTH + self.radius
            self.vx *= -0.3
        if self.x + self.radius > C.WINDOW_W - C.GOAL_WIDTH:
            self.x = C.WINDOW_W - C.GOAL_WIDTH - self.radius
            self.vx *= -0.3

        # Piso
        if self.y + self.radius >= C.GROUND_Y:
            self.y = C.GROUND_Y - self.radius
            self.vy = 0
            self.on_ground = True

        # Techo
        if self.y - self.radius < C.PITCH_TOP - 60:
            self.y = C.PITCH_TOP - 60 + self.radius
            self.vy = 0

        # Kick timer
        if self.kick_delay > 0:
            self.kick_delay += 1
            if self.kick_delay >= self.KICK_DURATION:
                self.kick_delay = 0

    @property
    def is_kicking(self):
        return 1 <= self.kick_delay <= 4

    @property
    def rect(self):
        """Rect de la cabeza (para posicionar el pie como en la referencia)."""
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius),
                          self.radius * 2, self.radius * 2)

    # ── FOOT POSITION ────────────────────────────────────────
    def get_foot_pos(self):
        if self.kick_delay > 0:
            if self.num == 1:
                return (self.rect.right + 7, self.y + self.radius / 7)
            else:
                return (self.rect.left - 7, self.y + self.radius / 7)
        else:
            return (self.x, self.rect.bottom + self.boot_h / 7)

    def get_foot_rect(self):
        fx, fy = self.get_foot_pos()
        if self.kick_delay > 0:
            # Kick: el boot está rotado (ancho y alto intercambiados)
            r = self.boot_kick_img.get_rect(center=(int(fx), int(fy)))
        else:
            r = self.boot_idle_img.get_rect(center=(int(fx), int(fy)))
        return r

    # ── DRAW ─────────────────────────────────────────────────
    def draw(self, surface):
        # Sombra
        shadow_w = int(self.radius * 1.2)
        shadow_surf = pygame.Surface((shadow_w*2, 8), pygame.SRCALPHA)
        dist = max(1, C.GROUND_Y - (self.y + self.radius))
        alpha = max(20, 70 - dist)
        pygame.draw.ellipse(shadow_surf, (0,0,0,alpha), (0,0,shadow_w*2,8))
        surface.blit(shadow_surf, (int(self.x)-shadow_w, C.GROUND_Y+2))

        # Pie (dibujado EXACTAMENTE como nogica.py)
        self._draw_boot(surface)

        # Cabeza
        head_rect = self.head_surface.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.head_surface, head_rect)

    def _draw_boot(self, surface):
        """Posiciona el botín como en nogica.py:
        - IDLE: midbottom de la cabeza, desplazado abajo
        - KICK: al costado de la cabeza, hacia el rival
        """
        if self.kick_delay > 0:
            # ── PATEANDO ──
            boot = self.boot_kick_img
            if self.num == 1:
                # P1: pie al lado DERECHO de la cabeza
                pos_x = self.rect.right + 7
            else:
                # P2: pie al lado IZQUIERDO de la cabeza
                pos_x = self.rect.left - 7
            pos_y = self.y + self.radius / 7
        else:
            # ── IDLE ──
            boot = self.boot_idle_img
            pos_x = self.x                           # centrado con la cabeza
            pos_y = self.rect.bottom + self.boot_h / 7  # justo debajo

        rect = boot.get_rect(center=(int(pos_x), int(pos_y)))
        surface.blit(boot, rect)
