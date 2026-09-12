"""Expo Heads UNO — renderizado de cancha y estadio (v4 — estilo referencia)."""

import pygame
import random
import config as C


def _draw_sky(surface):
    """Cielo con degradé suave."""
    for y in range(220):
        t = y / 220
        r = int(160 + t * 30)
        g = int(195 + t * 15)
        b = int(220 - t * 20)
        pygame.draw.line(surface, (r, g, b), (0, y), (C.WINDOW_W, y))


def _draw_stadium(surface):
    """Tribuna con público en colores OPACOS/apagados, más espaciado."""
    W = C.WINDOW_W

    # Fondo de la tribuna — gris claro, más suave
    pygame.draw.rect(surface, (165, 160, 155), (0, 100, W, 295))

    # Tiers (separadores de la tribuna)
    pygame.draw.rect(surface, (185, 180, 175), (0, 100, W, 6))
    pygame.draw.rect(surface, (150, 145, 140), (0, 220, W, 5))
    pygame.draw.rect(surface, (140, 135, 130), (0, 320, W, 5))

    # Baranda/separador antes de la cancha
    pygame.draw.rect(surface, (130, 125, 120), (0, 355, W, 4))

    rng = random.Random(42)

    # Colores de camisetas MUY APAGADOS/OPACOS
    shirt_colors = [
        (140, 160, 180), (100, 130, 100), (170, 150, 130),
        (200, 195, 190), (130, 140, 150), (160, 140, 120),
        (120, 150, 160), (150, 130, 140), (170, 170, 160),
        (140, 120, 130), (160, 170, 150), (180, 170, 170),
    ]
    skin_tones = [(220, 195, 170), (200, 175, 150),
                  (180, 155, 130), (210, 185, 160)]

    # Fila lejana (chiquita, bien espaciada)
    for row_y in range(115, 215, 16):
        for x in range(15, W - 15, 18):
            sc = rng.choice(shirt_colors)
            sk = rng.choice(skin_tones)
            hx = x + rng.randint(-2, 2)
            pygame.draw.circle(surface, sk, (hx, row_y), 4)
            pygame.draw.rect(surface, sc, (hx - 4, row_y + 4, 8, 8))

    # Fila media (más espaciada)
    for row_y in range(230, 315, 18):
        for x in range(12, W - 12, 20):
            sc = rng.choice(shirt_colors)
            sk = rng.choice(skin_tones)
            hx = x + rng.randint(-3, 3)
            pygame.draw.circle(surface, sk, (hx, row_y), 5)
            pygame.draw.rect(surface, sc, (hx - 5, row_y + 5, 10, 9))

    # Fila cercana (más grande, bien espaciada)
    for row_y in range(330, 355, 20):
        for x in range(15, W - 15, 24):
            sc = rng.choice(shirt_colors)
            sk = rng.choice(skin_tones)
            hx = x + rng.randint(-4, 4)
            pygame.draw.circle(surface, sk, (hx, row_y), 6)
            pygame.draw.rect(surface, sc, (hx - 6, row_y + 6, 12, 10))


