"""
Expo Heads - JOYSTICK CHECK 1B
Prueba de bridge usando SCANCODES fisicos de teclado para SDL/Pygame.

P1:
- stick izq -> A (scan code 0x1E)
- stick der -> D (scan code 0x20)
- centro    -> suelta A/D

No agrega salto ni patada todavia.
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
SCAN_A = 0x1E
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
            self.down.add(scan)
            if not ok:
                print("[WARN] SendInput no pudo inyectar KEYDOWN")

    def release(self, scan: int):
        if scan in self.down:
            ok = send_scan(scan, False)
            self.down.remove(scan)
            if not ok:
                print("[WARN] SendInput no pudo inyectar KEYUP")

    def release_all(self):
        for scan in list(self.down):
            send_scan(scan, False)
        self.down.clear()


DEADZONE = 0.35
POLL_HZ = 120


def main():
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    print("=" * 72)
    print("EXPO HEADS - JOYSTICK CHECK 1B (SCANCODE)")
    print("=" * 72)
    print(f"Joysticks detectados: {count}")

    if count < 1:
        print("[ERROR] No se detecto ningun joystick.")
        return 1

    joy = pygame.joystick.Joystick(0)
    joy.init()

    print(f"[GAMEPAD] P1 detectado: {joy.get_name()}")
    print("Modo de inyeccion: SCANCODE fisico")
    print("  Stick izquierda -> A (scan 0x1E)")
    print("  Stick derecha   -> D (scan 0x20)")
    print("  Centro          -> libera A/D")
    print()
    print("IMPORTANTE:")
    print("  1) Deja este script abierto.")
    print("  2) Inicia Expo Heads y entra a 1 VS 1.")
    print("  3) Hace click una vez sobre la ventana del partido.")
    print("  4) Move el stick.")
    print("  5) Para salir del bridge: Ctrl+C")
    print("=" * 72)

    held = HeldKeys()
    last_dir = None
    last_window = None

    try:
        while True:
            pygame.event.pump()

            x = joy.get_axis(0)
            if x < -DEADZONE:
                direction = "LEFT"
                held.release(SCAN_D)
                held.press(SCAN_A)
            elif x > DEADZONE:
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
                    print(f"[P1] <- axis0={x:+.2f} => SCAN A")
                elif direction == "RIGHT":
                    print(f"[P1] -> axis0={x:+.2f} => SCAN D")
                else:
                    print(f"[P1] -- axis0={x:+.2f} => libre")
                last_dir = direction

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
