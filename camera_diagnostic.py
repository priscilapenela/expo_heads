
import cv2
import os
import sys
import time

def backend_name(value):
    names = {
        cv2.CAP_DSHOW: "DirectShow",
        cv2.CAP_MSMF: "Media Foundation",
        cv2.CAP_ANY: "AUTO",
    }
    return names.get(value, str(value))

backends = [
    cv2.CAP_DSHOW,
    cv2.CAP_MSMF,
    cv2.CAP_ANY,
]

print("=== EXPO HEADS - CAMERA DIAGNOSTIC ===")
print("OpenCV:", cv2.__version__)
print("Python:", sys.version.split()[0])
print()

working = []

for backend in backends:
    print(f"--- Backend: {backend_name(backend)} ---")
    for index in range(5):
        cap = cv2.VideoCapture(index, backend)

        if not cap.isOpened():
            print(f"[X] Cámara {index}: no abre")
            cap.release()
            continue

        # Darle un momento a la cámara.
        time.sleep(0.25)

        ok, frame = cap.read()

        if not ok or frame is None:
            print(f"[!] Cámara {index}: abre, pero no entrega imagen")
            cap.release()
            continue

        h, w = frame.shape[:2]
        print(f"[OK] Cámara {index}: {w}x{h}")

        working.append((index, backend, frame.copy()))
        cap.release()

    print()

if not working:
    print("RESULTADO: No se encontró ninguna cámara accesible.")
    print()
    print("Revisá:")
    print("- Configuración de Windows > Privacidad y seguridad > Cámara")
    print("- Permitir acceso a la cámara")
    print("- Permitir que las aplicaciones de escritorio accedan a la cámara")
    print("- Cerrá Zoom / Meet / Discord / OBS / app Cámara")
    print("- Revisá la cámara en Administrador de dispositivos")
    sys.exit(1)

index, backend, frame = working[0]
output = os.path.abspath("camera_test_frame.png")
cv2.imwrite(output, frame)

print("RESULTADO: Cámara detectada.")
print(f"Índice recomendado: {index}")
print(f"Backend recomendado: {backend_name(backend)}")
print(f"Frame de prueba guardado en: {output}")
