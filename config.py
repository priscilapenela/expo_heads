"""Expo Heads UNO — configuración global."""

# ── Ventana ──────────────────────────────────────────────
WINDOW_W = 960
WINDOW_H = 540
FPS = 60
TITLE = "Expo Heads UNO"

# ── Cancha ───────────────────────────────────────────────
PITCH_TOP = 365          # balance entre estética plana y espacio jugable
PITCH_BOTTOM = WINDOW_H
GROUND_Y = WINDOW_H - 8

# ── Arcos ────────────────────────────────────────────────
GOAL_WIDTH = 60
GOAL_DEPTH = 28
GOAL_TOP = PITCH_TOP + 12
GOAL_BOTTOM = GROUND_Y

# ── Física ───────────────────────────────────────────────
GRAVITY = 0.4
BALL_BOUNCE = 0.75
BALL_FRICTION = 0.99
BALL_RADIUS = 14

# ── Jugadores ────────────────────────────────────────────
PLAYER_HEAD_RADIUS = 30
PLAYER_SPEED = 4
PLAYER_JUMP_FORCE = -9
PLAYER_FOOT_LENGTH = 40

# ── Partido ──────────────────────────────────────────────
MATCH_TIME = 90  # segundos
GOALS_TO_WIN = 5

# ── Colores ──────────────────────────────────────────────
SKY_TOP = (85, 155, 225)
SKY_BOTTOM = (115, 175, 210)
GRASS_LIGHT = (45, 105, 30)
GRASS_DARK = (38, 88, 24)
STADIUM_BG = (80, 70, 65)
STADIUM_TIER = (100, 90, 82)
AD_BOARD_BG = (30, 30, 30)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 220, 60)
UNO_BLUE = (32, 144, 192)
EXPO_RED = (200, 40, 80)
HUD_BG = (20, 20, 30)