def _draw_banners(surface):
    """Carteles grandes y visibles."""
    W = C.WINDOW_W

    # Banner principal UNO — MÁS GRANDE
    banner_h = 22
    banner = pygame.Rect(220, 215, 520, banner_h)
    pygame.draw.rect(surface, C.UNO_BLUE, banner)
    pygame.draw.rect(surface, (25, 120, 165), banner, 1)
    font_banner = pygame.font.SysFont("monospace", 16, bold=True)
    txt = font_banner.render("UNO    Universidad Nacional del Oeste", True, C.WHITE)
    tw = txt.get_width()
    surface.blit(txt, (220 + (520 - tw) // 2, 217))

    # Carteles publicitarios — pegados al borde cancha/tribuna
    y = C.PITCH_TOP - 18
    h = 18
    pygame.draw.rect(surface, C.AD_BOARD_BG, (0, y, W, h))

    ads = [
        (0, 240, C.UNO_BLUE, "UNO"),
        (240, 260, C.EXPO_RED, "EXPO HEADS"),
        (500, 220, (55, 70, 55), "INFORMÁTICA"),
        (720, 240, C.UNO_BLUE, "UNO"),
    ]
    font_ad = pygame.font.SysFont("monospace", 14, bold=True)
    for x, w, color, text in ads:
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (50, 50, 50), rect, 1)
        label = font_ad.render(text, True, C.WHITE)
        lw = label.get_width()
        surface.blit(label, (x + (w - lw) // 2, y + 3))


def _draw_grass(surface):
    """Pasto con franjas y tonos más vivos/variados como cancha real."""
    stripe_h = 22
    y = C.PITCH_TOP
    i = 0
    while y < C.PITCH_BOTTOM:
        # Alternar entre verde claro y verde más oscuro
        if i % 2 == 0:
            color = (82, 160, 55)
        else:
            color = (72, 145, 48)
        h = min(stripe_h, C.PITCH_BOTTOM - y)
        pygame.draw.rect(surface, color, (0, y, C.WINDOW_W, h))
        y += stripe_h
        i += 1


def _draw_field_lines(surface):
    """Líneas de cancha con perspectiva horizontal — elipse ACHATADA."""
    W = C.WINDOW_W
    top = C.PITCH_TOP + 3
    bot = C.GROUND_Y
    mid_x = W // 2
    mid_y = (top + bot) // 2
    pitch_h = bot - top

    line_color = (255, 255, 255, 100)

    # Línea superior
    ls = pygame.Surface((W - 40, 2), pygame.SRCALPHA)
    ls.fill(line_color)
    surface.blit(ls, (20, top))

    # Línea inferior
    surface.blit(ls, (20, bot - 2))

    # Línea central vertical
    cl = pygame.Surface((2, bot - top), pygame.SRCALPHA)
    cl.fill(line_color)
    surface.blit(cl, (mid_x - 1, top))

    # Círculo central — ELIPSE HORIZONTAL (achatada, da sensación de perspectiva)
    ellipse_w = min(120, W // 5)
    ellipse_h = min(pitch_h - 10, 50)  # bien achatada
    el_surf = pygame.Surface((ellipse_w, ellipse_h), pygame.SRCALPHA)
    pygame.draw.ellipse(el_surf, line_color,
                        (0, 0, ellipse_w, ellipse_h), 2)
    surface.blit(el_surf, (mid_x - ellipse_w // 2, mid_y - ellipse_h // 2))

    # Punto central
    dot_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(dot_surf, line_color, (3, 3), 3)
    surface.blit(dot_surf, (mid_x - 3, mid_y - 3))

    # Áreas de portería (rectángulos chicos a cada lado)
    area_w = 65
    area_h = pitch_h - 12

    # Área izquierda
    area_surf = pygame.Surface((area_w, area_h), pygame.SRCALPHA)
    pygame.draw.rect(area_surf, line_color, (0, 0, area_w, area_h), 2)
    surface.blit(area_surf, (2, top + 6))

    # Área chica izquierda
    small_w = 30
    small_h = area_h - 30
    sa_surf = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
    pygame.draw.rect(sa_surf, line_color, (0, 0, small_w, small_h), 2)
    surface.blit(sa_surf, (2, top + 6 + 15))

    # Área derecha
    surface.blit(area_surf, (W - area_w - 2, top + 6))

    # Área chica derecha
    surface.blit(sa_surf, (W - small_w - 2, top + 6 + 15))


def _draw_goal(surface, x, is_left):
    """Arco cargado desde sprite de referencia."""
    top = C.GOAL_TOP
    bot = C.GOAL_BOTTOM
    goal_h = bot - top
    import os
    base = os.path.dirname(os.path.abspath(__file__))

    if is_left:
        path = os.path.join(base, "assets", "sprites", "goal_left.png")
    else:
        path = os.path.join(base, "assets", "sprites", "goal_right.png")

    try:
        img = pygame.image.load(path).convert_alpha()
        # Escalar al tamaño del arco en nuestra cancha
        goal_w = C.GOAL_WIDTH + 10
        img = pygame.transform.smoothscale(img, (goal_w, goal_h))

        if is_left:
            surface.blit(img, (0, top))
        else:
            surface.blit(img, (C.WINDOW_W - goal_w, top))
    except Exception:
        # Fallback
        w = C.GOAL_WIDTH
        pc = (90, 95, 100)
        if is_left:
            pygame.draw.rect(surface, pc, (x + w - 5, top, 5, bot - top))
            pygame.draw.rect(surface, pc, (x, top, w, 5))
        else:
            pygame.draw.rect(surface, pc, (x, top, 5, bot - top))
            pygame.draw.rect(surface, pc, (x, top, w, 5))


def build_pitch_surface():
    surf = pygame.Surface((C.WINDOW_W, C.WINDOW_H))
    surf.fill((0, 0, 0))
    _draw_sky(surf)
    _draw_stadium(surf)
    _draw_banners(surf)
    _draw_grass(surf)
    _draw_field_lines(surf)
    _draw_goal(surf, 0, is_left=True)
    _draw_goal(surf, C.WINDOW_W - C.GOAL_WIDTH, is_left=False)
    return surf
