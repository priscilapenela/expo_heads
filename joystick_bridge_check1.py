"""
Expo Heads - JOYSTICK CHECK 1
Xbox 360 / XInput compatible

Objetivo de este check:
- Joystick 0, stick izquierdo horizontal (axis 0)
- izquierda -> mantiene A
- derecha   -> mantiene D
- centro    -> suelta A y D

No implementa salto ni patada todavia.
El juego sigue usando sus controles originales; este bridge convierte el
joystick en pulsaciones reales de teclado de Windows.
"""

import sys
import time
import ctypes
from ctypes import wintypes

try:
    import pygame
except ImportError:
    print("ERROR: pygame no esta instalado en este Python.")
    print("Ejecutalo desde el mismo .venv de Expo Heads.")
    raise SystemExit(1)

if sys.platform != "win32":
    print("ERROR: este bridge esta preparado para Windows.")
    raise SystemExit(1)

# -----------------------------------------------------------------------------
# Windows SendInput
# -----------------------------------------------------------------------------
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

VK_A = 0x41
VK_D = 0x44

ULONG_PTR = wintypes.WPARAM


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


SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT


def _send_key(vk: int, down: bool) -> None:
    flags = 0 if down else KEYEVENTF_KEYUP
    inp = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=vk,
            wScan=0,
            dwFlags=flags,
            time=0,
            dwExtraInfo=0,
        ),
    )
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


class HeldKeys:
    def __init__(self):
        self.down = set()

    def press(self, vk: int) -> None:
        if vk not in self.down:
            _send_key(vk, True)
            self.down.add(vk)

    def release(self, vk: int) -> None:
        if vk in self.down:
            _send_key(vk, False)
            self.down.remove(vk)

    def release_all(self) -> None:
        for vk in list(self.down):
            _send_key(vk, False)
        self.down.clear()


# -----------------------------------------------------------------------------
# Joystick
# -----------------------------------------------------------------------------
DEADZONE = 0.35
POLL_HZ = 120


def main() -> int:
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    print("=" * 64)
    print("EXPO HEADS - JOYSTICK CHECK 1")
    print("=" * 64)
    print(f"Joysticks detectados: {count}")

    if count < 1:
        print("[ERROR] No se detecto ningun joystick.")
        return 1

    joy = pygame.joystick.Joystick(0)
    joy.init()

    print(f"[GAMEPAD] P1 detectado: {joy.get_name()}")
    print(f"[GAMEPAD] Ejes: {joy.get_numaxes()} | Botones: {joy.get_numbuttons()}")
    print()
    print("CHECK 1 ACTIVO:")
    print("  Stick izquierda -> A")
    print("  Stick derecha   -> D")
    print("  Centro           -> suelta A/D")
    print()
    print("Deja esta consola abierta, inicia Expo Heads y entra a 1 VS 1.")
    print("Para cerrar el bridge: Ctrl+C")
    print("=" * 64)

    held = HeldKeys()
    last_direction = None
    sleep_time = 1.0 / POLL_HZ

    try:
        while True:
            # Mantiene actualizado el estado del joystick incluso sin ventana pygame.
            pygame.event.pump()

            # Si se desconecta, liberar teclas y esperar.
            if pygame.joystick.get_count() < 1 or not joy.get_init():
                held.release_all()
                time.sleep(0.25)
                continue

            x = joy.get_axis(0)

            if x < -DEADZONE:
                direction = "LEFT"
                held.release(VK_D)
                held.press(VK_A)
            elif x > DEADZONE:
                direction = "RIGHT"
                held.release(VK_A)
                held.press(VK_D)
            else:
                direction = "CENTER"
                held.release(VK_A)
                held.release(VK_D)

            if direction != last_direction:
                if direction == "LEFT":
                    print(f"[P1] <-  axis0={x:+.2f}  => A")
                elif direction == "RIGHT":
                    print(f"[P1] ->  axis0={x:+.2f}  => D")
                else:
                    print(f"[P1] --  axis0={x:+.2f}  => libre")
                last_direction = direction

            time.sleep(sleep_time)

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
