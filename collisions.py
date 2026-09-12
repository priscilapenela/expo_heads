"""Expo Heads UNO — colisiones.

Basado en el método reflect() de lopta.py del juego de referencia:
- Pelota a nivel del piso + tocando jugador → hereda vel.x * 2
- Pelota más arriba → empuje con fuerza basada en masa
- Patada → velocidades escalonadas (nogica.py)
"""

import math
import config as C


def check_ball_head_collision(ball, player) -> bool:
    """Colisión pelota-cabeza basada en reflect() de la referencia."""
    dx = ball.x - player.x
    dy = ball.y - player.y
    dist = math.sqrt(dx * dx + dy * dy)
    min_dist = ball.radius + player.radius + 1

    if dist >= min_dist or dist == 0:
        return False

    # ── Separar objetos ──
    nx = dx / dist
    ny = dy / dist
    overlap = min_dist - dist
    ball.x += nx * (overlap + 1)
    ball.y += ny * (overlap + 1)

    # ── Lógica de la referencia (reflect method) ──
    # Verificar si la pelota está a nivel del piso (cerca del ground)
    near_ground = ball.y + ball.radius >= C.GROUND_Y - 5

    if near_ground:
        # Pelota rodando en el piso — hereda velocidad del jugador
        # Referencia: self.vel.x = igr.vel.x * 2
        if ball.y >= player.y:
            # Pelota está abajo/al nivel del jugador
            ball.vx = player.vx * 2.5
            if ball.x >= player.x:
                ball.x += 3
            else:
                ball.x -= 3
            if ball.vy > 0:
                ball.vy = 0
        else:
            # Pelota encima pero cerca del piso
            ball.vx = player.vx * 2
            if ball.x >= player.x:
                ball.x += 3
                ball.vx += 3
            else:
                ball.x -= 3
                ball.vx -= 3
            if ball.vy > 0:
                ball.vy = -2
    else:
        # ── Pelota en el aire — cabezazo con física ──
        # Referencia: empuja según posición relativa
        player_mass = 100

        if ball.x <= player.x:
            ball.x -= 2
            ball.vx -= 8 * player_mass / 100
        else:
            ball.x += 2
            ball.vx += 8 * player_mass / 100

        if ball.y <= player.y:
            ball.y -= 2
            ball.vy -= 6
        else:
            ball.y += 1

    # Limitar velocidad
    ball.vx = max(-25, min(25, ball.vx))
    ball.vy = max(-25, min(25, ball.vy))

    return True


def check_ball_kick_collision(ball, player) -> bool:
    """Colisión patada-pelota (nogica.py)."""
    if not player.is_kicking:
        return False

    foot_x, foot_y = player.get_foot_pos()

    dx = ball.x - foot_x
    dy = ball.y - foot_y
    dist = math.sqrt(dx * dx + dy * dy)

    kick_range = player.boot_w * 0.8 + ball.radius

    if dist > kick_range:
        return False

    # Verificar lado correcto
    if player.num == 1 and ball.x < player.x - 5:
        return False
    if player.num == 2 and ball.x > player.x + 5:
        return False

    # Velocidades escalonadas (como nogica.py)
    body_dist = abs(ball.x - player.x)
    direction = 1 if player.num == 1 else -1

    if body_dist > player.radius + 20 or ball.y > player.y + player.radius:
        ball.vx = 20 * direction
        ball.vy = -4
    elif body_dist > player.radius + 10:
        ball.vx = 16 * direction
        ball.vy = -8
    elif body_dist > player.radius:
        ball.vx = 12 * direction
        ball.vy = -11
    elif body_dist > player.radius - 10:
        ball.vx = 8 * direction
        ball.vy = -14
    else:
        ball.vx = 4 * direction
        ball.vy = -18

    return True


def check_player_player_collision(p1, p2) -> None:
    """Colisión entre jugadores — empuje (referencia)."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    dist = math.sqrt(dx * dx + dy * dy)
    min_dist = p1.radius + p2.radius

    if dist < min_dist and dist > 0:
        nx = dx / dist
        ny = dy / dist
        overlap = min_dist - dist

        # Separar y empujar (como referencia: vel.x = ±7, pos ±5)
        p1.x -= nx * overlap * 0.5
        p2.x += nx * overlap * 0.5

        p1.vx = -5 if dx > 0 else 5
        p2.vx = 5 if dx > 0 else -5
