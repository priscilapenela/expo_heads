
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


def _estimate_hair(img_bgr, face_box):
    x, y, w, h = face_box

    hair_color, color_conf, ref_color = (
        _dominant_hair_color(img_bgr, face_box)
    )

    top = _crop(
        img_bgr,
        x - 0.10*w,
        y - 0.45*h,
        x + 1.10*w,
        y + 0.10*h,
    )

    left_low = _crop(
        img_bgr,
        x - 0.55*w,
        y + 0.55*h,
        x + 0.15*w,
        y + 1.45*h,
    )

    right_low = _crop(
        img_bgr,
        x + 0.85*w,
        y + 0.55*h,
        x + 1.55*w,
        y + 1.45*h,
    )

    top_dark = _dark_ratio(top, 115)

    # Combina color similar al pelo + oscuridad;
    # esto reduce que una pared o ropa clara parezca pelo largo.
    left_sim = _color_similarity_ratio(
        left_low,
        ref_color,
    )
    right_sim = _color_similarity_ratio(
        right_low,
        ref_color,
    )

    low_presence = max(left_sim, right_sim)

    if top_dark < 0.08:
        bald = True
        hair_length = "bald"
        hair_color = "none"
        hair_texture = "none"
        length_conf = 0.70
        bald_conf = 0.70

    else:
        bald = False
        bald_conf = 0.82

        if low_presence >= 0.24:
            hair_length = "long"
            length_conf = 0.85
        elif low_presence >= 0.12:
            hair_length = "medium"
            length_conf = 0.70
        else:
            hair_length = "short"
            length_conf = 0.65

        # Textura todavía es demasiado frágil.
        # Mejor "no sé" que afirmar algo incorrecto.
        hair_texture = None

    return {
        "bald": bald,
        "hair_length": hair_length,
        "hair_color": hair_color,
        "hair_texture": hair_texture,
        "_confidence": {
            "bald": bald_conf,
            "hair_length": length_conf,
            "hair_color": color_conf,
            "hair_texture": 0.0,
        },
    }


def _estimate_glasses(face_roi):
    """
    V3 - detector de anteojos mejorado.

    La V2 dependía demasiado de píxeles oscuros.
    Eso falla con marcos:
    - finos
    - transparentes
    - metálicos
    - claros

    V3 combina:
    - densidad de bordes
    - HoughCircles para lentes grandes
    - HoughLinesP para patillas/puente/marcos
    """
    if face_roi is None or face_roi.size == 0:
        return None, 0.0

    h, w = face_roi.shape[:2]

    eye_band = _crop(
        face_roi,
        0.08*w,
        0.18*h,
        0.92*w,
        0.55*h,
    )

    if eye_band is None or eye_band.size == 0:
        return None, 0.0

    # Trabajamos ampliado para conservar marcos finos.
    scale = 2
    enlarged = cv2.resize(
        eye_band,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(
        enlarged,
        cv2.COLOR_BGR2GRAY,
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )
    gray = clahe.apply(gray)

    blur = cv2.GaussianBlur(
        gray,
        (5, 5),
        1.2,
    )

    edges = cv2.Canny(
        blur,
        45,
        120,
    )

    eh, ew = edges.shape[:2]

    # --------------------------------------------------
    # Círculos / lentes
    # --------------------------------------------------
    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(20, int(ew * 0.20)),
        param1=100,
        param2=18,
        minRadius=max(8, int(ew * 0.07)),
        maxRadius=max(14, int(ew * 0.22)),
    )

    circle_count = 0

    if circles is not None:
        detected_circles = np.round(
            circles[0]
        ).astype(int)

        # Solo círculos razonablemente ubicados
        # a izquierda/derecha del centro.
        for cx, cy, radius in detected_circles:
            if (
                int(0.08*ew) <= cx <= int(0.92*ew)
                and int(0.10*eh) <= cy <= int(0.90*eh)
            ):
                circle_count += 1

    # --------------------------------------------------
    # Líneas de marco / puente / patillas
    # --------------------------------------------------
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=20,
        minLineLength=max(12, int(ew * 0.08)),
        maxLineGap=max(5, int(ew * 0.035)),
    )

    useful_lines = 0

    if lines is not None:
        for line in lines[:, 0]:
            x1, y1, x2, y2 = [
                int(v) for v in line
            ]

            dx = x2 - x1
            dy = y2 - y1
            length = (dx*dx + dy*dy) ** 0.5

            if length < ew * 0.07:
                continue

            # líneas horizontales, verticales o diagonales
            # propias de marcos.
            angle = abs(
                np.degrees(
                    np.arctan2(dy, dx)
                )
            )

            if (
                angle < 25
                or angle > 155
                or 65 < angle < 115
            ):
                useful_lines += 1

    edge_density = float(
        (edges > 0).mean()
    )

    # --------------------------------------------------
    # Score de evidencia
    # --------------------------------------------------
    evidence = 0.0

    if circle_count >= 2:
        evidence += 0.65
    elif circle_count == 1:
        evidence += 0.35

    if useful_lines >= 7:
        evidence += 0.30
    elif useful_lines >= 4:
        evidence += 0.18
    elif useful_lines >= 2:
        evidence += 0.08

    if edge_density > 0.16:
        evidence += 0.18
    elif edge_density > 0.11:
        evidence += 0.10

    detected = bool(evidence >= 0.48)

    if detected:
        confidence = min(
            0.96,
            0.68 + evidence * 0.25
        )
    else:
        # False con confianza moderada,
        # porque algunos anteojos son muy difíciles.
        confidence = max(
            0.45,
            0.72 - evidence * 0.25
        )

    return detected, confidence


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
            "Uso: python face_analyzer_v2.py "
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
