"""
Expo Heads - JOYSTICK CHECK 2
Bridge joystick -> teclado fisico (SCANCODES) para Windows.

P1:
- stick izquierda/derecha -> A / D
- stick arriba            -> W (un salto por cada empuje hacia arriba)
- boton X (boton 2)       -> S (una patada por cada pulsacion)

El teclado original sigue funcionando.
"""

import sys
import time
import ctypes
from ctypes import wintypes

try:
    import pygame
except ImportError:
    print("ERROR: pygame no esta instalado. Ejecuta desde el .venv de Expo Heads.")
    raise SystemExit(1)

if sys.platform != "win32":
    print("ERROR: este bridge es solo para Windows.")
    raise SystemExit(1)

# -----------------------------------------------------------------------------
# Win32 SendInput - SCANCODE mode
# -----------------------------------------------------------------------------
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# Set 1 keyboard scancodes
SCAN_W = 0x11
SCAN_A = 0x1E
SCAN_S = 0x1F
SCAN_D = 0x20

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]


user32 = ctypes.windll.user32
SendInput = user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT


def send_scan(scan: int, down: bool) -> bool:
    flags = KEYEVENTF_SCANCODE
    if not down:
        flags |= KEYEVENTF_KEYUP

    inp = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=0,
            wScan=scan,
            dwFlags=flags,
            time=0,
            dwExtraInfo=0,
        ),
    )
    sent = SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return sent == 1


def foreground_title() -> str:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "<sin ventana>"
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(max(length + 1, 2))
    user32.GetWindowTextW(hwnd, buf, len(buf))
    title = buf.value.strip()
    return title or f"<HWND {hwnd}>"


class HeldKeys:
    def __init__(self):
        self.down = set()

    def press(self, scan: int):
        if scan not in self.down:
            ok = send_scan(scan, True)
            if ok:
                self.down.add(scan)
            else:
                print("[WARN] SendInput no pudo inyectar KEYDOWN")

    def release(self, scan: int):
        if scan in self.down:
            ok = send_scan(scan, False)
            self.down.discard(scan)
            if not ok:
                print("[WARN] SendInput no pudo inyectar KEYUP")

    def release_all(self):
        for scan in list(self.down):
            send_scan(scan, False)
        self.down.clear()


# -----------------------------------------------------------------------------
# Ajustes de sensibilidad
# -----------------------------------------------------------------------------
MOVE_DEADZONE = 0.35

# En SDL/Xbox, arriba en el stick izquierdo es Y negativo.
JUMP_THRESHOLD = -0.55
JUMP_RESET = -0.30

# Xbox 360 Controller detectado en el diagnostico:
# X = boton numero 2.
KICK_BUTTON = 2

# Duracion de los pulsos. Suficiente para que el juego vea el input
# durante varios frames, sin dejar teclas pegadas.
JUMP_PULSE_SECONDS = 0.12
KICK_PULSE_SECONDS = 0.10

POLL_HZ = 120


def main():
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()

    print("=" * 72)
    print("EXPO HEADS - JOYSTICK CHECK 2")
    print("=" * 72)
    print(f"Joysticks detectados: {count}")

    if count < 1:
        print("[ERROR] No se detecto ningun joystick.")
        return 1

    joy = pygame.joystick.Joystick(0)
    joy.init()

    print(f"[GAMEPAD] P1 detectado: {joy.get_name()}")
    print(f"[GAMEPAD] Ejes: {joy.get_numaxes()} | Botones: {joy.get_numbuttons()}")
    print()
    print("CONTROLES P1:")
    print("  Stick izquierda -> A -> mover izquierda")
    print("  Stick derecha   -> D -> mover derecha")
    print("  Stick arriba    -> W -> SALTAR")
    print("  Boton X         -> S -> PATEAR")
    print()
    print("Deja este script abierto e inicia una partida 1 VS 1.")
    print("Para cerrar el bridge: Ctrl+C")
    print("=" * 72)

    held = HeldKeys()

    last_dir = None
    last_window = None

    jump_latched = False
    jump_release_at = 0.0

    kick_latched = False
    kick_release_at = 0.0

    try:
        while True:
            pygame.event.pump()
            now = time.monotonic()

            # -------------------------------------------------------------
            # Movimiento horizontal: eje 0
            # -------------------------------------------------------------
            x = joy.get_axis(0)

            if x < -MOVE_DEADZONE:
                direction = "LEFT"
                held.release(SCAN_D)
                held.press(SCAN_A)

            elif x > MOVE_DEADZONE:
                direction = "RIGHT"
                held.release(SCAN_A)
                held.press(SCAN_D)

            else:
                direction = "CENTER"
                held.release(SCAN_A)
                held.release(SCAN_D)

            if direction != last_dir:
                title = foreground_title()
                if title != last_window:
                    print(f"[FOCUS] {title}")
                    last_window = title

                if direction == "LEFT":
                    print(f"[P1] <- axis0={x:+.2f} => A")
                elif direction == "RIGHT":
                    print(f"[P1] -> axis0={x:+.2f} => D")
                else:
                    print(f"[P1] -- axis0={x:+.2f} => libre")

                last_dir = direction

            # -------------------------------------------------------------
            # Salto: eje 1 hacia arriba
            # Un solo salto hasta que el stick vuelva cerca del centro.
            # -------------------------------------------------------------
            y = joy.get_axis(1)

            if y < JUMP_THRESHOLD and not jump_latched:
                jump_latched = True
                held.press(SCAN_W)
                jump_release_at = now + JUMP_PULSE_SECONDS
                print(f"[P1] ^  axis1={y:+.2f} => W / SALTO")

            if jump_release_at and now >= jump_release_at:
                held.release(SCAN_W)
                jump_release_at = 0.0

            if jump_latched and y > JUMP_RESET:
                jump_latched = False

            # -------------------------------------------------------------
            # Patada: boton X = boton 2
            # Un solo KEYDOWN por pulsacion fisica.
            # -------------------------------------------------------------
            x_pressed = bool(joy.get_button(KICK_BUTTON))

            if x_pressed and not kick_latched:
                kick_latched = True
                held.press(SCAN_S)
                kick_release_at = now + KICK_PULSE_SECONDS
                print("[P1] X  boton=2 => S / PATADA")

            if kick_release_at and now >= kick_release_at:
                held.release(SCAN_S)
                kick_release_at = 0.0

            if kick_latched and not x_pressed:
                kick_latched = False

            time.sleep(1.0 / POLL_HZ)

    except KeyboardInterrupt:
        print("\nCerrando bridge...")

    finally:
        held.release_all()
        pygame.joystick.quit()
        pygame.quit()
        print("Teclas liberadas. OK.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
