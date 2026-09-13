"""Expo Heads UNO - launcher de los modos 1 VS 1 y 1 VS TOP #1."""

from pathlib import Path
import os
import subprocess
import sqlite3
from datetime import datetime
import math

import pygame
import pygame.camera

import shutil

from avatar_selector import AvatarSelector


BASE_DIR = Path(__file__).resolve().parent
AVATARS_DIR = BASE_DIR / "data" / "avatars"
CAPTURES_DIR = BASE_DIR / "data" / "captures"
AVATAR_CATALOG_FILE = BASE_DIR / "avatars_catalog.json"
GAME_EXE_1V1 = "head_football_patched_v5_1v1.exe"
GAME_EXE_TOP1 = "head_football_patched_v5_top1_ai.exe"
CURRENT_SETTINGS_FILE = BASE_DIR / "data" / "info_files" / "tren_igra_postavke.txt"
GAME_STATE_FILE = BASE_DIR / "cijeli_game.txt"
DB_FILE = BASE_DIR / "data" / "ranking.db"

SCREEN_W, SCREEN_H = 1200, 700
FPS = 60
MAX_NAME_LENGTH = 15
TOP1_NAME = "TOP #1"

# === PALETA RETRO ARCADE (A juego con los botones del juego) ===
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (15, 15, 25)

# Colores de paneles y marquesinas
PANEL_BG = (14, 24, 40)
PANEL_BORDER_LIGHT = (40, 105, 175)
PANEL_BORDER_DARK = (6, 12, 22)

# Colores de botones y textos principales
BTN_ORANGE = (215, 75, 20)
BTN_ORANGE_LIGHT = (245, 110, 45)
BTN_ORANGE_DARK = (130, 35, 10)
BTN_ORANGE_HOVER = (245, 110, 45)

BTN_YELLOW = (235, 185, 25)
BTN_YELLOW_LIGHT = (255, 220, 70)
BTN_YELLOW_DARK = (150, 110, 10)
BTN_YELLOW_HOVER = (255, 220, 70)

BTN_GRAY_BG = (32, 32, 44)
BTN_GRAY_HOVER = (48, 48, 62)

GRAY = (160, 160, 170)
DARK_GRAY = (40, 40, 40)

# Luces y Podio
NEON_CYAN = (0, 240, 255)
NEON_PINK = (255, 0, 128)
ARCADE_GREEN = (50, 255, 60)
ARCADE_GREEN_DIM = (15, 110, 25)
GOLD = (255, 205, 20)
SILVER = (210, 220, 235)
BRONZE = (215, 125, 50)
ACCENT = (0, 170, 255)
ACCENT_2 = (220, 40, 80)


# ==========================================
# BASE DE DATOS Y LÓGICA DE ARCHIVOS
# ==========================================

def init_db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ranking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT,
                    mode TEXT,
                    gf INTEGER,
                    gc INTEGER,
                    match_date TIMESTAMP
                )''')
    conn.commit()
    conn.close()

def save_score(name, mode, gf, gc):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO ranking (player_name, mode, gf, gc, match_date)
                 VALUES (?, ?, ?, ?, ?)''', (name, mode, gf, gc, datetime.now()))
    conn.commit()
    conn.close()

