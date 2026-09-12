"""Expo Heads UNO — motor de juego adaptado del juego de referencia.

Wrappea los módulos originales (igrac, nogica, lopta, gol, platforma)
sin modificarlos, adaptando paths y configuración.
"""

import pygame
import os
import math

vec = pygame.math.Vector2

# ── Paths ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "assets", "ref_images")
SND_DIR = os.path.join(BASE_DIR, "assets", "sounds")


def img_path(name):
    return os.path.join(IMG_DIR, name)


# ══════════════════════════════════════════════════════════
# PLATFORMA (ground)
# ══════════════════════════════════════════════════════════
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, y))


# ══════════════════════════════════════════════════════════
# GOL (goal)
# ══════════════════════════════════════════════════════════
class Goal(pygame.sprite.Sprite):
    def __init__(self, width, height, side, screen_w, screen_h, ground_h):
        """side: 1=left, 2=right"""
        super().__init__()
        img_name = "gol111.png" if side == 1 else "gol222.png"
        self.image = pygame.image.load(img_path(img_name)).convert_alpha()
        self.image = pygame.transform.smoothscale(self.image, (width, height))
        self.side = side
        self.width = width
        self.height = height

        if side == 1:
            self.rect = self.image.get_rect(
                center=(width // 2, screen_h - ground_h - height // 2))
        else:
            self.rect = self.image.get_rect(
                center=(screen_w - width // 2, screen_h - ground_h - height // 2))


    def draw(self, surface):
        surface.blit(self.image, self.rect)


# ══════════════════════════════════════════════════════════
# LOPTA (ball) — simplified from reference
# ══════════════════════════════════════════════════════════
class Ball(pygame.sprite.Sprite):
    def __init__(self, pos, radius, elasticnost=0.65):
        super().__init__()
        self.pos = vec(pos)
        self.vel = vec(0, 0)
        self.acc = vec(0, 0)
        self.radius = radius
        self.masa = 5
        self.elasticnost = elasticnost
        self.zadnji_diro = -1

        raw = pygame.image.load(img_path("lopta.png")).convert_alpha()
        self.image = pygame.transform.smoothscale(raw, (radius * 2, radius * 2))
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update_move(self, gravitacija, otpor_zraka, fric, platform, screen_w):
        self.acc = vec(0, gravitacija)

        # Friction: air vs ground
        if self.rect.bottom + 1 < platform.rect.top:
            self.acc.x += self.vel.x * otpor_zraka
        else:
            self.acc.x += self.vel.x * fric

        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        # Wall bounces
        if self.pos.x + self.radius >= screen_w:
            self.vel.x *= -self.elasticnost
            self.acc.x *= -self.elasticnost
            self.pos.x = screen_w - self.radius - 1

        if self.pos.x - self.radius < 0:
            self.vel.x *= -self.elasticnost
            self.acc.x *= -self.elasticnost
            self.pos.x = self.radius + 1

        if self.rect.top < 0:
            self.vel.y *= -self.elasticnost
            self.acc.y *= -self.elasticnost
            self.pos.y = self.radius + 1

        self.rect.center = self.pos

        # Clamp velocity
        self.vel.x = max(-50, min(50, self.vel.x))
        self.vel.y = max(-50, min(50, self.vel.y))

    def update_col(self, platform):
        """Ground collision."""
        if self.vel.y > 0:
            if self.rect.bottom >= platform.rect.top:
                self.pos.y = platform.rect.top - self.radius + 1
                self.vel.y *= -self.elasticnost * 0.8
                if abs(self.vel.y) < 0.5:
                    self.vel.y = 0
                self.rect.center = self.pos

    def reflect(self, player, platform):
        """Ball-player head collision (from reference reflect method)."""
        dist = self.pos.distance_to(player.pos)
        if dist > self.radius + player.radius + 1:
            return False

        if platform.rect.top - self.rect.center[1] <= self.radius + 1:
            # Ball near ground level
            if platform.rect.top - player.rect.center[1] > player.radius:
                # Player is in the air
                if self.pos.x >= player.pos.x:
                    self.pos.x += 10
                    self.vel.x += 10 * player.masa / 100
                else:
                    self.pos.x -= 10
                    self.vel.x -= 10 * player.masa / 100
            else:
                # Both on ground — inherit player velocity
                self.vel.x = player.vel.x * 2
                if self.pos.x >= player.pos.x:
                    self.pos.x += 3
                    if self.vel.y > 0:
                        self.vel.y = 0
                else:
                    self.pos.x -= 3
                    if self.vel.y > 0:
                        self.vel.y = 0
        else:
            # Ball in the air — push away
            if self.pos.x <= player.pos.x:
                self.pos.x -= 2
            else:
                self.pos.x += 2

            if self.pos.y <= player.pos.y:
                self.pos.y -= 2
            else:
                self.pos.y += 1

        self.rect.center = self.pos
        self.vel.x = max(-50, min(50, self.vel.x))
        self.vel.y = max(-50, min(50, self.vel.y))
        return True

    def is_goal(self, goal, platform):
        """Check if ball entered the goal."""
        if self.rect.bottom >= platform.rect.top - 5:
            if goal.side == 1 and self.rect.right < goal.rect.right:
                return True
            if goal.side == 2 and self.rect.left > goal.rect.left:
                return True
        return False

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# ══════════════════════════════════════════════════════════
# NOGICA (foot/kick) — from reference
# ══════════════════════════════════════════════════════════
class Foot:
    def __init__(self, player, boot_w, boot_h):
        self.player = player
        self.boot_w = boot_w
        self.boot_h = boot_h
        self.delay = 0

        raw = pygame.image.load(img_path("nogica1.png")).convert_alpha()

        if player.side == 1:
            raw = pygame.transform.flip(raw, True, False)

        self.img_idle = pygame.transform.smoothscale(raw, (boot_w, boot_h))

        if player.side == 1:
            self.img_kick = pygame.transform.rotate(self.img_idle, 90)
        else:
            self.img_kick = pygame.transform.rotate(self.img_idle, -90)

    def handle_kick(self):
        if self.delay == 0:
            self.delay = 1

    def update(self):
        if self.delay > 0:
            self.delay += 1
            if self.delay >= 12:
                self.delay = 0

    @property
    def is_kicking(self):
        return 1 <= self.delay <= 4

    def kick_ball(self, ball):
        """Apply kick force to ball (from reference nogica update_col)."""
        if not self.is_kicking:
            return False

        p = self.player
        kick_range = self.boot_w + ball.radius

        # Check if ball is on the correct side and in range
        if p.side == 1:
            if ball.pos.x < p.pos.x:
                return False
            if ball.rect.left - p.rect.right > kick_range:
                return False

            # Velocity based on distance (from reference)
            hdist = ball.rect.left - p.rect.right
            if hdist > 30 or ball.pos.y > p.rect.bottom:
                ball.vel.x = 22
                ball.vel.y = -5
            elif hdist > 20:
                ball.vel.x = 18
                ball.vel.y = -9
            elif hdist > 10:
                ball.vel.x = 14
                ball.vel.y = -12
            elif hdist > 0:
                ball.vel.x = 9
                ball.vel.y = -15
            else:
                ball.vel.x = 4
                ball.vel.y = -18
        else:
            if ball.pos.x > p.pos.x:
                return False
            if p.rect.left - ball.rect.right > kick_range:
                return False

            hdist = p.rect.left - ball.rect.right
            if hdist > 30 or ball.pos.y > p.rect.bottom:
                ball.vel.x = -22
                ball.vel.y = -5
            elif hdist > 20:
                ball.vel.x = -18
                ball.vel.y = -9
            elif hdist > 10:
                ball.vel.x = -14
                ball.vel.y = -12
            elif hdist > 0:
                ball.vel.x = -9
                ball.vel.y = -15
            else:
                ball.vel.x = -4
                ball.vel.y = -18

        ball.zadnji_diro = p
        return True

    def get_pos(self):
        p = self.player
        if self.delay > 0:
            if p.side == 1:
                return (p.rect.right + 7, p.pos.y + p.radius / 7)
            else:
                return (p.rect.left - 7, p.pos.y + p.radius / 7)
        else:
            return (p.pos.x, p.rect.bottom + self.boot_h / 7)

    def draw(self, surface):
        p = self.player
        if self.delay > 0:
            img = self.img_kick
            if p.side == 1:
                pos = (p.rect.right + 7, p.pos.y + p.radius / 7)
            else:
                pos = (p.rect.left - 7, p.pos.y + p.radius / 7)
        else:
            img = self.img_idle
            pos = (p.pos.x, p.rect.bottom + self.boot_h / 7)

        rect = img.get_rect(center=(int(pos[0]), int(pos[1])))
        surface.blit(img, rect)


# ══════════════════════════════════════════════════════════
# IGRAC (player) — from reference
# ══════════════════════════════════════════════════════════
class Player(pygame.sprite.Sprite):
    def __init__(self, pos, radius, side, acc=0.6, jump=10.0, head_img=None):
        """side: 1=left player, 2=right player"""
        super().__init__()
        self.pos = vec(pos)
        self.vel = vec(0, 0)
        self.acc = vec(0, 0)
        self.radius = radius
        self.side = side
        self.ACC = acc
        self.SKOK = jump
        self.masa = 100

        # Head image
        if head_img:
            self.img = pygame.image.load(head_img).convert_alpha()
        else:
            self.img = pygame.image.load(img_path("igrac1.png")).convert_alpha()

        if side == 1:
            self.img = pygame.transform.flip(self.img, True, False)

        self.image = pygame.transform.smoothscale(self.img, (radius * 2, radius * 2))
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update_move(self, keys, controls, fric, platform, screen_w, gravitacija):
        self.acc = vec(0, gravitacija + 0.07)

        # Check if on ground (proximity-based, not sprite collision)
        on_ground = self.pos.y + self.radius >= platform.rect.top - 2 if hasattr(platform, 'rect') else False
        # If platform is a Group, check against first sprite
        if not on_ground and isinstance(platform, pygame.sprite.Group):
            for p in platform:
                if self.pos.y + self.radius >= p.rect.top - 2:
                    on_ground = True
                    break

        # Movement
        if keys[controls["left"]]:
            self.acc.x = -self.ACC
        if keys[controls["right"]]:
            self.acc.x = self.ACC
        if keys[controls["jump"]] and on_ground:
            self.vel.y = -self.SKOK

        # Friction
        self.acc.x += self.vel.x * fric
        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        # Walls
        if self.rect.right >= screen_w:
            self.vel.x *= -1
            self.pos.x = screen_w - self.radius - 1
        if self.rect.left < 0:
            self.vel.x *= -1
            self.pos.x = self.radius + 1

        self.rect.center = self.pos

    def update_col(self, platform):
        """Ground collision."""
        hits = pygame.sprite.spritecollide(self, platform, False)
        if hits and self.vel.y > 0:
            self.pos.y = hits[0].rect.top - self.radius
            self.vel.y = 0
            self.rect.center = self.pos

    def draw(self, surface):
        surface.blit(self.image, self.rect)
