
from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np


CASCADE_FILES = [
    "haarcascade_frontalface_default.xml",
    "haarcascade_frontalface_alt2.xml",
]


def _load_cascades():
    result = []
    for name in CASCADE_FILES:
        path = Path(cv2.data.haarcascades) / name
        cascade = cv2.CascadeClassifier(str(path))
        if not cascade.empty():
            result.append(cascade)
    return result


FACE_CASCADES = _load_cascades()


def _crop(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1 = max(0, min(w, int(x1)))
    x2 = max(0, min(w, int(x2)))
    y1 = max(0, min(h, int(y1)))
    y2 = max(0, min(h, int(y2)))

    if x2 <= x1 or y2 <= y1:
        return None

    return img[y1:y2, x1:x2]


def _dark_ratio(img, threshold=85):
    if img is None or img.size == 0:
        return 0.0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float((gray < threshold).mean())


def _edge_ratio(img):
    if img is None or img.size == 0:
        return 0.0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 140)
    return float((edges > 0).mean())


def _detect_main_face(img_bgr):
    if not FACE_CASCADES:
        return None

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)

    found = []

    for cascade in FACE_CASCADES:
        for src in (gray, equalized):
            faces = cascade.detectMultiScale(
                src,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(45, 45),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )

            for face in faces:
                found.append(
                    tuple(int(v) for v in face)
                )

    if not found:
        return None

    h, w = img_bgr.shape[:2]
    center_x = w / 2
    center_y = h / 2

    def priority(face):
        x, y, fw, fh = face
        cx = x + fw / 2
        cy = y + fh / 2
        area = fw * fh
        dist = (
            (cx - center_x) ** 2 +
            (cy - center_y) ** 2
        ) ** 0.5

        return area - dist * 100

    return max(found, key=priority)


def _estimate_skin_tone(face_roi):
    """
    V2:
    Ya no promedia toda la cara.

    Usa mejillas y zona central, filtra colores compatibles
    con piel y toma MEDIANA para resistir:
    - pelo
    - anteojos
    - ojos
    - sombras puntuales
    """
    if face_roi is None or face_roi.size == 0:
        return None, 0.0

    h, w = face_roi.shape[:2]

    patches = [
        _crop(face_roi, 0.12*w, 0.43*h, 0.34*w, 0.68*h),
        _crop(face_roi, 0.66*w, 0.43*h, 0.88*w, 0.68*h),
        _crop(face_roi, 0.34*w, 0.18*h, 0.66*w, 0.34*h),
    ]

    values = []

    for patch in patches:
        if patch is None or patch.size == 0:
            continue

        ycc = cv2.cvtColor(patch, cv2.COLOR_BGR2YCrCb)
        Y, Cr, Cb = cv2.split(ycc)

        skin_mask = (
            (Cr >= 128) & (Cr <= 185) &
            (Cb >= 70) & (Cb <= 145)
        )

        valid = Y[skin_mask]
        if valid.size:
            values.extend(valid.tolist())

    if len(values) < 25:
        return None, 0.0

    y_med = float(np.median(values))

    # Rangos deliberadamente amplios:
    # la iluminación de la webcam cambia mucho.
    if y_med >= 165:
        tone = "very_light"
    elif y_med >= 118:
        tone = "light"
    elif y_med >= 92:
        tone = "medium"
    elif y_med >= 72:
        tone = "tan"
    elif y_med >= 52:
        tone = "dark"
    else:
        tone = "very_dark"

    # No le damos mucha autoridad debido a la iluminación.
    confidence = 0.45
    return tone, confidence


