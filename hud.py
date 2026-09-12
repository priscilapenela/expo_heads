"""Expo Heads UNO — HUD (marcador, timer, nombres)."""

import pygame
import config as C


class HUD:
    def __init__(self):
        self.font_big = pygame.font.SysFont("monospace", 48, bold=True)
        self.font_med = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_sm = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_hud = pygame.font.SysFont("monospace", 28, bold=True)

    def draw(self, surface: pygame.Surface, p1_name: str, p2_name: str,
             p1_score: int, p2_score: int, time_left: float) -> None:
        W = C.WINDOW_W

        # Barra superior
        hud_bar = pygame.Surface((W, 42), pygame.SRCALPHA)
        hud_bar.fill((*C.HUD_BG, 230))
        surface.blit(hud_bar, (0, 0))
        pygame.draw.line(surface, C.YELLOW, (0, 41), (W, 41), 2)

        # Nombre P1
        p1_label = self.font_med.render(p1_name, True, C.WHITE)
        surface.blit(p1_label, (55, 8))
        p1_tag = self.font_sm.render("P1", True, (150, 150, 180))
        surface.blit(p1_tag, (55, 28))

        # Nombre P2
        p2_label = self.font_med.render(p2_name, True, C.WHITE)
        p2_w = p2_label.get_width()
        surface.blit(p2_label, (W - 55 - p2_w, 8))
        p2_tag = self.font_sm.render("P2", True, (150, 150, 180))
        surface.blit(p2_tag, (W - 72, 28))

        # Marcador
        score1 = self.font_big.render(str(p1_score), True, C.WHITE)
        surface.blit(score1, (200, 0))

        dash = self.font_big.render("-", True, C.YELLOW)
        surface.blit(dash, (W // 2 - 10, 0))

        score2 = self.font_big.render(str(p2_score), True, C.WHITE)
        s2_w = score2.get_width()
        surface.blit(score2, (W - 200 - s2_w, 0))

        # Timer
        minutes = int(time_left) // 60
        seconds = int(time_left) % 60
        time_str = f"{minutes}:{seconds:02d}"
        timer_rect = pygame.Rect(W // 2 - 60, 4, 120, 34)
        pygame.draw.rect(surface, (40, 40, 50), timer_rect)
        pygame.draw.rect(surface, C.YELLOW, timer_rect, 1)
        time_label = self.font_hud.render(time_str, True, C.YELLOW)
        tw = time_label.get_width()
        surface.blit(time_label, (W // 2 - tw // 2, 5))
