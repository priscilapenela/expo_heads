"""Expo Heads UNO - launcher de los modos 1 VS 1 y 1 VS TOP #1."""

from pathlib import Path
import os
import subprocess

import pygame


BASE_DIR = Path(__file__).resolve().parent
GAME_EXE_1V1 = "head_football_patched_v5_1v1.exe"
GAME_EXE_TOP1 = "head_football_patched_v5_top1_ai.exe"
CURRENT_SETTINGS_FILE = BASE_DIR / "data" / "info_files" / "tren_igra_postavke.txt"

SCREEN_W, SCREEN_H = 1200, 700
FPS = 60
MAX_NAME_LENGTH = 15
TOP1_NAME = "TOP #1"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (15, 15, 25)
BUTTON_BG = (40, 40, 55)
BUTTON_HOVER = (60, 60, 80)
ACCENT = (0, 170, 255)
ACCENT_2 = (220, 40, 80)
GRAY = (150, 150, 150)
ORANGE = (210, 70, 20)
ORANGE_HOVER = (235, 90, 30)
YELLOW = (220, 180, 30)
YELLOW_HOVER = (240, 200, 50)


def asset_path(filename):
    """Devuelve un asset aun si el nombre sólo difiere en mayúsculas."""
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
    """Valida un nombre sin transformarlo silenciosamente."""
    name = name.strip()
    if not name:
        raise ValueError("El nombre no puede estar vacío.")
    if any(char in name for char in "|\r\n"):
        raise ValueError("El nombre no puede contener | ni saltos de línea.")
    return name


def write_player_names(player_1, player_2, settings_path=CURRENT_SETTINGS_FILE):
    """Reemplaza sólo la cuarta línea del archivo de nombres del partido."""
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
    """Abre el ejecutable directo y espera su cierre al terminar el partido."""
    exe_path = BASE_DIR / exe_name
    if not exe_path.is_file():
        raise FileNotFoundError(
            f"No se encontró {exe_name}. Debe estar en la misma carpeta que launcher.py."
        )

    process = subprocess.Popen([str(exe_path)], cwd=str(BASE_DIR))
    return process.wait()