def get_top_ranking(limit=10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT player_name, mode, gf, gc, match_date
                 FROM ranking
                 ORDER BY gf DESC, gc ASC, match_date ASC
                 LIMIT ?''', (limit,))
    results = c.fetchall()
    conn.close()
    return results

def parse_match_results():
    if not GAME_STATE_FILE.exists():
        return 0, 0
    try:
        text = GAME_STATE_FILE.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("GOLOVI-->"):
                parts = line.split("|!|")
                if len(parts) >= 3:
                    g1_str = parts[1].split("|")[0].strip()
                    g2_str = parts[2].split("|")[0].strip()
                    if g1_str.isdigit() and g2_str.isdigit():
                        return int(g1_str), int(g2_str)

        for line in text.splitlines():
            if line.startswith("IGRACI-->"):
                parts = line.split("|!|")
                if len(parts) >= 3:
                    p1_data = parts[1].split("|")
                    p2_data = parts[2].split("|")
                    for idx in (7, 8, 9, 10, 15, 16, 17):
                        if idx < len(p1_data) and idx < len(p2_data):
                            if p1_data[idx].isdigit() and p2_data[idx].isdigit():
                                v1, v2 = int(p1_data[idx]), int(p2_data[idx])
                                if v1 > 0 or v2 > 0:
                                    return v1, v2
    except Exception as e:
        print(f"Error parseando resultados: {e}")
    return 0, 0

def asset_path(filename):
    folder = BASE_DIR / "data" / "images"
    direct = folder / filename
    if direct.exists():
        return direct
    if folder.exists():
        wanted = filename.casefold()
        for candidate in folder.iterdir():
            if candidate.is_file() and candidate.name.casefold() == wanted:
                return candidate
    return direct

LOGO_FILE = asset_path("naslov2.png")
BG_FILE = asset_path("pozadina.png")
BTN_TOP1_FILE = asset_path("bot1vstop.png")
BTN_1V1_FILE = asset_path("bot1vs1.png")

def validate_name(name):
    name = name.strip()
    if not name:
        raise ValueError("El nombre no puede estar vacío.")
    if any(char in name for char in "|\r\n"):
        raise ValueError("El nombre no puede contener | ni saltos de línea.")
    return name

def write_player_names(player_1, player_2, settings_path=CURRENT_SETTINGS_FILE):
    player_1 = validate_name(player_1)
    player_2 = validate_name(player_2)
    path = Path(settings_path)

    if not path.is_file():
        raise FileNotFoundError(f"No se encontró {path}")

    original = path.read_bytes()
    lines = original.splitlines(keepends=True)
    if len(lines) < 4:
        raise ValueError("El archivo de configuración no tiene las cuatro líneas esperadas.")

    current = lines[3]
    if current.endswith(b"\r\n"):
        ending = b"\r\n"
    elif current.endswith(b"\n"):
        ending = b"\n"
    elif current.endswith(b"\r"):
        ending = b"\r"
    else:
        ending = b""

    lines[3] = f"{player_1}|{player_2}".encode("utf-8") + ending
    updated = b"".join(lines)

    temp_path = path.with_name(path.name + ".expo_tmp")
    try:
        temp_path.write_bytes(updated)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

def launch_game(exe_name):
    exe_path = BASE_DIR / exe_name
    if not exe_path.is_file():
        raise FileNotFoundError(f"No se encontró {exe_name}.")

    img_dir = BASE_DIR / "data" / "images"
    bg_launcher = img_dir / "pozadina.png"
    bg_game = img_dir / "pozadina2.png"
    bg_tmp = img_dir / "pozadina_tmp.png"

    swapped = False
    if bg_launcher.exists() and bg_game.exists():
        try:
            os.replace(bg_launcher, bg_tmp)
            os.replace(bg_game, bg_launcher)
            swapped = True
        except Exception as e:
            print(f"Aviso: Falló el intercambio de fondos: {e}")

    try:
        process = subprocess.Popen([str(exe_path)], cwd=str(BASE_DIR))
        return process.wait()
    finally:
        if swapped:
            try:
                os.replace(bg_launcher, bg_game)
                os.replace(bg_tmp, bg_launcher)
            except Exception as e:
                print(f"Error crítico al restaurar fondos: {e}")


# ==========================================
# COMPONENTES VISUALES PIXEL ART
# ==========================================

def draw_arcade_panel(surface, rect, bg_color=PANEL_BG, border_color=BLACK, border_w=4, highlight_color=PANEL_BORDER_LIGHT, shadow_color=PANEL_BORDER_DARK):
    pygame.draw.rect(surface, BLACK, rect.move(5, 5))
    pygame.draw.rect(surface, border_color, rect)
    
    inner = rect.inflate(-border_w * 2, -border_w * 2)
    pygame.draw.rect(surface, bg_color, inner)
    
    pygame.draw.line(surface, highlight_color, (inner.x, inner.y), (inner.right - 1, inner.y), 3)
    pygame.draw.line(surface, highlight_color, (inner.x, inner.y), (inner.x, inner.bottom - 1), 3)
    pygame.draw.line(surface, shadow_color, (inner.x + 1, inner.bottom - 2), (inner.right - 1, inner.bottom - 2), 3)
    pygame.draw.line(surface, shadow_color, (inner.right - 2, inner.y + 1), (inner.right - 2, inner.bottom - 1), 3)


class Button:
    def __init__(self, x, y, width, height, text, font, color=WHITE, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER, border_color=BLACK, border_w=4):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.bg = bg
        self.hover_bg = hover_bg
        self.border_color = border_color
        self.border_w = border_w
        self.hovered = False

    def draw(self, surface):
        bg = self.hover_bg if self.hovered else self.bg
        highlight = tuple(min(c + 50, 255) for c in bg)
        shadow = tuple(max(c - 40, 0) for c in bg)

        draw_arcade_panel(
            surface, self.rect,
            bg_color=bg, border_color=self.border_color,
            border_w=self.border_w, highlight_color=highlight, shadow_color=shadow
        )

        text_surface = self.font.render(self.text, True, self.color)
        text_shadow = self.font.render(self.text, True, BLACK)
        t_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_shadow, t_rect.move(2, 2))
        surface.blit(text_surface, t_rect)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


class ImageButton:
    def __init__(self, center_x, center_y, image_path, scale_w=420):
        raw = pygame.image.load(str(image_path)).convert_alpha()
        scale_h = int(raw.get_height() * (scale_w / raw.get_width()))
        self.image = pygame.transform.smoothscale(raw, (scale_w, scale_h))
        self.image_hover = self.image.copy()
        overlay = pygame.Surface(self.image_hover.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 35))
        self.image_hover.blit(overlay, (0, 0))
        self.rect = self.image.get_rect(center=(center_x, center_y))
        self.hovered = False

    def draw(self, surface):
        surface.blit(self.image_hover if self.hovered else self.image, self.rect)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


class Launcher:
    def __init__(self):
        init_db()
        pygame.init()

        AVATARS_DIR.mkdir(parents=True, exist_ok=True)
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

        self.avatar_selector = AvatarSelector(AVATAR_CATALOG_FILE)

        self.avatar_p1 = None
        self.avatar_p2 = None
        self.avatar_match_p1 = None
        self.avatar_match_p2 = None

        try:
            pygame.camera.init()
            self.cam_list = pygame.camera.list_cameras()
        except Exception:
            self.cam_list = []

        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Expo Heads UNO")
        self.clock = pygame.time.Clock()

        pixel_font = self._find_pixel_font()
        self.font_title = pygame.font.SysFont(pixel_font, 46, bold=True)
        self.font_subtitle = pygame.font.SysFont(pixel_font, 22)
        self.font_button = pygame.font.SysFont(pixel_font, 26, bold=True)
        self.font_small = pygame.font.SysFont(pixel_font, 18, bold=True)
        self.font_hud_title = pygame.font.SysFont(pixel_font, 22, bold=True)
        self.font_hud_row = pygame.font.SysFont(pixel_font, 16, bold=True)
        self.font_mini = pygame.font.SysFont(pixel_font, 12, bold=True)

        self.running = True
        self.state = "menu"
        self.prev_state = "menu"
        self.game_mode = None
        self.p1_name = ""
        self.p2_name = ""
        self.active_input = 1
        self.finished_mode = ""
        self.status_message = ""
        
        self.cam = None
        self.cam_surface = None
        self.active_camera = 1
        self.photo_p1 = None
        self.photo_p2 = None

        self.ranking_box_rect = pygame.Rect(900, 22, 275, 195)

        self.bg_image = self._load_background()
        self.logo_image = self._load_logo()
        self._create_menu_buttons()

    @staticmethod
    def _find_pixel_font():
        available = {name.casefold(): name for name in pygame.font.get_fonts()}
        for wanted in ("pressstart2p", "pixelifysans", "vt323"):
            if wanted in available:
                return available[wanted]
        return "Courier"

    def _load_background(self):
        if not BG_FILE.is_file():
            return None
        try:
            image = pygame.image.load(str(BG_FILE)).convert()
            image = pygame.transform.scale(image, (SCREEN_W, SCREEN_H))
            overlay = pygame.Surface((SCREEN_W, SCREEN_H))
            overlay.fill(BLACK)
            overlay.set_alpha(100)
            image.blit(overlay, (0, 0))
            return image
        except pygame.error:
            return None

    @staticmethod
    def _load_logo():
        if not LOGO_FILE.is_file():
            return None
        try:
            raw = pygame.image.load(str(LOGO_FILE)).convert_alpha()
            logo_w = 540
            logo_h = int(raw.get_height() * (logo_w / raw.get_width()))
            return pygame.transform.smoothscale(raw, (logo_w, logo_h))
        except pygame.error:
            return None

    def _create_menu_buttons(self):
        center_x = SCREEN_W // 2
        if BTN_TOP1_FILE.is_file() and BTN_1V1_FILE.is_file():
            self.btn_top1 = ImageButton(center_x, 430, BTN_TOP1_FILE)
            self.btn_1v1 = ImageButton(center_x, 525, BTN_1V1_FILE)
        else:
            self.btn_top1 = Button(center_x - 210, 397, 420, 66, "1 VS TOP #1", self.font_button, bg=BTN_ORANGE, hover_bg=BTN_ORANGE_HOVER)
            self.btn_1v1 = Button(center_x - 210, 497, 420, 66, "1 VS 1", self.font_button, bg=BTN_YELLOW, hover_bg=BTN_YELLOW_HOVER)

        self.btn_exit = Button(
            center_x - 100, 610, 200, 46, "SALIR", self.font_small, 
            color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER, border_color=BLACK, border_w=4
        )

    def _draw_bg(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(DARK_BG)

    def _draw_title(self):
        if self.logo_image:
            rect = self.logo_image.get_rect(center=(SCREEN_W // 2, 120))
            self.screen.blit(self.logo_image, rect)
        else:
            title = self.font_title.render("EXPO HEADS", True, WHITE)
            self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 100)))

    def _draw_ranking_hud(self):
        r = self.ranking_box_rect

        draw_arcade_panel(
            self.screen, r,
            bg_color=PANEL_BG,
            border_color=BLACK,
            border_w=4,
            highlight_color=PANEL_BORDER_LIGHT,
            shadow_color=PANEL_BORDER_DARK
        )

        time_ms = pygame.time.get_ticks()
        pulse = (math.sin(time_ms * 0.006) + 1) / 2
        r_g = int(ARCADE_GREEN_DIM[0] + (ARCADE_GREEN[0] - ARCADE_GREEN_DIM[0]) * pulse)
        g_g = int(ARCADE_GREEN_DIM[1] + (ARCADE_GREEN[1] - ARCADE_GREEN_DIM[1]) * pulse)
        b_g = int(ARCADE_GREEN_DIM[2] + (ARCADE_GREEN[2] - ARCADE_GREEN_DIM[2]) * pulse)
        neon_color = (r_g, g_g, b_g)

        title_surf = self.font_hud_title.render("RANKING", True, neon_color)
        title_shadow = self.font_hud_title.render("RANKING", True, BLACK)
        title_rect = title_surf.get_rect(center=(r.centerx, r.y + 24))
        self.screen.blit(title_shadow, title_rect.move(2, 2))
        self.screen.blit(title_surf, title_rect)

        line_y = r.y + 46
        pygame.draw.line(self.screen, BTN_YELLOW_DARK, (r.x + 14, line_y + 1), (r.right - 14, line_y + 1), 3)
        pygame.draw.line(self.screen, BTN_YELLOW, (r.x + 14, line_y), (r.right - 14, line_y), 2)

        top3 = get_top_ranking(3)
        podium = [("1ST", GOLD), ("2ND", SILVER), ("3RD", BRONZE)]

        row_y = r.y + 60
        for i in range(3):
            pos_label, color = podium[i]

            if i < len(top3):
                p_name, _mode, gf, _gc, _date = top3[i]
                display_name = (p_name[:7] + "..") if len(p_name) > 8 else p_name
                score_label = f"{gf} goles"
            else:
                display_name = "------"
                score_label = "- goles"

            pos_surf = self.font_hud_row.render(pos_label, True, color)
            pos_shadow = self.font_hud_row.render(pos_label, True, BLACK)
            
            name_surf = self.font_hud_row.render(display_name, True, WHITE)
            name_shadow = self.font_hud_row.render(display_name, True, BLACK)
            
            score_surf = self.font_hud_row.render(score_label, True, BTN_ORANGE_LIGHT)
            score_shadow = self.font_hud_row.render(score_label, True, BLACK)

            self.screen.blit(pos_shadow, (r.x + 16, row_y + 1))
            self.screen.blit(pos_surf, (r.x + 15, row_y))

            self.screen.blit(name_shadow, (r.x + 56, row_y + 1))
            self.screen.blit(name_surf, (r.x + 55, row_y))

            score_rect = score_surf.get_rect(right=r.right - 15, top=row_y)
            self.screen.blit(score_shadow, score_rect.move(1, 1))
            self.screen.blit(score_surf, score_rect)

            row_y += 36

        if (time_ms // 500) % 2 == 0:
            click_surf = self.font_mini.render("CLICK VER TOP 10", True, GRAY)
            self.screen.blit(click_surf, click_surf.get_rect(center=(r.centerx, r.bottom - 13)))

    def _screen_menu(self, events):
        self._draw_bg()
        self._draw_title()
        self._draw_ranking_hud()

        mouse = pygame.mouse.get_pos()
        for button in (self.btn_top1, self.btn_1v1, self.btn_exit):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_1v1.clicked(mouse):
                    self.game_mode = "1v1"
                    self.p1_name = ""
                    self.p2_name = ""
                    self.photo_p1 = None
                    self.photo_p2 = None
                    self.active_input = 1
                    self.status_message = ""
                    self.state = "input_1v1"
                elif self.btn_top1.clicked(mouse):
                    self.game_mode = "top1"
                    self.p1_name = ""
                    self.photo_p1 = None
                    self.status_message = ""
                    self.state = "input_top1"
                elif self.ranking_box_rect.collidepoint(mouse):
                    self.state = "ranking"
                elif self.btn_exit.clicked(mouse):
                    self.state = "confirm_exit"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "confirm_exit"

    def _draw_silhouette(self, rect, color, photo=None):
        draw_arcade_panel(self.screen, rect, bg_color=PANEL_BG, border_color=color, border_w=4)
        
        if photo:
            photo_rect = photo.get_rect(center=rect.center)
            self.screen.blit(photo, photo_rect)
            pygame.draw.rect(self.screen, color, photo_rect, 2)
        else:
            cx, cy = rect.center
            pygame.draw.circle(self.screen, GRAY, (cx, cy - 25), 35, 4)
            pygame.draw.arc(self.screen, GRAY, (cx - 55, cy + 10, 110, 80), 0, math.pi, 4)
            
            time_ms = pygame.time.get_ticks()
            if (time_ms // 500) % 2 == 0:
                text = self.font_mini.render("CLICK FOTO", True, WHITE)
                self.screen.blit(text, text.get_rect(center=(cx, rect.bottom - 20)))

    def _open_camera(self, player_num):
        if not self.cam_list:
            self.status_message = "NO SE DETECTÓ CÁMARA WEB."
            return
        try:
            self.cam = pygame.camera.Camera(self.cam_list[0], (640, 480))
            self.cam.start()
            self.active_camera = player_num
            self.prev_state = self.state
            self.state = "camera"
        except Exception as e:
            self.status_message = f"ERROR CÁMARA: {e}"

    def _screen_camera(self, events):
        self.screen.fill(BLACK)
        if self.cam and self.cam.query_image():
            self.cam_surface = self.cam.get_image()

        if self.cam_surface:
            mirrored = pygame.transform.flip(self.cam_surface, True, False)
            rect = mirrored.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
            self.screen.blit(mirrored, rect)

            crop_size = min(rect.width, rect.height)
            target_rect = pygame.Rect(0, 0, crop_size, crop_size)
            target_rect.center = rect.center
            pygame.draw.rect(self.screen, ARCADE_GREEN, target_rect, 4)

        title = self.font_title.render(f"FOTO JUGADOR {self.active_camera}", True, ACCENT)
        title_shadow = self.font_title.render(f"FOTO JUGADOR {self.active_camera}", True, DARK_GRAY)
        t_rect = title.get_rect(center=(SCREEN_W // 2, 60))
        self.screen.blit(title_shadow, t_rect.move(3, 3))
        self.screen.blit(title, t_rect)
        
        inst = self.font_button.render("ESPACIO: CAPTURAR   |   ESC: CANCELAR", True, WHITE)
        self.screen.blit(inst, inst.get_rect(center=(SCREEN_W // 2, SCREEN_H - 60)))

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and self.cam_surface:
                    mirrored = pygame.transform.flip(self.cam_surface, True, False)
                    w, h = mirrored.get_size()
                    size = min(w, h)
                    crop_rect = pygame.Rect((w - size) // 2, (h - size) // 2, size, size)
                    cropped = mirrored.subsurface(crop_rect).copy()
                    
                    final_img = pygame.transform.smoothscale(cropped, (128, 128))
                    
                    filename = f"igrac{self.active_camera}.png"
                    filepath = BASE_DIR / "data" / "images" / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(final_img, str(filepath))
                    
                    if self.active_camera == 1:
                        self.photo_p1 = pygame.transform.smoothscale(final_img, (140, 140))
                    else:
                        self.photo_p2 = pygame.transform.smoothscale(final_img, (140, 140))
                        
                    self.cam.stop()
                    self.cam = None
                    self.state = self.prev_state
                elif event.key == pygame.K_ESCAPE:
                    self.cam.stop()
                    self.cam = None
                    self.state = self.prev_state
            elif event.type == pygame.QUIT:
                if self.cam:
                    self.cam.stop()
                self.running = False

    def _draw_input_box(self, label, name, x, y, active, color):
        label_surface = self.font_small.render(label, True, color)
        label_shadow = self.font_small.render(label, True, BLACK)
        self.screen.blit(label_shadow, (x + 2, y + 2))
        self.screen.blit(label_surface, (x, y))

        rect = pygame.Rect(x, y + 28, 450, 52)
        highlight = color if active else (50, 60, 80)
        shadow = tuple(max(c - 80, 0) for c in color) if active else (10, 15, 25)
        
        draw_arcade_panel(
            self.screen, rect, bg_color=(10, 15, 25), border_color=BLACK, 
            border_w=3, highlight_color=highlight, shadow_color=shadow
        )

        time_ms = pygame.time.get_ticks()
        cursor = "_" if active and (time_ms // 400) % 2 == 0 else ""
        text_surface = self.font_button.render(name + cursor, True, WHITE)
        self.screen.blit(text_surface, (rect.x + 18, rect.y + 12))
        return rect

    def _draw_status(self, x, y):
        if self.status_message:
            text = self.font_small.render(self.status_message[:82], True, ACCENT_2)
            self.screen.blit(text, text.get_rect(center=(x, y)))

    @staticmethod
    def _valid_input_character(event):
        return bool(event.unicode) and len(event.unicode) == 1 and event.unicode.isprintable() and event.unicode != "|"

    def _screen_input_1v1(self, events):
        self._draw_bg()

        left_panel = pygame.Rect(80, 120, 560, 430)
        cam1_rect = pygame.Rect(700, 120, 400, 195)
        cam2_rect = pygame.Rect(700, 345, 400, 195)

        draw_arcade_panel(self.screen, left_panel, bg_color=PANEL_BG, border_color=BLACK)
        
        t_surf = self.font_button.render("1 VS 1", True, BTN_YELLOW)
        t_shadow = self.font_button.render("1 VS 1", True, BLACK)
        t_pos = t_surf.get_rect(center=(left_panel.centerx, left_panel.y + 35))
        self.screen.blit(t_shadow, t_pos.move(2, 2))
        self.screen.blit(t_surf, t_pos)

        sub_surf = self.font_small.render("INGRESA LOS NOMBRES", True, WHITE)
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(left_panel.centerx, left_panel.y + 70)))

        box_1 = self._draw_input_box("JUGADOR 1:", self.p1_name, left_panel.x + 55, left_panel.y + 95, self.active_input == 1, ACCENT)
        box_2 = self._draw_input_box("JUGADOR 2:", self.p2_name, left_panel.x + 55, left_panel.y + 205, self.active_input == 2, BTN_ORANGE_LIGHT)
        
        self._draw_status(left_panel.centerx, left_panel.y + 325)

        # VOLVER a la izquierda, JUGAR a la derecha
        btn_back = Button(
            left_panel.centerx - 165, left_panel.bottom - 65, 150, 45, "VOLVER", self.font_small, 
            color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER
        )
        can_play = bool(self.p1_name.strip() and self.p2_name.strip())
        btn_play = Button(
            left_panel.centerx + 15, left_panel.bottom - 65, 150, 45, "JUGAR", self.font_button, 
            color=WHITE if can_play else GRAY, 
            bg=(35, 140, 65) if can_play else (40, 40, 50), 
            hover_bg=(45, 175, 80) if can_play else (40, 40, 50)
        )

        self._draw_silhouette(cam1_rect, ACCENT, self.photo_p1)
        self._draw_silhouette(cam2_rect, BTN_ORANGE_LIGHT, self.photo_p2)

        mouse = pygame.mouse.get_pos()
        for button in (btn_play, btn_back):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                can_play = bool(self.p1_name.strip() and self.p2_name.strip())
                if btn_play.clicked(mouse) and can_play:
                    self._start_match_1v1()
                elif btn_back.clicked(mouse):
                    self.state = "menu"
                elif box_1.collidepoint(mouse):
                    self.active_input = 1
                elif box_2.collidepoint(mouse):
                    self.active_input = 2
                elif cam1_rect.collidepoint(mouse):
                    self._open_camera(1)
                elif cam2_rect.collidepoint(mouse):
                    self._open_camera(2)
            elif event.type == pygame.KEYDOWN:
                can_play = bool(self.p1_name.strip() and self.p2_name.strip())
                if event.key == pygame.K_TAB:
                    self.active_input = 2 if self.active_input == 1 else 1
                elif event.key == pygame.K_RETURN and can_play:
                    self._start_match_1v1()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif event.key == pygame.K_BACKSPACE:
                    if self.active_input == 1:
                        self.p1_name = self.p1_name[:-1]
                    else:
                        self.p2_name = self.p2_name[:-1]
                elif self._valid_input_character(event):
                    if self.active_input == 1 and len(self.p1_name) < MAX_NAME_LENGTH:
                        self.p1_name += event.unicode
                    elif self.active_input == 2 and len(self.p2_name) < MAX_NAME_LENGTH:
                        self.p2_name += event.unicode

    def _screen_input_top1(self, events):
        self._draw_bg()

        left_panel = pygame.Rect(80, 150, 560, 380)
        cam1_rect = pygame.Rect(700, 150, 400, 380)

        draw_arcade_panel(self.screen, left_panel, bg_color=PANEL_BG, border_color=BLACK)
        self._draw_silhouette(cam1_rect, ACCENT, self.photo_p1)
        
        t_surf = self.font_button.render("1 VS TOP #1", True, BTN_ORANGE_LIGHT)
        t_shadow = self.font_button.render("1 VS TOP #1", True, BLACK)
        t_pos = t_surf.get_rect(center=(left_panel.centerx, left_panel.y + 40))
        self.screen.blit(t_shadow, t_pos.move(2, 2))
        self.screen.blit(t_surf, t_pos)

        box_1 = self._draw_input_box("TU NOMBRE:", self.p1_name, left_panel.x + 55, left_panel.y + 105, True, ACCENT)
        
        rival_surf = self.font_button.render(f"RIVAL: {TOP1_NAME}", True, BTN_YELLOW)
        r_pos = rival_surf.get_rect(center=(left_panel.centerx, left_panel.y + 245))
        self.screen.blit(rival_surf, r_pos)
        
        self._draw_status(left_panel.centerx, left_panel.y + 280)

        # VOLVER a la izquierda, DESAFIAR a la derecha
        btn_back = Button(
            left_panel.centerx - 165, left_panel.bottom - 65, 150, 45, "VOLVER", self.font_small, 
            color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER
        )
        can_play = bool(self.p1_name.strip())
        btn_play = Button(
            left_panel.centerx + 15, left_panel.bottom - 65, 150, 45, "DESAFIAR", self.font_small, 
            color=WHITE if can_play else GRAY, 
            bg=BTN_ORANGE if can_play else (40, 40, 50), 
            hover_bg=BTN_ORANGE_HOVER if can_play else (40, 40, 50)
        )
        
        mouse = pygame.mouse.get_pos()
        for button in (btn_play, btn_back):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                can_play = bool(self.p1_name.strip())
                if btn_play.clicked(mouse) and can_play:
                    self._start_match_top1()
                elif btn_back.clicked(mouse):
                    self.state = "menu"
                elif box_1.collidepoint(mouse):
                    self.active_input = 1
                elif cam1_rect.collidepoint(mouse):
                    self._open_camera(1)
            elif event.type == pygame.KEYDOWN:
                can_play = bool(self.p1_name.strip())
                if event.key == pygame.K_RETURN and can_play:
                    self._start_match_top1()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif event.key == pygame.K_BACKSPACE:
                    self.p1_name = self.p1_name[:-1]
                elif self._valid_input_character(event) and len(self.p1_name) < MAX_NAME_LENGTH:
                    self.p1_name += event.unicode

    def _draw_center_panel(self, title, subtitle="", height=350):
        self._draw_bg()
        panel = pygame.Rect(SCREEN_W // 2 - 400, SCREEN_H // 2 - (height // 2), 800, height)
        draw_arcade_panel(
            self.screen, panel,
            bg_color=PANEL_BG,
            border_color=BLACK,
            border_w=4,
            highlight_color=PANEL_BORDER_LIGHT,
            shadow_color=PANEL_BORDER_DARK
        )

        title_surface = self.font_title.render(title, True, ARCADE_GREEN)
        title_shadow = self.font_title.render(title, True, BLACK)
        t_rect = title_surface.get_rect(center=(SCREEN_W // 2, panel.top + 45))
        self.screen.blit(title_shadow, t_rect.move(3, 3))
        self.screen.blit(title_surface, t_rect)

        if subtitle:
            subtitle_surface = self.font_subtitle.render(subtitle, True, GRAY)
            self.screen.blit(subtitle_surface, subtitle_surface.get_rect(center=(SCREEN_W // 2, panel.top + 85)))

    def _screen_finished(self, events):
        self._draw_center_panel("MATCH OVER", self.finished_mode)
        info = self.font_subtitle.render(self.status_message[:86], True, WHITE)
        self.screen.blit(info, info.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 10)))
        
        saved_info = self.font_small.render("PUNTAJE ENVIADO AL LEADERBOARD", True, NEON_CYAN)
        self.screen.blit(saved_info, saved_info.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 45)))

        btn_menu = Button(SCREEN_W // 2 - 250, SCREEN_H // 2 + 92, 220, 58, "MENU", self.font_button)
        btn_exit = Button(SCREEN_W // 2 + 30, SCREEN_H // 2 + 92, 220, 58, "QUIT", self.font_button, bg=ACCENT_2, hover_bg=(245, 55, 95))
        mouse = pygame.mouse.get_pos()
        for button in (btn_menu, btn_exit):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_menu.clicked(mouse):
                    self.state = "menu"
                elif btn_exit.clicked(mouse):
                    self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.state = "menu"

    def _screen_ranking(self, events):
        self._draw_center_panel("TOP 10 HIGH SCORES", height=500)
        
        headers = self.font_small.render(f"{'RANK':<5} {'JUGADOR':<16} {'MODO':<14} {'GOLES':<6} FECHA", True, NEON_PINK)
        self.screen.blit(headers, (SCREEN_W // 2 - 320, 185))
        pygame.draw.line(self.screen, NEON_CYAN, (SCREEN_W // 2 - 320, 210), (SCREEN_W // 2 + 320, 210), 3)

        records = get_top_ranking(10)
        y_pos = 225
        for i, (name, mode, gf, gc, m_date) in enumerate(records):
            dt_obj = datetime.strptime(m_date, "%Y-%m-%d %H:%M:%S.%f")
            date_str = dt_obj.strftime("%d/%m %H:%M")
            row_text = f"#{i+1:02d}   {name.upper()[:15]:<16} {mode[:12]:<14} {gf:<6} {date_str}"
            
            color = GOLD if i == 0 else SILVER if i == 1 else BRONZE if i == 2 else NEON_CYAN
            
            row_surf = self.font_small.render(row_text, True, color)
            self.screen.blit(row_surf, (SCREEN_W // 2 - 320, y_pos))
            y_pos += 28

        btn_back = Button(SCREEN_W // 2 - 100, 520, 200, 45, "VOLVER", self.font_small, color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER)
        mouse = pygame.mouse.get_pos()
        btn_back.update(mouse)
        btn_back.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_back.clicked(mouse):
                    self.state = "menu"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "menu"

    def _screen_confirm_exit(self, events):
        self._draw_center_panel("INSERT COIN TO CONTINUE?", "O QUIERES SALIR DEL JUEGO?")
        btn_yes = Button(SCREEN_W // 2 - 260, SCREEN_H // 2 + 60, 220, 58, "SALIR", self.font_button, bg=ACCENT_2, hover_bg=(245, 55, 95))
        btn_no = Button(SCREEN_W // 2 + 40, SCREEN_H // 2 + 60, 220, 58, "VOLVER", self.font_button)
        mouse = pygame.mouse.get_pos()
        for button in (btn_yes, btn_no):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_yes.clicked(mouse):
                    self.running = False
                elif btn_no.clicked(mouse):
                    self.state = "menu"
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    self.state = "menu"
                elif event.key in (pygame.K_RETURN, pygame.K_y, pygame.K_s):
                    self.running = False

    def _run_match(self, mode_label, exe_name, player_1, player_2):
        try:
            write_player_names(player_1, player_2)
            pygame.display.iconify()
            
            return_code = launch_game(exe_name)
            
            g1, g2 = parse_match_results()
            self.match_results = (g1, g2)
            
            if return_code == 0:
                self.status_message = f"MARCADOR FINAL: {g1} - {g2}"
                if self.game_mode == "1v1":
                    save_score(player_1, "1 VS 1", g1, g2)
                    save_score(player_2, "1 VS 1", g2, g1)
                elif self.game_mode == "top1":
                    save_score(player_1, "1 VS TOP #1", g1, g2)
            else:
                self.status_message = f"GAME ERROR CODE: {return_code}"

            self.finished_mode = mode_label
            self.state = "finished"
        except (OSError, ValueError) as exc:
            self.finished_mode = mode_label
            self.status_message = str(exc)
            self.state = "finished"
        finally:
            self._restore_window()

    def _start_match_1v1(self):
        self._run_match("1 VS 1", GAME_EXE_1V1, self.p1_name.strip(), self.p2_name.strip())

    def _start_match_top1(self):
        self._run_match("1 VS TOP #1", GAME_EXE_TOP1, self.p1_name.strip(), TOP1_NAME)

    def _restore_window(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Expo Heads UNO")
        pygame.event.clear()

    def run(self):
        while self.running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            if self.state == "menu":
                self._screen_menu(events)
            elif self.state == "input_1v1":
                self._screen_input_1v1(events)
            elif self.state == "input_top1":
                self._screen_input_top1(events)
            elif self.state == "camera":
                self._screen_camera(events)
            elif self.state == "finished":
                self._screen_finished(events)
            elif self.state == "ranking":
                self._screen_ranking(events)
            elif self.state == "confirm_exit":
                self._screen_confirm_exit(events)

            pygame.display.flip()
            self.clock.tick(FPS)

        if self.cam:
            self.cam.stop()
        pygame.quit()


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    Launcher().run()