from pathlib import Path
from PIL import Image
import shutil
import sys

ROOT = Path(__file__).resolve().parent
IMG_DIR = ROOT / "data" / "images"

# Fondo que realmente usa el partido.
BACKGROUND_CANDIDATES = [
    IMG_DIR / "pozadina.PNG",
    IMG_DIR / "pozadina.png",
]

# PNG del marcador. Podés reemplazar este archivo por otro manteniendo el nombre.
MARKER_CANDIDATES = [
    IMG_DIR / "marcador.png",
    IMG_DIR / "marcador.PNG",
]

# Ajustes visuales. Si queda corrido, cambiá estos valores.
TARGET_WIDTH_RATIO = 0.36   # ancho del marcador respecto al fondo
Y_RATIO = 0.040             # altura desde arriba respecto al fondo
CROP_BLACK_BG = True        # elimina fondo negro del PNG si no tiene transparencia


def find_existing(candidates, label):
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"No encontré {label}. Busqué:\n" +
        "\n".join(f" - {p}" for p in candidates)
    )


def crop_non_black(img):
    """
    Recorta el marco negro alrededor del PNG.
    Si el PNG ya tiene transparencia, usa alpha.
    Si no, toma como contenido todo pixel que no sea casi negro.
    """
    img = img.convert("RGBA")
    px = img.load()

    minx, miny = img.width, img.height
    maxx, maxy = -1, -1

    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]

            # Si tiene alpha real, respetarlo.
            if a > 10 and (r > 18 or g > 18 or b > 18):
                minx = min(minx, x)
                miny = min(miny, y)
                maxx = max(maxx, x)
                maxy = max(maxy, y)

    if maxx < minx or maxy < miny:
        return img

    return img.crop((minx, miny, maxx + 1, maxy + 1))


def remove_black_background(img):
    """
    Convierte el fondo casi negro en transparente para que sólo quede la barra.
    """
    img = img.convert("RGBA")
    px = img.load()

    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if r < 18 and g < 18 and b < 18:
                px[x, y] = (0, 0, 0, 0)

    return img


def main():
    bg_path = find_existing(BACKGROUND_CANDIDATES, "el fondo del partido pozadina.PNG/pozadina.png")
    marker_path = find_existing(MARKER_CANDIDATES, "el marcador marcador.png")

    print(f"[OK] Fondo detectado: {bg_path}")
    print(f"[OK] Marcador detectado: {marker_path}")

    backup_dir = ROOT / "backup_marcador_overlay"
    backup_dir.mkdir(exist_ok=True)

    backup_path = backup_dir / bg_path.name
    shutil.copy2(bg_path, backup_path)
    print(f"[OK] Backup creado: {backup_path}")

    bg = Image.open(bg_path).convert("RGBA")
    marker = Image.open(marker_path).convert("RGBA")

    if CROP_BLACK_BG:
        marker = crop_non_black(marker)
        marker = remove_black_background(marker)

    target_w = int(bg.width * TARGET_WIDTH_RATIO)
    scale = target_w / marker.width
    target_h = int(marker.height * scale)

    # Mantener pixel-art: NEAREST evita suavizado borroso.
    marker = marker.resize((target_w, target_h), Image.Resampling.NEAREST)

    x = (bg.width - target_w) // 2
    y = int(bg.height * Y_RATIO)

    bg.alpha_composite(marker, (x, y))

    # Guardar sobre el fondo real.
    # Conservamos PNG. Si el fondo original no tenía alpha, igual el juego lo lee bien.
    bg.save(bg_path)

    print("[OK] Marcador aplicado sobre el fondo.")
    print(f"[INFO] Posición usada: x={x}, y={y}, ancho={target_w}, alto={target_h}")
    print()
    print("Abrí el launcher y probá un partido.")
    print("Si lo querés más grande/chico o más arriba/abajo, avisame y ajustamos TARGET_WIDTH_RATIO / Y_RATIO.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print()
        print("[ERROR]", e)
        print()
        print("Verificá que estés ejecutando este script desde la raíz del proyecto Expo Heads,")
        print("donde existen las carpetas data/images.")
        input("Presioná ENTER para salir...")
        sys.exit(1)

    input("Presioná ENTER para salir...")
