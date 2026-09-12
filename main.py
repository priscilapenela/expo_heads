"""Expo Heads UNO — main game loop usando motor de referencia."""

import pygame
import sys
from pitch import build_pitch_surface
from hud import HUD
from game_engine import Platform, Goal, Ball, Player, Foot
import config as C

# ── Configuración del juego ──
SCREEN_W = C.WINDOW_W
SCREEN_H = C.WINDOW_H
GRAVITY = 0.5
FRIC_PLAYER = -0.12
FRIC_BALL_AIR = -0.02       # resistencia aire (OTPOR_ZRAKA)
FRIC_BALL_GROUND = -0.08    # fricción piso (FRIC)
GROUND_H = SCREEN_H - C.GROUND_Y  # altura del piso
GOAL_W = 65
GOAL_H = C.GOAL_BOTTOM - C.GOAL_TOP
PLAYER_RADIUS = 30
BALL_RADIUS = 14
MATCH_TIME = 60  # 1 minuto como el juego de referencia


def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(C.TITLE)
    clock = pygame.time.Clock()

    # ── Fondo ──
    pitch_surface = build_pitch_surface()

    # ── Sonidos ──
    sounds = {}
    for name in ["dodir", "skok", "veselje", "kraj"]:
        try:
            sounds[name] = pygame.mixer.Sound(f"assets/sounds/{name}.ogg")
            sounds[name].set_volume(0.4)
        except Exception:
            sounds[name] = None

    # ── Plataforma (piso) ──
    platform = Platform(0, C.GROUND_Y, SCREEN_W, GROUND_H)
    platform_group = pygame.sprite.Group(platform)

    # ── Arcos ──
    goal_left = Goal(GOAL_W, GOAL_H, 1, SCREEN_W, SCREEN_H, GROUND_H)
    goal_right = Goal(GOAL_W, GOAL_H, 2, SCREEN_W, SCREEN_H, GROUND_H)

    # ── Jugadores ──
    p1_start = (SCREEN_W * 0.25, C.GROUND_Y - PLAYER_RADIUS)
    p2_start = (SCREEN_W * 0.75, C.GROUND_Y - PLAYER_RADIUS)

    p1 = Player(p1_start, PLAYER_RADIUS, side=1, acc=0.6, jump=10.0)
    p2 = Player(p2_start, PLAYER_RADIUS, side=2, acc=0.6, jump=10.0)

    p1_controls = {"left": pygame.K_a, "right": pygame.K_d,
                   "jump": pygame.K_w, "kick": pygame.K_s}
    p2_controls = {"left": pygame.K_LEFT, "right": pygame.K_RIGHT,
                   "jump": pygame.K_UP, "kick": pygame.K_DOWN}

    # ── Pies ──
    boot_w = int(PLAYER_RADIUS * 1.3)
    boot_h = int(PLAYER_RADIUS * 0.65)
    foot1 = Foot(p1, boot_w, boot_h)
    foot2 = Foot(p2, boot_w, boot_h)

    # ── Pelota ──
    ball_start = (SCREEN_W / 2, C.PITCH_TOP + 30)
    ball = Ball(ball_start, BALL_RADIUS)

    # ── HUD ──
    hud = HUD()

    # ── Estado ──
    p1_score = 0
    p2_score = 0
    time_left = MATCH_TIME
    goal_pause = 0
    game_over = False

    def reset_positions():
        p1.pos = pygame.math.Vector2(p1_start)
        p1.vel = pygame.math.Vector2(0, 0)
        p1.rect.center = p1.pos
        p2.pos = pygame.math.Vector2(p2_start)
        p2.vel = pygame.math.Vector2(0, 0)
        p2.rect.center = p2.pos
        ball.pos = pygame.math.Vector2(ball_start)
        ball.vel = pygame.math.Vector2(0, 0)
        ball.rect.center = ball.pos
        foot1.delay = 0
        foot2.delay = 0

    running = True
    while running:
        dt = clock.tick(C.FPS) / 1000.0

        # ── Eventos ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    reset_positions()
                    p1_score = 0
                    p2_score = 0
                    time_left = MATCH_TIME
                    game_over = False
                elif event.key == pygame.K_SPACE and game_over:
                    reset_positions()
                    p1_score = 0
                    p2_score = 0
                    time_left = MATCH_TIME
                    game_over = False

                # Kick events
                if event.key == p1_controls["kick"] and foot1.delay == 0:
                    foot1.handle_kick()
                if event.key == p2_controls["kick"] and foot2.delay == 0:
                    foot2.handle_kick()

        # ── Game Over ──
        if game_over:
            screen.blit(pitch_surface, (0, 0))
            hud.draw(screen, "TITAN", "RIVAL", p1_score, p2_score, 0)

            font_big = pygame.font.SysFont("monospace", 40, bold=True)
            font_sm = pygame.font.SysFont("monospace", 16, bold=True)

            if p1_score > p2_score:
                winner = "TITAN GANA!"
            elif p2_score > p1_score:
                winner = "RIVAL GANA!"
            else:
                winner = "EMPATE!"

            txt = font_big.render(winner, True, (255, 255, 60))
            screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, SCREEN_H // 2 - 50))

            restart = font_sm.render("ESPACIO para reiniciar", True, (200, 200, 200))
            screen.blit(restart, (SCREEN_W // 2 - restart.get_width() // 2, SCREEN_H // 2 + 10))

            pygame.display.flip()
            continue

        # ── Pausa de gol ──
        if goal_pause > 0:
            goal_pause -= 1
            screen.blit(pitch_surface, (0, 0))
            goal_left.draw(screen)
            goal_right.draw(screen)
            foot1.draw(screen)
            foot2.draw(screen)
            p1.draw(screen)
            p2.draw(screen)
            ball.draw(screen)
            hud.draw(screen, "TITAN", "RIVAL", p1_score, p2_score, time_left)

            if goal_pause > 15:
                gol_font = pygame.font.SysFont("monospace", 50, bold=True)
                txt = gol_font.render("GOL!", True, (255, 255, 60))
                screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2,
                                  SCREEN_H // 2 - 60))

            pygame.display.flip()

            if goal_pause == 0:
                reset_positions()
            continue

        # ── Input ──
        keys = pygame.key.get_pressed()

        # ── Update ──
        time_left -= dt
        if time_left <= 0:
            time_left = 0
            game_over = True
            if sounds["kraj"]:
                sounds["kraj"].play()

        # Players
        p1.update_move(keys, p1_controls, FRIC_PLAYER, platform_group, SCREEN_W, GRAVITY)
        p2.update_move(keys, p2_controls, FRIC_PLAYER, platform_group, SCREEN_W, GRAVITY)
        p1.update_col(platform_group)
        p2.update_col(platform_group)

        # Feet
        foot1.update()
        foot2.update()

        # Ball
        ball.update_move(GRAVITY, FRIC_BALL_AIR, FRIC_BALL_GROUND, platform, SCREEN_W)
        ball.update_col(platform)

        # ── Colisiones ──
        # Ball vs heads
        if ball.reflect(p1, platform):
            if sounds["dodir"]:
                sounds["dodir"].play()
        if ball.reflect(p2, platform):
            if sounds["dodir"]:
                sounds["dodir"].play()

        # Ball vs feet (kicks)
        if foot1.kick_ball(ball):
            if sounds["dodir"]:
                sounds["dodir"].play()
        if foot2.kick_ball(ball):
            if sounds["dodir"]:
                sounds["dodir"].play()

        # Player vs player
        dist = p1.pos.distance_to(p2.pos)
        if dist < p1.radius + p2.radius and dist > 0:
            dx = p2.pos.x - p1.pos.x
            overlap = (p1.radius + p2.radius) - dist
            if dx > 0:
                p1.pos.x -= overlap * 0.5
                p2.pos.x += overlap * 0.5
            else:
                p1.pos.x += overlap * 0.5
                p2.pos.x -= overlap * 0.5
            p1.vel.x, p2.vel.x = p2.vel.x * 0.5, p1.vel.x * 0.5
            p1.rect.center = p1.pos
            p2.rect.center = p2.pos

        # ── Goles ──
        if ball.is_goal(goal_left, platform):
            p2_score += 1
            goal_pause = 60
            if sounds["veselje"]:
                sounds["veselje"].play()
        elif ball.is_goal(goal_right, platform):
            p1_score += 1
            goal_pause = 60
            if sounds["veselje"]:
                sounds["veselje"].play()

        # ── Render ──
        screen.blit(pitch_surface, (0, 0))

        # Goals behind players
        goal_left.draw(screen)
        goal_right.draw(screen)

        # Feet behind heads
        foot1.draw(screen)
        foot2.draw(screen)

        # Players
        p1.draw(screen)
        p2.draw(screen)

        # Ball
        ball.draw(screen)

        # HUD
        hud.draw(screen, "TITAN", "RIVAL", p1_score, p2_score, time_left)

        # Controls help
        help_font = pygame.font.SysFont("monospace", 10)
        screen.blit(help_font.render("P1: A/D W=saltar S=patear  |  P2: flechas",
                                     True, (180, 180, 180)), (8, SCREEN_H - 12))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