def _dominant_hair_color(img_bgr, face_box):
    """
    Obtiene un color de referencia del cabello usando KMeans
    solamente sobre la zona superior próxima a la cabeza.

    Evita el error de V1 donde el fondo claro dominaba el promedio.
    """
    x, y, w, h = face_box

    roi = _crop(
        img_bgr,
        x + 0.03*w,
        y - 0.48*h,
        x + 0.97*w,
        y + 0.08*h,
    )

    if roi is None or roi.size < 100:
        return None, 0.0, None

    pixels = roi.reshape(-1, 3).astype(np.float32)

    # Limitar coste.
    if len(pixels) > 12000:
        idx = np.linspace(
            0,
            len(pixels)-1,
            12000,
            dtype=np.int32,
        )
        pixels = pixels[idx]

    criteria = (
        cv2.TERM_CRITERIA_EPS +
        cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.4,
    )

    _, labels, centers = cv2.kmeans(
        pixels,
        4,
        None,
        criteria,
        3,
        cv2.KMEANS_PP_CENTERS,
    )

    counts = np.bincount(
        labels.flatten(),
        minlength=len(centers),
    )

    candidates = []

    for count, center in zip(counts, centers):
        b, g, r = [float(v) for v in center]

        hsv = cv2.cvtColor(
            np.uint8([[[b, g, r]]]),
            cv2.COLOR_BGR2HSV,
        )[0, 0]

        H, S, V = [int(v) for v in hsv]

        # Quitar fondo claro.
        if V > 220 and S < 45:
            continue

        # Quitar verde del óvalo/debug si llegara a aparecer.
        if 35 <= H <= 90 and S > 100:
            continue

        # Evitar clusters minúsculos.
        if count < len(pixels) * 0.08:
            continue

        candidates.append(
            (count, V, S, np.array([b, g, r]))
        )

    if not candidates:
        return None, 0.0, None

    # Cabello suele ser uno de los clusters oscuros grandes,
    # no necesariamente EL más oscuro.
    candidates.sort(
        key=lambda t: (t[1], -t[0])
    )

    count, V, S, color = candidates[0]

    b, g, r = color

    # Etiqueta gruesa; selector V2 tolera brown/dark_brown.
    if V < 48:
        label = "black"
    elif V < 95:
        label = "dark_brown"
    elif r > g + 18 and r > b + 22:
        label = "red"
    elif V < 155:
        label = "brown"
    elif S < 35:
        label = "gray"
    else:
        label = "blond"

    confidence = min(
        0.80,
        0.40 + float(count / len(pixels))
    )

    return label, confidence, color


def _color_similarity_ratio(region, ref_bgr, tolerance=58):
    if (
        region is None or
        region.size == 0 or
        ref_bgr is None
    ):
        return 0.0

    arr = region.astype(np.float32)
    ref = np.asarray(ref_bgr, dtype=np.float32)

    dist = np.linalg.norm(
        arr - ref.reshape(1, 1, 3),
        axis=2,
    )

    return float((dist < tolerance).mean())


def _texture_hair_presence(region, ref_bgr, tolerance=62):
    """Presencia de pelo que exige similitud de color + textura local.

    Evita confundir con pelo negro zonas grandes y lisas como:
    auriculares, ropa oscura o padding negro del scan.
    """
    if region is None or region.size == 0 or ref_bgr is None:
        return 0.0, 0.0

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    arr = region.astype(np.float32)
    ref = np.asarray(ref_bgr, dtype=np.float32)
    dist = np.linalg.norm(arr - ref.reshape(1, 1, 3), axis=2)
    similar = dist < tolerance

    fgray = gray.astype(np.float32)
    mean = cv2.blur(fgray, (5, 5))
    mean2 = cv2.blur(fgray * fgray, (5, 5))
    local_std = np.sqrt(np.maximum(mean2 - mean * mean, 0.0))
    textured = local_std > 10.0

    edges = cv2.Canny(gray, 45, 120) > 0

    # Pelo real suele tener algo de textura interna; un bloque negro liso no.
    textured_presence = float((similar & textured).mean())
    edge_presence = float((similar & edges).mean())
    return textured_presence, edge_presence


def _estimate_hair_texture(top_region, ref_bgr):
    if top_region is None or top_region.size == 0 or ref_bgr is None:
        return None, 0.0

    gray = cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY)
    arr = top_region.astype(np.float32)
    ref = np.asarray(ref_bgr, dtype=np.float32)
    dist = np.linalg.norm(arr - ref.reshape(1, 1, 3), axis=2)
    similar = dist < 62

    if similar.mean() < 0.08:
        return None, 0.0

    edges = cv2.Canny(gray, 45, 120) > 0
    edge_in_hair = float((edges & similar).sum() / max(1, similar.sum()))

    fgray = gray.astype(np.float32)
    mean = cv2.blur(fgray, (5, 5))
    mean2 = cv2.blur(fgray * fgray, (5, 5))
    local_std = np.sqrt(np.maximum(mean2 - mean * mean, 0.0))
    texture_strength = float(np.median(local_std[similar])) if np.any(similar) else 0.0

    # Curly hair creates many short internal edges and local brightness changes.
    if edge_in_hair >= 0.052 or texture_strength >= 8.5:
        return "curly", 0.74
    if edge_in_hair >= 0.032 or texture_strength >= 5.0:
        return "wavy", 0.62
    return "straight", 0.55


