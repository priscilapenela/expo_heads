"""
Expo Heads - JOYSTICK CHECK 3 - DOS JUGADORES

P1 - Joystick 0:
  Stick izquierda/derecha -> A / D
  Stick arriba            -> W
  Boton X (boton 2)       -> S

P2 - Joystick 1:
  Stick izquierda/derecha -> Flecha izquierda / derecha
  Stick arriba            -> Flecha arriba
  Boton X (boton 2)       -> Flecha abajo

Modo seguro:
  F8 = activar ambos joysticks
  F7 = desactivar y liberar todas las teclas
"""

import sys
import time
import ctypes
from ctypes import wintypes

try:
    import pygame
except ImportError:
    print("ERROR: pygame no esta instalado.")
    raise SystemExit(1)

if sys.platform != "win32":
    print("ERROR: este script requiere Windows.")
    raise SystemExit(1)

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# P1
SCAN_W = 0x11
SCAN_A = 0x1E
SCAN_S = 0x1F
SCAN_D = 0x20

# P2 - teclas extendidas
SCAN_UP = 0x48
SCAN_LEFT = 0x4B
SCAN_RIGHT = 0x4D
SCAN_DOWN = 0x50

VK_F7 = 0x76
VK_F8 = 0x77

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
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION),
    ]

user32 = ctypes.windll.user32

def send_scan(scan, down, extended=False):
    flags = KEYEVENTF_SCANCODE
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
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
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)

def foreground_title():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "<sin ventana>"

    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(max(n + 1, 2))
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value.strip() or f"<HWND {hwnd}>"

class HeldKeys:
    def __init__(self):
        self.down = set()

    def press(self, scan, extended=False):
        key = (scan, extended)
        if key not in self.down:
            if send_scan(scan, True, extended):
                self.down.add(key)

    def release(self, scan, extended=False):
        key = (scan, extended)
        if key in self.down:
            send_scan(scan, False, extended)
            self.down.discard(key)

    def release_all(self):
        for scan, extended in list(self.down):
            send_scan(scan, False, extended)
        self.down.clear()

MOVE_DEADZONE = 0.35

JUMP_THRESHOLD = -0.60
JUMP_RESET = -0.25

KICK_BUTTON = 2

JUMP_PULSE = 0.14
KICK_PULSE = 0.12

POLL_HZ = 120


class PlayerState:
    def __init__(self):
        self.last_dir = None
        self.jump_latched = False
        self.jump_release_at = 0.0
        self.kick_latched = False
        self.kick_release_at = 0.0


def handle_player(
    player_name,
    joy,
    state,
    held,
    now,
    left_key,
    right_key,
    jump_key,
    kick_key,
    extended=False,
):
    # Movimiento horizontal
    x = joy.get_axis(0)

    if x < -MOVE_DEADZONE:
        direction = "LEFT"
        held.release(right_key, extended)
        held.press(left_key, extended)

    elif x > MOVE_DEADZONE:
        direction = "RIGHT"
        held.release(left_key, extended)
        held.press(right_key, extended)

    else:
        direction = "CENTER"
        held.release(left_key, extended)
        held.release(right_key, extended)

    if direction != state.last_dir:
        if direction == "LEFT":
            print(f"[{player_name}] <- axis0={x:+.2f}")
        elif direction == "RIGHT":
            print(f"[{player_name}] -> axis0={x:+.2f}")
        else:
            print(f"[{player_name}] -- axis0={x:+.2f}")

        state.last_dir = direction

    # Salto: un pulso por cada empuje hacia arriba
    y = joy.get_axis(1)

    if y < JUMP_THRESHOLD and not state.jump_latched:
        state.jump_latched = True
        held.press(jump_key, extended)
        state.jump_release_at = now + JUMP_PULSE
        print(f"[{player_name}] ^ axis1={y:+.2f} => SALTO")

    if state.jump_release_at and now >= state.jump_release_at:
        held.release(jump_key, extended)
        state.jump_release_at = 0.0

    if state.jump_latched and y > JUMP_RESET:
        state.jump_latched = False

    # Patada: X = boton 2
    pressed = bool(joy.get_button(KICK_BUTTON))

    if pressed and not state.kick_latched:
        state.kick_latched = True
        held.press(kick_key, extended)
        state.kick_release_at = now + KICK_PULSE
        print(f"[{player_name}] X boton=2 => PATADA")

    if state.kick_release_at and now >= state.kick_release_at:
        held.release(kick_key, extended)
        state.kick_release_at = 0.0

    if state.kick_latched and not pressed:
        state.kick_latched = False


