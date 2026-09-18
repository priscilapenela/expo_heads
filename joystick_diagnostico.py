import sys
import time
import pygame

print('=' * 60)
print('EXPO HEADS - DIAGNOSTICO DE JOYSTICK')
print('=' * 60)
print('Python:', sys.version.split()[0])
print('Pygame:', pygame.version.ver)

pygame.init()
pygame.joystick.init()

count = pygame.joystick.get_count()
print('\nJoysticks detectados por pygame:', count)

joysticks = []
for i in range(count):
    joy = pygame.joystick.Joystick(i)
    joy.init()
    joysticks.append(joy)
    print(f'\n[GAMEPAD {i}]')
    print('  Nombre  :', joy.get_name())
    try:
        print('  GUID    :', joy.get_guid())
    except Exception:
        pass
    print('  Ejes    :', joy.get_numaxes())
    print('  Botones :', joy.get_numbuttons())
    print('  Hats    :', joy.get_numhats())

if count == 0:
    print('\n[RESULTADO] Pygame NO esta detectando ningun joystick.')
    print('Proba primero que Windows lo vea (joy.cpl), y luego volve a ejecutar este archivo.')
    input('\nENTER para cerrar...')
    pygame.quit()
    raise SystemExit

print('\n[RESULTADO] Pygame SI detecta el joystick.')
print('Ahora move el stick izquierdo y presiona X durante unos segundos.')
print('Para salir: ESC o cerrar la ventana.\n')

screen = pygame.display.set_mode((640, 240))
pygame.display.set_caption('Expo Heads - Diagnostico joystick')
font = pygame.font.Font(None, 28)
clock = pygame.time.Clock()
running = True
last_line = ''

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    joy = joysticks[0]
    axes = [round(joy.get_axis(i), 2) for i in range(joy.get_numaxes())]
    buttons = [i for i in range(joy.get_numbuttons()) if joy.get_button(i)]
    hats = [joy.get_hat(i) for i in range(joy.get_numhats())]
    line = f'Ejes={axes}  Botones={buttons}  Hats={hats}'
    if line != last_line:
        print(line)
        last_line = line

    screen.fill((25, 25, 25))
    lines = [
        f'Joystick 0: {joy.get_name()}',
        f'Ejes: {axes}',
        f'Botones presionados: {buttons}',
        f'Hats: {hats}',
        'Move el stick / presiona X. ESC para salir.'
    ]
    y = 20
    for text in lines:
        surf = font.render(text, True, (235, 235, 235))
        screen.blit(surf, (20, y))
        y += 38
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
