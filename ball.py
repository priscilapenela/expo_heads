"""Expo Heads UNO — pelota con física."""

import pygame
import math
import config as C


class Ball:
    def __init__(self):
        self.reset()
        self.sprite = self._build_sprite()

    def reset(self) -> None:
        """Posición y velocidad inicial (centro de la cancha, cae)."""
        self.x = C.WINDOW_W / 2
        self.y = C.PITCH_TOP + 40
        self.vx = 0.0
        self.vy = 0.0
        self.radius = C.BALL_RADIUS

    def _build_sprite(self) -> pygame.Surface:
        """Carga la pelota clásica desde sprite o la genera."""
        size = self.radius * 2 + 4
        try:
            # Usar el sprite de referencia
            import os
            ball_path = os.path.join(os.path.dirname(__file__),
                                     "assets", "sprites", "ball.png")
            img = pygame.image.load(ball_path).convert_alpha()
            return pygame.transform.smoothscale(img, (size, size))
        except Exception:
            # Fallback: dibujar una pelota simple
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            cx, cy = size // 2, size // 2
            r = self.radius
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), r)
            pr = int(r * 0.35)
            for i in range(5):
                a = math.radians(i * 72 - 90)
                pts = []
                for j in range(5):
                    sa = math.radians(i * 72 + j * 72 - 90)
                    pts.append((cx + int(pr * math.cos(sa)),
                                cy + int(pr * math.sin(sa))))
                pygame.draw.polygon(surf, (25, 25, 25), pts)
            pygame.draw.circle(surf, (20, 20, 20), (cx, cy), r, 2)
            return surf

    def update(self) -> None:
        """Actualiza posición aplicando gravedad, velocidad y rebotes."""
        # Gravedad
        self.vy += C.GRAVITY

        # Fricción (referencia: OTPOR_ZRAKA en aire, FRIC en piso)
        on_ground = self.y + self.radius >= C.GROUND_Y - 2
        if on_ground:
            # Fricción del piso (más fuerte)
            self.vx *= 0.94
        else:
            # Resistencia del aire (más suave — mantiene impulso)
            self.vx *= 0.995
            self.vy *= 0.998

        # Mover
        self.x += self.vx
        self.y += self.vy

        # ── Rebotes (con elasticidad como referencia) ──
        elasticidad = C.BALL_BOUNCE

        # Piso
        if self.y + self.radius > C.GROUND_Y:
            self.y = C.GROUND_Y - self.radius
            self.vy = -self.vy * elasticidad * 0.8
            if abs(self.vy) < 0.8:
                self.vy = 0

        # Techo
        if self.y - self.radius < C.PITCH_TOP - 40:
            self.y = C.PITCH_TOP - 40 + self.radius
            self.vy = -self.vy * elasticidad

        # Pared izquierda
        if self.x - self.radius < 0:
            if C.GOAL_TOP < self.y < C.GOAL_BOTTOM:
                pass
            else:
                self.x = self.radius + 1
                self.vx = -self.vx * elasticidad

        # Pared derecha
        if self.x + self.radius > C.WINDOW_W:
            if C.GOAL_TOP < self.y < C.GOAL_BOTTOM:
                pass
            else:
                self.x = C.WINDOW_W - self.radius - 1
                self.vx = -self.vx * elasticidad

        # Limitar velocidad máxima (referencia: max 75)
        self.vx = max(-25, min(25, self.vx))
        self.vy = max(-25, min(25, self.vy))

        # ── Rebote con los postes del arco ──
        self._check_post_collision()

    def _check_post_collision(self) -> None:
        """Rebote contra los travesaños y postes de los arcos."""
        for goal_x, post_x in [(0, C.GOAL_WIDTH), (C.WINDOW_W - C.GOAL_WIDTH, C.WINDOW_W - C.GOAL_WIDTH)]:
            is_left = goal_x == 0

            # Travesaño superior
            if (goal_x < self.x < goal_x + C.GOAL_WIDTH and
                    abs(self.y - self.radius - C.GOAL_TOP) < 5 and
                    self.vy < 0):
                self.vy = abs(self.vy) * C.BALL_BOUNCE
                self.y = C.GOAL_TOP + self.radius + 2

            # Travesaño inferior
            if (goal_x < self.x < goal_x + C.GOAL_WIDTH and
                    abs(self.y + self.radius - C.GOAL_BOTTOM) < 5 and
                    self.vy > 0):
                self.vy = -abs(self.vy) * C.BALL_BOUNCE
                self.y = C.GOAL_BOTTOM - self.radius - 2

            # Poste vertical
            if is_left:
                px = C.GOAL_WIDTH
            else:
                px = C.WINDOW_W - C.GOAL_WIDTH

            if (C.GOAL_TOP < self.y < C.GOAL_BOTTOM and
                    abs(self.x - px) < self.radius + 3):
                if is_left and self.vx < 0:
                    self.vx = abs(self.vx) * C.BALL_BOUNCE
                    self.x = px + self.radius + 2
                elif not is_left and self.vx > 0:
                    self.vx = -abs(self.vx) * C.BALL_BOUNCE
                    self.x = px - self.radius - 2

    def is_goal_left(self) -> bool:
        """¿Entró al arco izquierdo?"""
        return (self.x + self.radius < 0 and
                C.GOAL_TOP < self.y < C.GOAL_BOTTOM)

    def is_goal_right(self) -> bool:
        """¿Entró al arco derecho?"""
        return (self.x - self.radius > C.WINDOW_W and
                C.GOAL_TOP < self.y < C.GOAL_BOTTOM)

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja la pelota y su sombra."""
        # Sombra en el piso
        shadow_alpha = max(30, 80 - int((C.GROUND_Y - self.y) * 0.3))
        shadow_w = int(self.radius * 1.5)
        shadow_h = 6
        shadow_surf = pygame.Surface((shadow_w * 2, shadow_h * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, shadow_alpha),
                           (0, 0, shadow_w * 2, shadow_h * 2))
        surface.blit(shadow_surf, (int(self.x) - shadow_w,
                                    C.GROUND_Y - shadow_h))

        # Pelota
        sprite_rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.sprite, sprite_rect)