def reset_state(state):
    state.last_dir = None
    state.jump_latched = False
    state.jump_release_at = 0.0
    state.kick_latched = False
    state.kick_release_at = 0.0


def main():
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()

    print("=" * 76)
    print("EXPO HEADS - JOYSTICK CHECK 3 - DOS JUGADORES")
    print("=" * 76)
    print(f"Joysticks detectados: {count}")

    if count < 2:
        print()
        print("[ERROR] Para este check necesitas DOS joysticks conectados.")
        print("Conecta ambos antes de ejecutar este script.")
        return 1

    joy1 = pygame.joystick.Joystick(0)
    joy2 = pygame.joystick.Joystick(1)

    joy1.init()
    joy2.init()

    print(f"[GAMEPAD] P1 / joystick 0: {joy1.get_name()}")
    print(f"[GAMEPAD] P2 / joystick 1: {joy2.get_name()}")
    print()
    print("P1:")
    print("  Stick <- / -> = A / D")
    print("  Stick arriba  = W / salto")
    print("  X             = S / patada")
    print()
    print("P2:")
    print("  Stick <- / -> = flechas izquierda / derecha")
    print("  Stick arriba  = flecha arriba / salto")
    print("  X             = flecha abajo / patada")
    print()
    print("MODO SEGURO:")
    print("  F8 = activar ambos joysticks")
    print("  F7 = desactivar y liberar todas las teclas")
    print("  Ctrl+C = cerrar")
    print("=" * 76)
    print("[SAFE] Bridge DESARMADO.")

    held = HeldKeys()

    p1 = PlayerState()
    p2 = PlayerState()

    armed = False
    old_f7 = False
    old_f8 = False
    last_focus = None

    try:
        while True:
            pygame.event.pump()
            now = time.monotonic()

            f7 = key_down(VK_F7)
            f8 = key_down(VK_F8)

            if f8 and not old_f8:
                armed = True
                print(f"\n[SAFE] DOS JOYSTICKS ACTIVADOS | FOCUS: {foreground_title()}")

            if f7 and not old_f7:
                armed = False
                held.release_all()
                reset_state(p1)
                reset_state(p2)
                print("\n[SAFE] JOYSTICKS DESACTIVADOS. Teclas liberadas.")

            old_f7 = f7
            old_f8 = f8

            if not armed:
                time.sleep(1.0 / POLL_HZ)
                continue

            title = foreground_title()
            if title != last_focus:
                print(f"[FOCUS] {title}")
                last_focus = title

            # P1 -> WASD
            handle_player(
                "P1",
                joy1,
                p1,
                held,
                now,
                SCAN_A,
                SCAN_D,
                SCAN_W,
                SCAN_S,
                extended=False,
            )

            # P2 -> flechas
            handle_player(
                "P2",
                joy2,
                p2,
                held,
                now,
                SCAN_LEFT,
                SCAN_RIGHT,
                SCAN_UP,
                SCAN_DOWN,
                extended=True,
            )

            time.sleep(1.0 / POLL_HZ)

    except KeyboardInterrupt:
        print("\nCerrando bridge...")

    finally:
        held.release_all()
        pygame.joystick.quit()
        pygame.quit()
        print("Todas las teclas fueron liberadas. OK.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