def _estimate_hair(img_bgr, face_box):
    """V4: largo y textura de pelo sin confundir auriculares con pelo largo."""
    x, y, w, h = face_box

    hair_color, color_conf, ref_color = _dominant_hair_color(img_bgr, face_box)

    top = _crop(
        img_bgr,
        x - 0.05*w,
        y - 0.50*h,
        x + 1.05*w,
        y + 0.12*h,
    )

    top_dark = _dark_ratio(top, 115)

    if top_dark < 0.07:
        return {
            "bald": True,
            "hair_length": "bald",
            "hair_color": "none",
            "hair_texture": "none",
            "_confidence": {
                "bald": 0.78,
                "hair_length": 0.76,
                "hair_color": 0.0,
                "hair_texture": 0.75,
            },
        }

    # Zonas próximas a los laterales del rostro. No usamos regiones gigantes,
    # porque allí suelen aparecer auriculares/ropa/fondo.
    left_mid = _crop(
        img_bgr,
        x - 0.20*w,
        y + 0.56*h,
        x + 0.12*w,
        y + 1.02*h,
    )
    right_mid = _crop(
        img_bgr,
        x + 0.88*w,
        y + 0.56*h,
        x + 1.20*w,
        y + 1.02*h,
    )

    left_below = _crop(
        img_bgr,
        x - 0.12*w,
        y + 0.84*h,
        x + 0.20*w,
        y + 1.18*h,
    )
    right_below = _crop(
        img_bgr,
        x + 0.80*w,
        y + 0.84*h,
        x + 1.12*w,
        y + 1.18*h,
    )

    mid_l, mid_l_edge = _texture_hair_presence(left_mid, ref_color)
    mid_r, mid_r_edge = _texture_hair_presence(right_mid, ref_color)
    low_l, low_l_edge = _texture_hair_presence(left_below, ref_color)
    low_r, low_r_edge = _texture_hair_presence(right_below, ref_color)

    mid_presence = (mid_l + mid_r) / 2.0
    below_presence = (low_l + low_r) / 2.0

    # Long solo si realmente hay pelo texturado cerca/debajo de la mandíbula.
    # Esto elimina el falso "long" causado por cascos negros y padding negro.
    if below_presence >= 0.105:
        hair_length = "long"
        length_conf = 0.82
    elif mid_presence >= 0.072 or below_presence >= 0.062:
        hair_length = "medium"
        length_conf = 0.78
    else:
        hair_length = "short"
        length_conf = 0.70

    hair_texture, texture_conf = _estimate_hair_texture(top, ref_color)

    return {
        "bald": False,
        "hair_length": hair_length,
        "hair_color": hair_color,
        "hair_texture": hair_texture,
        "_confidence": {
            "bald": 0.88,
            "hair_length": length_conf,
            "hair_color": color_conf,
            "hair_texture": texture_conf,
        },
    }

def _estimate_glasses(face_roi):
    """V4: detector conservador de anteojos.

    V3 usaba HoughCircles y confundía ojos/cejas con lentes. Esta versión
    busca evidencia de *marco* alrededor de ambos ojos y, sobre todo, puente.

    Devuelve True solo con evidencia fuerte; False con evidencia clara de
    ausencia; None cuando la imagen es ambigua. El selector ignora None.
    """
    if face_roi is None or face_roi.size == 0:
        return None, 0.0

    h, w = face_roi.shape[:2]
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

    def region_metrics(x1, y1, x2, y2):
        roi = _crop(gray, x1*w, y1*h, x2*w, y2*h)
        if roi is None or roi.size == 0:
            return 0.0, 0.0
        edges = cv2.Canny(roi, 50, 130)
        return float((roi < 72).mean()), float((edges > 0).mean())

    # Cada ojo: bandas donde debería existir el contorno del lente.
    # El ojo/ceja por sí solos producen mucha señal arriba, por eso el score
    # depende especialmente de borde inferior, lateral y puente.
    left_bottom = region_metrics(0.14, 0.47, 0.47, 0.57)
    right_bottom = region_metrics(0.53, 0.47, 0.86, 0.57)

    left_outer = region_metrics(0.12, 0.31, 0.19, 0.54)
    right_outer = region_metrics(0.81, 0.31, 0.88, 0.54)

    left_inner = region_metrics(0.43, 0.31, 0.49, 0.54)
    right_inner = region_metrics(0.51, 0.31, 0.57, 0.54)

    bridge_dark, bridge_edge = region_metrics(0.45, 0.34, 0.55, 0.49)

    bottom_dark = min(left_bottom[0], right_bottom[0])
    bottom_edge = min(left_bottom[1], right_bottom[1])
    outer_edge = min(left_outer[1], right_outer[1])
    inner_edge = min(left_inner[1], right_inner[1])

    strong_bridge = bridge_dark >= 0.035 or bridge_edge >= 0.24
    strong_two_lenses = (
        (bottom_dark >= 0.025 and bottom_edge >= 0.09)
        or (bottom_edge >= 0.14 and outer_edge >= 0.11)
    )
    side_support = outer_edge >= 0.08 and inner_edge >= 0.08

    if strong_bridge and strong_two_lenses and side_support:
        confidence = min(
            0.97,
            0.82
            + min(0.08, bridge_edge * 0.20)
            + min(0.07, bottom_edge * 0.22),
        )
        return True, confidence

    # Ausencia bastante clara: sin puente y sin marco inferior bilateral.
    if bridge_dark < 0.018 and bottom_dark < 0.018 and bottom_edge < 0.085:
        return False, 0.93

    if bridge_dark < 0.025 and bottom_edge < 0.105:
        return False, 0.86

    # Ambiguo: mejor no forzar anteojos ni no-anteojos en el matching.
    return None, 0.35

