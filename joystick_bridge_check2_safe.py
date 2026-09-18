"""
Expo Heads - JOYSTICK CHECK 2 SAFE

Diagnostico seguro:
- El bridge arranca DESARMADO: no inyecta ninguna tecla.
- Inicia el partido normalmente.
- Cuando ya ves la cancha / countdown, presiona F8 para ACTIVAR joystick.
- F7 desactiva y libera todas las teclas.

P1:
  Stick izquierda/derecha -> A / D
  Stick arriba            -> W
  Boton X (boton 2)       -> S
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
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

SCAN_W = 0x11
SCAN_A = 0x1E
SCAN_S = 0x1F
SCAN_D = 0x20

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
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]

user32 = ctypes.windll.user32

def send_scan(scan, down):
    flags = KEYEVENTF_SCANCODE | (0 if down else KEYEVENTF_KEYUP)
    inp = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(0, scan, flags, 0, 0),
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

    def press(self, scan):
        if scan not in self.down:
            if send_scan(scan, True):
                self.down.add(scan)

    def release(self, scan):
        if scan in self.down:
            send_scan(scan, False)
            self.down.discard(scan)

    def release_all(self):
        for scan in list(self.down):
            send_scan(scan, False)
        self.down.clear()

MOVE_DEADZONE = 0.35
JUMP_THRESHOLD = -0.60
JUMP_RESET = -0.25
KICK_BUTTON = 2

JUMP_PULSE = 0.14
KICK_PULSE = 0.12
POLL_HZ = 120

def main():
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()

    print("=" * 72)
    print("EXPO HEADS - JOYSTICK CHECK 2 SAFE")
    print("=" * 72)
    print(f"Joysticks detectados: {count}")

    if count < 1:
        print("[ERROR] No se detecto joystick.")
        return 1

    joy = pygame.joystick.Joystick(0)
    joy.init()

    print(f"[GAMEPAD] P1: {joy.get_name()}")
    print()
    print("IMPORTANTE:")
    print("  1) El bridge inicia DESARMADO.")
    print("  2) Inicia Expo Heads y entra a 1 VS 1.")
    print("  3) Cuando YA veas la cancha/countdown, presiona F8.")
    print()
    print("  F8 = ACTIVAR joystick")
    print("  F7 = DESACTIVAR joystick y liberar teclas")
    print("  Ctrl+C = cerrar bridge")
    print()
    print("Controles al activar:")
    print("  Stick <- / -> = mover")
    print("  Stick arriba  = saltar")
    print("  X             = patear")
    print("=" * 72)
    print("[SAFE] Bridge DESARMADO. No se esta enviando ninguna tecla.")

    held = HeldKeys()
    armed = False
    old_f7 = False
    old_f8 = False
    last_dir = None
    last_focus = None

    jump_latched = False
    jump_release_at = 0.0
    kick_latched = False
    kick_release_at = 0.0

    try:
        while True:
            pygame.event.pump()
            now = time.monotonic()

            f7 = key_down(VK_F7)
            f8 = key_down(VK_F8)

            if f8 and not old_f8:
                armed = True
                last_dir = None
                print(f"\n[SAFE] JOYSTICK ACTIVADO | FOCUS: {foreground_title()}")

            if f7 and not old_f7:
                armed = False
                held.release_all()
                jump_latched = False
                kick_latched = False
                jump_release_at = 0.0
                kick_release_at = 0.0
                last_dir = None
                print("\n[SAFE] JOYSTICK DESACTIVADO. Todas las teclas fueron liberadas.")

            old_f7 = f7
            old_f8 = f8

            if not armed:
                time.sleep(1.0 / POLL_HZ)
                continue

            title = foreground_title()
            if title != last_focus:
                print(f"[FOCUS] {title}")
                last_focus = title

            # Horizontal
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
                if direction == "LEFT":
                    print(f"[P1] <- {x:+.2f} => A")
                elif direction == "RIGHT":
                    print(f"[P1] -> {x:+.2f} => D")
                else:
                    print(f"[P1] -- {x:+.2f} => libre")
                last_dir = direction

            # Jump: single pulse per upward gesture
            y = joy.get_axis(1)
            if y < JUMP_THRESHOLD and not jump_latched:
                jump_latched = True
                held.press(SCAN_W)
                jump_release_at = now + JUMP_PULSE
                print(f"[P1] ^ axis1={y:+.2f} => W / SALTO")

            if jump_release_at and now >= jump_release_at:
                held.release(SCAN_W)
                jump_release_at = 0.0

            if jump_latched and y > JUMP_RESET:
                jump_latched = False

            # Kick: one pulse per X press
            pressed = bool(joy.get_button(KICK_BUTTON))
            if pressed and not kick_latched:
                kick_latched = True
                held.press(SCAN_S)
                kick_release_at = now + KICK_PULSE
                print("[P1] X boton=2 => S / PATADA")

            if kick_release_at and now >= kick_release_at:
                held.release(SCAN_S)
                kick_release_at = 0.0

            if kick_latched and not pressed:
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