class Button:
    def __init__(
        self,
        x,
        y,
        width,
        height,
        text,
        font,
        color=WHITE,
        bg=BUTTON_BG,
        hover_bg=BUTTON_HOVER,
        border_color=BLACK,
        border_w=4,
    ):
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
        shadow = self.rect.move(4, 4)
        pygame.draw.rect(surface, BLACK, shadow)
        pygame.draw.rect(surface, bg, self.rect)
        pygame.draw.rect(surface, self.border_color, self.rect, self.border_w)

        highlight = tuple(min(channel + 40, 255) for channel in bg)
        pygame.draw.line(
            surface,
            highlight,
            (self.rect.x + self.border_w, self.rect.y + self.border_w),
            (self.rect.right - self.border_w, self.rect.y + self.border_w),
            2,
        )
        pygame.draw.line(
            surface,
            highlight,
            (self.rect.x + self.border_w, self.rect.y + self.border_w),
            (self.rect.x + self.border_w, self.rect.bottom - self.border_w),
            2,
        )

        text_surface = self.font.render(self.text, True, self.color)
        surface.blit(text_surface, text_surface.get_rect(center=self.rect.center))

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
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Expo Heads UNO")
        self.clock = pygame.time.Clock()

        pixel_font = self._find_pixel_font()
        self.font_title = pygame.font.SysFont(pixel_font, 42, bold=True)
        self.font_subtitle = pygame.font.SysFont(pixel_font, 22)
        self.font_button = pygame.font.SysFont(pixel_font, 28, bold=True)
        self.font_small = pygame.font.SysFont(pixel_font, 18)

        self.running = True
        self.state = "menu"
        self.game_mode = None
        self.p1_name = ""
        self.p2_name = ""
        self.active_input = 1
        self.finished_mode = ""
        self.status_message = ""

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
            logo_w = 550
            logo_h = int(raw.get_height() * (logo_w / raw.get_width()))
            return pygame.transform.smoothscale(raw, (logo_w, logo_h))
        except pygame.error:
            return None

    def _create_menu_buttons(self):
        center_x = SCREEN_W // 2
        if BTN_TOP1_FILE.is_file() and BTN_1V1_FILE.is_file():
            self.btn_top1 = ImageButton(center_x, 440, BTN_TOP1_FILE)
            self.btn_1v1 = ImageButton(center_x, 540, BTN_1V1_FILE)
        else:
            self.btn_top1 = Button(
                center_x - 210,
                407,
                420,
                66,
                "1 VS TOP #1",
                self.font_button,
                bg=ORANGE,
                hover_bg=ORANGE_HOVER,
            )
            self.btn_1v1 = Button(
                center_x - 210,
                507,
                420,
                66,
                "1 VS 1",
                self.font_button,
                bg=YELLOW,
                hover_bg=YELLOW_HOVER,
            )

        self.btn_exit = Button(
            center_x - 100,
            620,
            200,
            45,
            "SALIR",
            self.font_small,
            color=GRAY,
            bg=(30, 30, 40),
            hover_bg=(50, 50, 60),
            border_color=(60, 60, 60),
            border_w=3,
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

    def _draw_center_panel(self, title, subtitle=""):
        self._draw_bg()
        panel = pygame.Rect(SCREEN_W // 2 - 360, SCREEN_H // 2 - 165, 720, 330)
        pygame.draw.rect(self.screen, BLACK, panel.move(8, 8), border_radius=12)
        pygame.draw.rect(self.screen, (18, 18, 28), panel, border_radius=12)
        pygame.draw.rect(self.screen, WHITE, panel, 4, border_radius=12)
        pygame.draw.rect(
            self.screen, ACCENT_2, panel.inflate(-18, -18), 2, border_radius=8
        )

        title_surface = self.font_title.render(title, True, WHITE)
        self.screen.blit(
            title_surface,
            title_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 80)),
        )
        if subtitle:
            subtitle_surface = self.font_subtitle.render(subtitle, True, GRAY)
            self.screen.blit(
                subtitle_surface,
                subtitle_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 25)),
            )

    def _screen_menu(self, events):
        self._draw_bg()
        self._draw_title()

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
                    self.active_input = 1
                    self.status_message = ""
                    self.state = "input_1v1"
                elif self.btn_top1.clicked(mouse):
                    self.game_mode = "top1"
                    self.p1_name = ""
                    self.status_message = ""
                    self.state = "input_top1"
                elif self.btn_exit.clicked(mouse):
                    self.state = "confirm_exit"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "confirm_exit"

    def _draw_input_box(self, label, name, y, active, color):
        label_surface = self.font_small.render(label, True, color)
        self.screen.blit(label_surface, (SCREEN_W // 2 - 200, y))

        rect = pygame.Rect(SCREEN_W // 2 - 200, y + 30, 400, 50)
        pygame.draw.rect(self.screen, BUTTON_BG, rect, border_radius=8)
        pygame.draw.rect(
            self.screen, WHITE if active else BLACK, rect, 2, border_radius=8
        )
        cursor = "|" if active and pygame.time.get_ticks() % 1000 < 500 else ""
        text_surface = self.font_button.render(name + cursor, True, WHITE)
        self.screen.blit(text_surface, (rect.x + 15, rect.y + 10))
        return rect

    def _draw_status(self, y=455):
        if self.status_message:
            text = self.font_small.render(self.status_message[:82], True, ACCENT_2)
            self.screen.blit(text, text.get_rect(center=(SCREEN_W // 2, y)))

    def _screen_input_1v1(self, events):
        self._draw_bg()
        title = self.font_button.render("1 VS 1 - INGRESA LOS NOMBRES", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 80)))

        box_1 = self._draw_input_box(
            "JUGADOR 1:", self.p1_name, 200, self.active_input == 1, ACCENT
        )
        box_2 = self._draw_input_box(
            "JUGADOR 2:", self.p2_name, 320, self.active_input == 2, ACCENT_2
        )
        self._draw_status()

        can_play = bool(self.p1_name.strip() and self.p2_name.strip())
        btn_play = Button(
            SCREEN_W // 2 - 150,
            500,
            300,
            60,
            "JUGAR",
            self.font_button,
            color=WHITE if can_play else GRAY,
            bg=(30, 130, 60) if can_play else (40, 40, 40),
            hover_bg=(40, 160, 75) if can_play else (40, 40, 40),
            border_color=(50, 180, 80) if can_play else (60, 60, 60),
        )
        btn_back = Button(
            SCREEN_W // 2 - 100,
            590,
            200,
            45,
            "VOLVER",
            self.font_small,
            color=GRAY,
            bg=(30, 30, 40),
            hover_bg=(50, 50, 60),
            border_color=(80, 80, 80),
        )
        mouse = pygame.mouse.get_pos()
        for button in (btn_play, btn_back):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.clicked(mouse) and can_play:
                    self._start_match_1v1()
                elif btn_back.clicked(mouse):
                    self.state = "menu"
                elif box_1.collidepoint(mouse):
                    self.active_input = 1
                elif box_2.collidepoint(mouse):
                    self.active_input = 2
            elif event.type == pygame.KEYDOWN:
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
        title = self.font_button.render("1 VS TOP #1", True, ACCENT_2)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 85)))
        subtitle = self.font_small.render("LA IA JUEGA COMO JUGADOR 2", True, GRAY)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_W // 2, 130)))

        self._draw_input_box("TU NOMBRE:", self.p1_name, 220, True, ACCENT)
        rival = self.font_button.render(f"RIVAL: {TOP1_NAME}", True, ACCENT_2)
        self.screen.blit(rival, rival.get_rect(center=(SCREEN_W // 2, 350)))
        self._draw_status(385)

        can_play = bool(self.p1_name.strip())
        btn_play = Button(
            SCREEN_W // 2 - 150,
            430,
            300,
            60,
            "DESAFIAR",
            self.font_button,
            color=WHITE if can_play else GRAY,
            bg=(160, 30, 60) if can_play else (40, 40, 40),
            hover_bg=(200, 40, 75) if can_play else (40, 40, 40),
            border_color=ACCENT_2 if can_play else (60, 60, 60),
        )
        btn_back = Button(
            SCREEN_W // 2 - 100,
            530,
            200,
            45,
            "VOLVER",
            self.font_small,
            color=GRAY,
            bg=(30, 30, 40),
            hover_bg=(50, 50, 60),
            border_color=(80, 80, 80),
        )
        mouse = pygame.mouse.get_pos()
        for button in (btn_play, btn_back):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.clicked(mouse) and can_play:
                    self._start_match_top1()
                elif btn_back.clicked(mouse):
                    self.state = "menu"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and can_play:
                    self._start_match_top1()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif event.key == pygame.K_BACKSPACE:
                    self.p1_name = self.p1_name[:-1]
                elif self._valid_input_character(event) and len(self.p1_name) < MAX_NAME_LENGTH:
                    self.p1_name += event.unicode

    @staticmethod
    def _valid_input_character(event):
        return (
            bool(event.unicode)
            and len(event.unicode) == 1
            and event.unicode.isprintable()
            and event.unicode != "|"
        )

    def _run_match(self, mode_label, exe_name, player_1, player_2):
        try:
            write_player_names(player_1, player_2)
            pygame.display.iconify()
            return_code = launch_game(exe_name)
            self.finished_mode = mode_label
            self.status_message = (
                "El partido terminó correctamente."
                if return_code == 0
                else f"El juego finalizó con código {return_code}."
            )
            self.state = "finished"
        except (OSError, ValueError) as exc:
            self.finished_mode = mode_label
            self.status_message = str(exc)
            self.state = "finished"
        finally:
            self._restore_window()

    def _start_match_1v1(self):
        self._run_match(
            "1 VS 1",
            GAME_EXE_1V1,
            self.p1_name.strip(),
            self.p2_name.strip(),
        )

    def _start_match_top1(self):
        self._run_match(
            "1 VS TOP #1",
            GAME_EXE_TOP1,
            self.p1_name.strip(),
            TOP1_NAME,
        )

    def _restore_window(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Expo Heads UNO")
        pygame.event.clear()

    def _screen_finished(self, events):
        self._draw_center_panel("PARTIDO TERMINADO", self.finished_mode)
        info = self.font_small.render(self.status_message[:86], True, GRAY)
        self.screen.blit(info, info.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 38)))

        btn_menu = Button(
            SCREEN_W // 2 - 250,
            SCREEN_H // 2 + 92,
            220,
            58,
            "MENU",
            self.font_button,
        )
        btn_exit = Button(
            SCREEN_W // 2 + 30,
            SCREEN_H // 2 + 92,
            220,
            58,
            "SALIR",
            self.font_button,
            bg=ACCENT_2,
            hover_bg=(245, 55, 95),
        )
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

    def _screen_confirm_exit(self, events):
        self._draw_center_panel("SALIR", "QUIERES CERRAR EXPO HEADS?")
        btn_yes = Button(
            SCREEN_W // 2 - 260,
            SCREEN_H // 2 + 60,
            220,
            58,
            "SALIR",
            self.font_button,
            bg=ACCENT_2,
            hover_bg=(245, 55, 95),
        )
        btn_no = Button(
            SCREEN_W // 2 + 40,
            SCREEN_H // 2 + 60,
            220,
            58,
            "VOLVER",
            self.font_button,
        )
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
            elif self.state == "finished":
                self._screen_finished(events)
            elif self.state == "confirm_exit":
                self._screen_confirm_exit(events)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    Launcher().run()