def _estimate_facial_hair(face_roi):
    """
    V2 MUCHO más conservadora.

    V1 miraba zonas laterales demasiado grandes y,
    con pelo largo, terminaba interpretándolo como barba.

    Ahora barba se decide dentro de la zona central
    de mandíbula/mentón.
    """
    if face_roi is None or face_roi.size == 0:
        return {
            "beard": None,
            "moustache": None,
            "facial_hair_style": None,
            "_confidence": {},
        }

    h, w = face_roi.shape[:2]

    moustache_roi = _crop(
        face_roi,
        0.36*w,
        0.55*h,
        0.64*w,
        0.67*h,
    )

    jaw_left = _crop(
        face_roi,
        0.28*w,
        0.67*h,
        0.45*w,
        0.89*h,
    )

    jaw_right = _crop(
        face_roi,
        0.55*w,
        0.67*h,
        0.72*w,
        0.89*h,
    )

    chin = _crop(
        face_roi,
        0.40*w,
        0.76*h,
        0.60*w,
        0.95*h,
    )

    must_dark = _dark_ratio(moustache_roi, 90)

    jaw_scores = [
        _dark_ratio(jaw_left, 88),
        _dark_ratio(jaw_right, 88),
        _dark_ratio(chin, 88),
    ]

    beard_zones = sum(
        score > 0.15
        for score in jaw_scores
    )

    moustache = bool(must_dark > 0.24)
    beard = bool(beard_zones >= 2)

    # Cuando decimos False somos bastante conservadores.
    beard_conf = 0.82 if not beard else 0.72
    moustache_conf = 0.78 if not moustache else 0.68

    if beard and moustache:
        style = "full_beard"
    elif beard:
        style = "beard"
    elif moustache:
        style = "moustache"
    else:
        style = "none"

    return {
        "beard": beard,
        "moustache": moustache,
        "facial_hair_style": style,
        "_confidence": {
            "beard": beard_conf,
            "moustache": moustache_conf,
            "facial_hair_style": min(
                beard_conf,
                moustache_conf,
            ),
        },
    }


def analyze_face(image_path: str | Path) -> dict:
    image_path = Path(image_path)

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(
            f"No se pudo abrir la imagen: {image_path}"
        )

    face_box = _detect_main_face(img)
    if face_box is None:
        raise RuntimeError(
            "No se detectó una cara en el scan."
        )

    x, y, w, h = face_box
    face_roi = _crop(
        img,
        x,
        y,
        x+w,
        y+h,
    )

    traits = {}
    confidence = {}

    # -------- skin
    skin_tone, skin_conf = _estimate_skin_tone(face_roi)
    traits["skin_tone"] = skin_tone
    confidence["skin_tone"] = skin_conf

    # -------- hair
    hair = _estimate_hair(img, face_box)
    confidence.update(hair.pop("_confidence"))
    traits.update(hair)

    # -------- glasses
    glasses, glasses_conf = _estimate_glasses(face_roi)
    traits["glasses"] = glasses
    confidence["glasses"] = glasses_conf

    # -------- facial hair
    facial = _estimate_facial_hair(face_roi)
    confidence.update(facial.pop("_confidence"))
    traits.update(facial)

    # V2: no inventamos lo que todavía no podemos medir bien.
    traits["freckles"] = None
    traits["age_group"] = None
    traits["eye_color"] = None

    confidence["freckles"] = 0.0
    confidence["age_group"] = 0.0
    confidence["eye_color"] = 0.0

    traits["_confidence"] = confidence

    # Convertir NumPy -> Python nativo.
    clean = {}

    for key, value in traits.items():
        if key == "_confidence":
            clean[key] = {
                k: (
                    v.item()
                    if isinstance(v, np.generic)
                    else float(v)
                )
                for k, v in value.items()
            }
        else:
            clean[key] = (
                value.item()
                if isinstance(value, np.generic)
                else value
            )

    return clean


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print(
            "Uso: python face_analyzer.py "
            "data/captures/player_1_scan.png"
        )
        raise SystemExit(1)

    result = analyze_face(sys.argv[1])
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
