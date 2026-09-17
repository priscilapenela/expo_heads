
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

    # CHECK HAIR 2F:
    # Los bordes altos por sí solos no alcanzan para declarar curly: flequillo,
    # reflejos y anteojos pueden generar muchos edges. Exigimos también
    # variación local real del cabello.
    if (
        texture_strength >= 8.8
        or (edge_in_hair >= 0.085 and texture_strength >= 6.8)
    ):
        return "curly", 0.74

    if (
        texture_strength >= 4.6
        or edge_in_hair >= 0.040
    ):
        return "wavy", 0.68

    return "straight", 0.58




def _hair_texture_region_metrics(region, ref_bgr, tolerance=62):
    """
    CHECK FACE 4A:
    mide textura solo sobre píxeles similares al color de cabello.

    Devuelve ocupación, densidad de bordes y variación local.
    """
    if region is None or region.size == 0 or ref_bgr is None:
        return None

    arr = region.astype(np.float32)
    ref = np.asarray(ref_bgr, dtype=np.float32)
    dist = np.linalg.norm(arr - ref.reshape(1, 1, 3), axis=2)
    similar = dist < tolerance

    occupancy = float(similar.mean())
    if occupancy < 0.025 or int(similar.sum()) < 12:
        return {
            "occupancy": occupancy,
            "edge": 0.0,
            "std": 0.0,
        }

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 45, 120) > 0
    edge_in_hair = float(
        (edges & similar).sum() / max(1, similar.sum())
    )

    fgray = gray.astype(np.float32)
    mean = cv2.blur(fgray, (5, 5))
    mean2 = cv2.blur(fgray * fgray, (5, 5))
    local_std = np.sqrt(
        np.maximum(mean2 - mean * mean, 0.0)
    )
    texture_std = float(
        np.median(local_std[similar])
    ) if np.any(similar) else 0.0

    return {
        "occupancy": occupancy,
        "edge": edge_in_hair,
        "std": texture_std,
    }


def _estimate_hair_texture_v4(img_bgr, face_box, ref_bgr):
    """
    CHECK FACE 4A.

    El detector anterior miraba casi solo la coronilla. Flequillo, reflejos,
    marcos de anteojos y una raya marcada podían inflar los bordes y convertir
    pelo lacio/ondulado en "curly".

    V4 analiza varias zonas:
      - coronilla
      - lateral izquierdo
      - lateral derecho
      - caída inferior izquierda/derecha

    Curly exige textura fuerte en VARIAS regiones, no un pico aislado.
    """
    if ref_bgr is None:
        return None, 0.0

    x, y, w, h = face_box

    regions = [
        _crop(
            img_bgr,
            x - 0.05*w,
            y - 0.48*h,
            x + 1.05*w,
            y + 0.14*h,
        ),
        _crop(
            img_bgr,
            x - 0.18*w,
            y + 0.05*h,
            x + 0.18*w,
            y + 0.96*h,
        ),
        _crop(
            img_bgr,
            x + 0.82*w,
            y + 0.05*h,
            x + 1.18*w,
            y + 0.96*h,
        ),
        _crop(
            img_bgr,
            x - 0.12*w,
            y + 0.62*h,
            x + 0.25*w,
            y + 1.34*h,
        ),
        _crop(
            img_bgr,
            x + 0.75*w,
            y + 0.62*h,
            x + 1.12*w,
            y + 1.34*h,
        ),
    ]

    metrics = [
        _hair_texture_region_metrics(region, ref_bgr)
        for region in regions
    ]
    metrics = [
        m for m in metrics
        if m is not None and m["occupancy"] >= 0.04
    ]

    if not metrics:
        return None, 0.0

    stds = np.asarray(
        [m["std"] for m in metrics],
        dtype=np.float32,
    )
    edges = np.asarray(
        [m["edge"] for m in metrics],
        dtype=np.float32,
    )

    robust_std = float(np.median(stds))
    robust_edge = float(np.median(edges))

    strong_curly_regions = int(
        np.sum(
            (stds >= 7.2)
            & (edges >= 0.095)
        )
    )
    strong_wave_regions = int(
        np.sum(
            (stds >= 4.0)
            | (edges >= 0.065)
        )
    )

    # Curly: señal sostenida, no un único parche muy texturado.
    if (
        strong_curly_regions >= 2
        and robust_std >= 6.6
        and robust_edge >= 0.085
    ):
        texture = "curly"
        confidence = min(
            0.86,
            0.72
            + 0.025 * strong_curly_regions
            + min(0.06, max(0.0, robust_std - 6.6) * 0.02),
        )

    # Wavy: textura intermedia o bordes repetidos en varias zonas.
    elif (
        strong_wave_regions >= 2
        and (
            robust_std >= 3.7
            or robust_edge >= 0.060
        )
    ):
        texture = "wavy"
        confidence = 0.74

    else:
        texture = "straight"
        confidence = 0.70

    print(
        "[HAIR 4A TEXTURE] "
        f"regions={len(metrics)} "
        f"std={robust_std:.2f} "
        f"edge={robust_edge:.3f} "
        f"curly_regions={strong_curly_regions} "
        f"wave_regions={strong_wave_regions} "
        f"=> {texture}"
    )

    return texture, confidence


def _hair_similarity_mask(region, ref_bgr, tolerance=62):
    """Máscara simple de color similar al pelo de referencia."""
    if region is None or region.size == 0 or ref_bgr is None:
        return None

    arr = region.astype(np.float32)
    ref = np.asarray(ref_bgr, dtype=np.float32)
    dist = np.linalg.norm(arr - ref.reshape(1, 1, 3), axis=2)
    return dist < tolerance


def _hair_region_presence(region, ref_bgr, tolerance=62, require_texture=False):
    """
    Ocupación aproximada de cabello dentro de una región.

    Si require_texture=True, exige además variación local para reducir falsos
    positivos de fondos/ropa de color parecido.
    """
    mask = _hair_similarity_mask(region, ref_bgr, tolerance=tolerance)
    if mask is None or mask.size == 0:
        return 0.0

    if not require_texture:
        return float(mask.mean())

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean = cv2.blur(gray, (5, 5))
    mean2 = cv2.blur(gray * gray, (5, 5))
    local_std = np.sqrt(np.maximum(mean2 - mean * mean, 0.0))
    textured = local_std > 8.0

    return float((mask & textured).mean())


def _estimate_hair_v2_details(
    img_bgr,
    face_box,
    ref_color,
    hair_length,
    hair_texture,
):
    """
    CHECK HAIR 2D.

    Agrega una descripción más fina del peinado usando únicamente geometría
    frontal + color/texture del cabello ya estimado.

    Campos:
      - hair_shape_family
      - hair_volume
      - bangs
      - hair_tied
      - parting
      - face_framing

    Es deliberadamente conservador: si una señal no es suficientemente clara,
    devuelve None y baja confianza en vez de inventar un peinado.
    """
    x, y, w, h = face_box

    if hair_length == "bald" or ref_color is None:
        return {
            "hair_shape_family": "none",
            "hair_style_family": "none",
            "hair_volume": "low",
            "bangs": "none",
            "hair_tied": "none",
            "braid_count": "none",
            "braid_style": "none",
            "parting": "none",
            "face_framing": "none",
            "_confidence": {
                "hair_shape_family": 0.92,
                "hair_style_family": 0.92,
                "hair_volume": 0.90,
                "bangs": 0.90,
                "hair_tied": 0.90,
                "braid_count": 0.92,
                "braid_style": 0.92,
                "parting": 0.88,
                "face_framing": 0.90,
            },
        }

    # --------------------------------------------------
    # 1) VOLUMEN GENERAL
    # --------------------------------------------------
    top_outer = _crop(
        img_bgr,
        x - 0.22*w,
        y - 0.58*h,
        x + 1.22*w,
        y + 0.12*h,
    )
    top_presence = _hair_region_presence(
        top_outer,
        ref_color,
        require_texture=True,
    )

    side_left = _crop(
        img_bgr,
        x - 0.28*w,
        y + 0.05*h,
        x + 0.12*w,
        y + 0.82*h,
    )
    side_right = _crop(
        img_bgr,
        x + 0.88*w,
        y + 0.05*h,
        x + 1.28*w,
        y + 0.82*h,
    )

    side_left_presence = _hair_region_presence(
        side_left, ref_color, require_texture=True
    )
    side_right_presence = _hair_region_presence(
        side_right, ref_color, require_texture=True
    )
    side_presence = (side_left_presence + side_right_presence) / 2.0

    if top_presence >= 0.20 or side_presence >= 0.13:
        hair_volume = "high"
        volume_conf = 0.72
    elif top_presence <= 0.075 and side_presence <= 0.055:
        hair_volume = "low"
        volume_conf = 0.66
    else:
        hair_volume = "medium"
        volume_conf = 0.68

    # --------------------------------------------------
    # 2) FACE FRAMING
    # --------------------------------------------------
    frame_left = _crop(
        img_bgr,
        x - 0.12*w,
        y + 0.18*h,
        x + 0.18*w,
        y + 1.18*h,
    )
    frame_right = _crop(
        img_bgr,
        x + 0.82*w,
        y + 0.18*h,
        x + 1.12*w,
        y + 1.18*h,
    )

    frame_l = _hair_region_presence(
        frame_left, ref_color, require_texture=True
    )
    frame_r = _hair_region_presence(
        frame_right, ref_color, require_texture=True
    )
    frame_bilateral = min(frame_l, frame_r)
    frame_mean = (frame_l + frame_r) / 2.0

    if frame_bilateral >= 0.090 or frame_mean >= 0.125:
        face_framing = "strong"
        framing_conf = 0.72
    elif frame_mean >= 0.045:
        face_framing = "light"
        framing_conf = 0.64
    else:
        face_framing = "none"
        framing_conf = 0.62

    # --------------------------------------------------
    # 3) FLEQUILLO + PARTIDO
    # --------------------------------------------------
    # Dividimos la franja superior de la cara en izquierda/centro/derecha.
    forehead_left = _crop(
        img_bgr,
        x + 0.08*w,
        y - 0.03*h,
        x + 0.38*w,
        y + 0.28*h,
    )
    forehead_center = _crop(
        img_bgr,
        x + 0.38*w,
        y - 0.03*h,
        x + 0.62*w,
        y + 0.28*h,
    )
    forehead_right = _crop(
        img_bgr,
        x + 0.62*w,
        y - 0.03*h,
        x + 0.92*w,
        y + 0.28*h,
    )

    fh_l = _hair_region_presence(forehead_left, ref_color)
    fh_c = _hair_region_presence(forehead_center, ref_color)
    fh_r = _hair_region_presence(forehead_right, ref_color)
    fh_mean = (fh_l + fh_c + fh_r) / 3.0

    bangs = None
    bangs_conf = 0.32

    # Cortina: cabello a ambos lados con apertura central.
    if min(fh_l, fh_r) >= 0.12 and fh_c <= min(fh_l, fh_r) * 0.65:
        bangs = "curtain"
        bangs_conf = 0.68

    # Recto: ocupación clara y bastante uniforme sobre la frente.
    elif fh_mean >= 0.16 and max(fh_l, fh_c, fh_r) - min(fh_l, fh_c, fh_r) <= 0.10:
        bangs = "straight"
        bangs_conf = 0.66

    # Lateral: un costado domina claramente.
    elif max(fh_l, fh_r) >= 0.16 and abs(fh_l - fh_r) >= 0.08:
        bangs = "side"
        bangs_conf = 0.62

    elif fh_mean >= 0.075:
        bangs = "short"
        bangs_conf = 0.56

    elif fh_mean <= 0.035:
        bangs = "none"
        bangs_conf = 0.60

    parting = None
    parting_conf = 0.30

    # Curtain bangs implican una apertura central aunque la pose de la cabeza
    # haga que un lado ocupe más píxeles que el otro.
    if bangs == "curtain":
        parting = "center"
        parting_conf = 0.66
    elif fh_c <= 0.055 and min(fh_l, fh_r) >= 0.085:
        parting = "center"
        parting_conf = 0.64
    elif abs(fh_l - fh_r) >= 0.095 and max(fh_l, fh_r) >= 0.12:
        parting = "side"
        parting_conf = 0.60
    elif fh_mean <= 0.05:
        parting = "none"
        parting_conf = 0.52

    # --------------------------------------------------
    # 4) RECOGIDO
    # --------------------------------------------------
    # Bun: blob centrado por encima de la caja facial.
    bun_region = _crop(
        img_bgr,
        x + 0.20*w,
        y - 0.78*h,
        x + 0.80*w,
        y - 0.20*h,
    )
    bun_presence = _hair_region_presence(
        bun_region, ref_color, require_texture=True
    )

    # Ponytail: masa lateral exterior detrás de la cabeza.
    pony_left = _crop(
        img_bgr,
        x - 0.48*w,
        y - 0.02*h,
        x - 0.08*w,
        y + 0.82*h,
    )
    pony_right = _crop(
        img_bgr,
        x + 1.08*w,
        y - 0.02*h,
        x + 1.48*w,
        y + 0.82*h,
    )

    pony_l = _hair_region_presence(
        pony_left, ref_color, require_texture=True
    )
    pony_r = _hair_region_presence(
        pony_right, ref_color, require_texture=True
    )
    strongest_pony = max(pony_l, pony_r)

    hair_tied = None
    tied_conf = 0.30

    if bun_presence >= 0.10 and side_presence <= 0.095:
        hair_tied = "bun"
        tied_conf = 0.70
    elif (
        strongest_pony >= 0.075
        and abs(pony_l - pony_r) >= 0.035
        # CHECK FACE 4A:
        # pelo largo suelto también puede sobresalir del face box en un lado.
        # Si enmarca fuertemente AMBOS lados de la cara, priorizamos "loose".
        and frame_bilateral < 0.090
    ):
        hair_tied = "ponytail"
        tied_conf = 0.66
    elif hair_length in {"medium", "long"} and frame_mean <= 0.030 and side_presence <= 0.040:
        hair_tied = "tied_back"
        tied_conf = 0.56
    elif (
        face_framing == "strong"
        and frame_bilateral >= 0.090
        and bun_presence <= 0.060
    ):
        hair_tied = "none"
        tied_conf = 0.68
    elif strongest_pony <= 0.025 and bun_presence <= 0.045:
        hair_tied = "none"
        tied_conf = 0.56

    # --------------------------------------------------
    # 5) FAMILIA GENERAL
    # --------------------------------------------------
    family = None
    family_conf = 0.40

    if hair_tied == "bun":
        family = "bun"
        family_conf = max(0.70, tied_conf)

    elif hair_tied == "ponytail":
        family = "ponytail"
        family_conf = max(0.68, tied_conf)

    elif hair_tied == "tied_back":
        family = "tied_back"
        family_conf = max(0.58, tied_conf)

    elif (
        hair_texture == "curly"
        and hair_volume == "high"
        and hair_length in {"short", "medium"}
    ):
        family = "afro"
        family_conf = 0.66

    elif hair_length == "short":
        if hair_texture in {"curly", "wavy"} and hair_volume != "low":
            family = "messy_short"
            family_conf = 0.60
        elif parting == "side":
            family = "side_part"
            family_conf = 0.58
        else:
            family = "crop"
            family_conf = 0.55

    elif hair_length == "medium":
        # CHECK HAIR 2G:
        # si existe enmarcado fuerte pero además la longitud global quedó en
        # medium, evitamos asumir "bob" demasiado pronto. Bob requiere caída
        # cercana a la cara SIN evidencia profunda clara.
        if (
            face_framing == "strong"
            and hair_volume in {"low", "medium"}
            and hair_tied in {None, "none"}
        ):
            family = "bob"
            family_conf = 0.61
        elif hair_texture in {"curly", "wavy"}:
            family = "messy_medium"
            family_conf = 0.58
        else:
            family = "long_layered"
            family_conf = 0.54

    elif hair_length == "long":
        if hair_texture in {"wavy", "curly"}:
            family = "long_layered"
            family_conf = 0.70
        else:
            family = "long_loose"
            family_conf = 0.66

    # --------------------------------------------------
    # 6) HAIR V3: familia semántica para matching
    # --------------------------------------------------
    # hair_shape_family conserva geometría; hair_style_family describe
    # la identidad visual que usa el selector V4.
    if hair_tied == "bun":
        style_family = "bun"
    elif hair_tied == "ponytail":
        style_family = "ponytail"
    elif hair_tied == "tied_back":
        style_family = "tied_back"
    elif family == "afro":
        style_family = "afro"
    elif hair_length == "long":
        if hair_texture == "straight":
            style_family = "long_straight"
        elif hair_texture == "curly":
            style_family = "long_curly"
        else:
            style_family = "long_wavy"
    elif hair_length == "medium":
        if family == "bob":
            style_family = "bob"
        elif hair_texture == "curly":
            style_family = "medium_curly"
        else:
            style_family = "layered_medium"
    elif hair_length == "short":
        if family == "afro":
            style_family = "afro"
        elif hair_texture == "curly":
            style_family = "short_curly"
        elif hair_texture == "wavy":
            style_family = "short_wavy"
        else:
            style_family = "short_straight"
    else:
        style_family = family

    style_conf = max(
        0.54,
        min(0.84, family_conf + 0.04),
    )

    return {
        "hair_shape_family": family,
        "hair_style_family": style_family,
        "hair_volume": hair_volume,
        "bangs": bangs,
        "hair_tied": hair_tied,
        "parting": parting,
        "face_framing": face_framing,
        "_confidence": {
            "hair_shape_family": family_conf,
            "hair_style_family": style_conf,
            "hair_volume": volume_conf,
            "bangs": bangs_conf,
            "hair_tied": tied_conf,
            "parting": parting_conf,
            "face_framing": framing_conf,
        },
    }



def _deep_hair_presence(img_bgr, face_box, ref_color):
    """
    CHECK HAIR 2G:
    busca evidencia de pelo que siga cayendo debajo de mandíbula/cuello,
    aproximando pelo hasta hombros.

    Devuelve:
      - deep_presence: ocupación media bilateral
      - deep_edge: fuerza texturada media bilateral
      - bilateral_deep: mínimo entre ambos lados
    """
    x, y, w, h = face_box

    deep_left = _crop(
        img_bgr,
        x - 0.18*w,
        y + 1.05*h,
        x + 0.26*w,
        y + 1.62*h,
    )
    deep_right = _crop(
        img_bgr,
        x + 0.74*w,
        y + 1.05*h,
        x + 1.18*w,
        y + 1.62*h,
    )

    dl_presence, dl_edge = _texture_hair_presence(deep_left, ref_color)
    dr_presence, dr_edge = _texture_hair_presence(deep_right, ref_color)

    deep_presence = (dl_presence + dr_presence) / 2.0
    deep_edge = (dl_edge + dr_edge) / 2.0
    bilateral_deep = min(dl_presence, dr_presence)

    return {
        "deep_presence": deep_presence,
        "deep_edge": deep_edge,
        "bilateral_deep": bilateral_deep,
        "left_presence": dl_presence,
        "right_presence": dr_presence,
    }




def _estimate_braid_structure(
    img_bgr,
    face_box,
    ref_color,
    hair_length,
    details,
    deep_metrics,
):
    """
    CHECK HAIR 3A

    Detecta estructuras de trenza largas mediante geometría bilateral.

    Idea:
    - dos columnas texturadas de color similar al pelo bajando por ambos lados
    - continuidad profunda por debajo de mandíbula/cuello
    - volumen global bajo/medio (las trenzas compactan el cabello)
    - mayor presencia lateral que en la franja central inferior

    Es deliberadamente conservador. Si no hay evidencia fuerte devuelve
    "none" para no inventar trenzas.
    """
    default = {
        "hair_style_family": details.get("hair_style_family") or details.get("hair_shape_family"),
        "braid_count": "none",
        "braid_style": "none",
        "_confidence": {
            "hair_style_family": details.get("_confidence", {}).get(
                "hair_shape_family", 0.40
            ),
            "braid_count": 0.55,
            "braid_style": 0.55,
        },
    }

    if (
        hair_length != "long"
        or ref_color is None
        or details.get("hair_tied") in {"bun", "ponytail"}
    ):
        return default

    x, y, w, h = face_box

    left_strand = _crop(
        img_bgr,
        x - 0.38*w,
        y + 0.68*h,
        x + 0.20*w,
        y + 1.72*h,
    )
    right_strand = _crop(
        img_bgr,
        x + 0.80*w,
        y + 0.68*h,
        x + 1.38*w,
        y + 1.72*h,
    )
    center_lower = _crop(
        img_bgr,
        x + 0.25*w,
        y + 1.00*h,
        x + 0.75*w,
        y + 1.70*h,
    )

    left_presence, left_edge = _texture_hair_presence(
        left_strand, ref_color
    )
    right_presence, right_edge = _texture_hair_presence(
        right_strand, ref_color
    )
    center_presence, center_edge = _texture_hair_presence(
        center_lower, ref_color
    )

    side_mean = (left_presence + right_presence) / 2.0
    side_min = min(left_presence, right_presence)
    edge_min = min(left_edge, right_edge)

    bilateral_deep = float(
        deep_metrics.get("bilateral_deep", 0.0)
    )
    deep_presence = float(
        deep_metrics.get("deep_presence", 0.0)
    )

    volume = details.get("hair_volume")
    parting = details.get("parting")

    # Dos trenzas: dos "columnas" laterales compactas y profundas.
    concentration_ratio = (
        side_mean / max(0.001, center_presence)
    )

    twin_braids = (
        side_min >= 0.034
        and edge_min >= 0.010
        and bilateral_deep >= 0.038
        and deep_presence >= 0.052
        and side_mean >= max(0.058, center_presence * 1.10)
        and parting in {"center", "side", None}
        # CHECK FACE 4A:
        # el pelo largo suelto puede formar dos columnas laterales.
        # Para declararlo trenzas pedimos pelo compacto (volume=low)
        # o una concentración lateral claramente superior al centro.
        and (
            volume == "low"
            or concentration_ratio >= 1.30
        )
    )

    print(
        "[HAIR 4A BRAID CHECK] "
        f"side_min={side_min:.3f} "
        f"side_mean={side_mean:.3f} "
        f"edge_min={edge_min:.3f} "
        f"deep={deep_presence:.3f} "
        f"bilateral_deep={bilateral_deep:.3f} "
        f"center={center_presence:.3f} "
        f"ratio={concentration_ratio:.2f} "
        f"volume={volume} "
        f"parting={parting} "
        f"twin_braids={twin_braids}"
    )

    if twin_braids:
        # Fuerza combinada para no dar 0.95 por una sola métrica.
        strength = min(
            1.0,
            0.45
            + min(0.18, side_min * 1.4)
            + min(0.16, bilateral_deep * 0.8)
            + min(0.12, edge_min * 2.0),
        )
        conf = max(0.76, min(0.90, strength))

        return {
            "hair_style_family": "braided_long",
            "braid_count": "double",
            "braid_style": "twin_braids",
            "_confidence": {
                "hair_style_family": conf,
                "braid_count": min(0.92, conf + 0.04),
                "braid_style": min(0.92, conf + 0.03),
            },
        }

    return default

def _estimate_hair(img_bgr, face_box):
    """
    V6 / CHECK HAIR 2D:
    conserva largo, color y textura existentes y agrega descripción fina
    de peinado para el selector Hair V2.
    """
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

    # CHECK HAIR 3C
    # --------------------------------------------------------------
    # El criterio viejo decía "top_dark < 0.07 => bald".
    # Eso falla con:
    #   - pelo recogido / trenzado
    #   - raya central amplia
    #   - fondos claros
    #   - cabello claro
    #
    # Ahora "bald" requiere varias evidencias a la vez:
    #   1) muy poca señal oscura arriba,
    #   2) sin color de cabello confiable,
    #   3) sin presencia texturada de cabello alrededor del cuero cabelludo.
    top_hair_presence, top_hair_edge = _texture_hair_presence(
        top,
        ref_color,
    )

    crown_left = _crop(
        img_bgr,
        x - 0.12*w,
        y - 0.20*h,
        x + 0.32*w,
        y + 0.18*h,
    )
    crown_right = _crop(
        img_bgr,
        x + 0.68*w,
        y - 0.20*h,
        x + 1.12*w,
        y + 0.18*h,
    )

    crown_l_presence, crown_l_edge = _texture_hair_presence(
        crown_left,
        ref_color,
    )
    crown_r_presence, crown_r_edge = _texture_hair_presence(
        crown_right,
        ref_color,
    )

    crown_presence = max(crown_l_presence, crown_r_presence)
    crown_edge = max(crown_l_edge, crown_r_edge)

    bald_detected = bool(
        top_dark < 0.035
        and (
            ref_color is None
            or color_conf < 0.34
        )
        and top_hair_presence < 0.012
        and top_hair_edge < 0.006
        and crown_presence < 0.012
        and crown_edge < 0.006
    )

    print(
        "[HAIR 3C BALD CHECK] "
        f"top_dark={top_dark:.3f} "
        f"hair_color={hair_color} "
        f"color_conf={color_conf:.2f} "
        f"top_presence={top_hair_presence:.3f} "
        f"crown_presence={crown_presence:.3f} "
        f"bald={bald_detected}"
    )

    if bald_detected:
        return {
            "bald": True,
            "hair_length": "bald",
            "hair_color": "none",
            "hair_texture": "none",
            "hair_shape_family": "none",
            "hair_style_family": "none",
            "hair_volume": "low",
            "bangs": "none",
            "hair_tied": "none",
            "braid_count": "none",
            "braid_style": "none",
            "parting": "none",
            "face_framing": "none",
            "_confidence": {
                "bald": 0.90,
                "hair_length": 0.88,
                "hair_color": 0.0,
                "hair_texture": 0.0,
                "hair_shape_family": 0.92,
                "hair_style_family": 0.92,
                "hair_volume": 0.90,
                "bangs": 0.90,
                "hair_tied": 0.90,
                "braid_count": 0.92,
                "braid_style": 0.92,
                "parting": 0.88,
                "face_framing": 0.90,
            },
        }

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
        x - 0.14*w,
        y + 0.84*h,
        x + 0.24*w,
        y + 1.24*h,
    )
    right_below = _crop(
        img_bgr,
        x + 0.76*w,
        y + 0.84*h,
        x + 1.14*w,
        y + 1.24*h,
    )

    mid_l, mid_l_edge = _texture_hair_presence(left_mid, ref_color)
    mid_r, mid_r_edge = _texture_hair_presence(right_mid, ref_color)
    low_l, low_l_edge = _texture_hair_presence(left_below, ref_color)
    low_r, low_r_edge = _texture_hair_presence(right_below, ref_color)

    mid_presence = (mid_l + mid_r) / 2.0
    below_presence = (low_l + low_r) / 2.0

    strongest_low_presence = max(low_l, low_r)
    strongest_low_edge = max(low_l_edge, low_r_edge)

    deep = _deep_hair_presence(img_bgr, face_box, ref_color)
    deep_presence = deep["deep_presence"]
    deep_edge = deep["deep_edge"]
    bilateral_deep = deep["bilateral_deep"]

    if (
        # Evidencia profunda bilateral: pelo claramente llega debajo del cuello.
        (deep_presence >= 0.050 and deep_edge >= 0.012 and bilateral_deep >= 0.030)
        or
        # Continuidad media -> baja -> profunda.
        (
            mid_presence >= 0.070
            and below_presence >= 0.060
            and deep_presence >= 0.030
            and deep_edge >= 0.010
        )
        or
        below_presence >= 0.105
        or (strongest_low_presence >= 0.065 and strongest_low_edge >= 0.018)
        # CHECK HAIR 2F: caída bilateral clara alrededor de la mandíbula +
        # continuidad texturada en la zona inferior.
        or (
            mid_presence >= 0.078
            and min(mid_l, mid_r) >= 0.072
            and strongest_low_edge >= 0.032
        )
    ):
        hair_length = "long"
        length_conf = 0.86
    elif (
        mid_presence >= 0.068
        or below_presence >= 0.055
        or (deep_presence >= 0.022 and deep_edge >= 0.008)
    ):
        hair_length = "medium"
        length_conf = 0.78
    else:
        hair_length = "short"
        length_conf = 0.70

    hair_texture, texture_conf = _estimate_hair_texture_v4(
        img_bgr,
        face_box,
        ref_color,
    )

    result = {
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

    details = _estimate_hair_v2_details(
        img_bgr,
        face_box,
        ref_color,
        hair_length,
        hair_texture,
    )

    detail_conf = details.get("_confidence", {}).copy()
    result["_confidence"].update(detail_conf)

    details_without_conf = dict(details)
    details_without_conf.pop("_confidence", None)
    result.update(details_without_conf)

    # CHECK HAIR 3A: estructura fina de trenzas.
    braid_details = _estimate_braid_structure(
        img_bgr,
        face_box,
        ref_color,
        hair_length,
        details,
        deep,
    )
    braid_conf = braid_details.pop("_confidence", {})
    result["_confidence"].update(braid_conf)
    result.update(braid_details)

    # Garantías de esquema Hair V3.
    result.setdefault(
        "hair_style_family",
        result.get("hair_shape_family")
    )
    result.setdefault("braid_count", "none")
    result.setdefault("braid_style", "none")

    # Si detectamos trenzas con evidencia alta, la estructura manda sobre
    # la familia "long_layered" inferida por largo/textura.
    if result.get("braid_style") == "twin_braids":
        result["hair_tied"] = "braids"
        result["hair_shape_family"] = "braids"
        result["_confidence"]["hair_tied"] = max(
            result["_confidence"].get("hair_tied", 0.0),
            result["_confidence"].get("braid_style", 0.0),
        )
        result["_confidence"]["hair_shape_family"] = max(
            result["_confidence"].get("hair_shape_family", 0.0),
            result["_confidence"].get("hair_style_family", 0.0),
        )

    return result


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
        # Marcos finos/redondos: pueden no tener una banda inferior oscura,
        # pero sí borde bilateral + puente muy claro.
        or (bottom_edge >= 0.09 and outer_edge >= 0.12)
    )
    side_support = outer_edge >= 0.08 and inner_edge >= 0.06

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


def _sample_iris_eye(face_roi, center_x_frac):
    """
    Muestrea una pequeña corona alrededor del centro esperado del iris.
    Hace balance local usando la esclerótica para reducir dominante cálida
    de webcam/ambiente.
    """
    if face_roi is None or face_roi.size == 0:
        return None

    h, w = face_roi.shape[:2]
    cx = int(center_x_frac * w)
    cy = int(0.425 * h)

    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt(
        (xx - cx) ** 2
        + (yy - cy) ** 2
    )

    hsv = cv2.cvtColor(
        face_roi,
        cv2.COLOR_BGR2HSV,
    )

    radius = max(2.0, 0.045 * w)

    iris_mask = (
        (dist <= radius)
        & (dist >= max(1.0, 0.012*w))
        & (hsv[..., 2] >= 20)
        & (hsv[..., 2] <= 150)
    )

    iris_pixels = face_roi[iris_mask]
    if len(iris_pixels) < 12:
        return None

    # Quitamos extremos:
    # - los más oscuros suelen ser pupila/marco
    # - los más claros suelen ser reflejo/esclerótica
    iris_hsv = cv2.cvtColor(
        iris_pixels.reshape(-1, 1, 3),
        cv2.COLOR_BGR2HSV,
    ).reshape(-1, 3)

    order = np.argsort(iris_hsv[:, 2])
    lo = int(len(order) * 0.15)
    hi = max(lo + 6, int(len(order) * 0.68))
    selected = iris_pixels[order[lo:hi]]

    if len(selected) < 6:
        return None

    # Referencia local aproximadamente blanca alrededor del iris.
    sclera_mask = (
        (dist >= 0.050*w)
        & (dist <= 0.105*w)
        & (np.abs(yy - cy) <= 0.030*h)
        & (hsv[..., 2] >= 105)
        & (hsv[..., 1] <= 115)
    )

    sclera = face_roi[sclera_mask]

    corrected = selected.astype(np.float32)

    if len(sclera) >= 8:
        sclera_med = np.median(
            sclera.astype(np.float32),
            axis=0,
        )
        target = float(
            np.mean(sclera_med)
        )
        factors = (
            target
            / np.maximum(sclera_med, 1.0)
        )
        # Limitar corrección para no inventar color.
        factors = np.clip(
            factors,
            0.78,
            1.25,
        )
        corrected *= factors.reshape(1, 3)

    corrected = np.clip(
        corrected,
        0,
        255,
    )

    med_bgr = np.median(
        corrected,
        axis=0,
    )

    med_hsv = cv2.cvtColor(
        np.uint8([[med_bgr]]),
        cv2.COLOR_BGR2HSV,
    )[0, 0]

    return {
        "bgr": tuple(
            float(v) for v in med_bgr
        ),
        "h": float(med_hsv[0]),
        "s": float(med_hsv[1]),
        "v": float(med_hsv[2]),
        "pixels": int(len(selected)),
        "has_sclera_reference": bool(len(sclera) >= 8),
    }


def _classify_eye_sample(sample):
    if sample is None:
        return None, 0.0

    h = sample["h"]
    s = sample["s"]
    v = sample["v"]
    b, g, r = sample["bgr"]

    # Muy oscuro: solo separar near-black / dark-brown.
    if v < 52:
        if s < 24:
            return "near_black", 0.45
        return "dark_brown", 0.50

    # Iris casi neutro: gris. El launcher puede refinar gray_green/gray_blue.
    if s < 34:
        return "gray", 0.56

    # Con saturación baja-media, pequeñas diferencias B/G sirven para
    # orientar un gris hacia verde/azul.
    if s < 52:
        if g >= r - 2 and g >= b - 3:
            return "gray_green", 0.55
        if b >= g + 4:
            return "gray_blue", 0.55
        return "gray", 0.52

    # OpenCV H: 0..179.
    # Marrones/hazel suelen caer en el sector cálido.
    if h <= 18 or h >= 165:
        if v <= 82:
            return "dark_brown", 0.58
        if s <= 85:
            return "hazel", 0.56
        return "brown", 0.58

    if 19 <= h <= 34:
        return "hazel", 0.60

    if 35 <= h <= 88:
        return "green", 0.61

    if 89 <= h <= 132:
        return "blue", 0.61

    return "gray", 0.45


def _estimate_eye_color(face_roi, glasses=None):
    """
    CHECK FACE 4A.

    Estimación SEMÁNTICA del iris, pensada para alimentar la paleta del
    launcher. Si la evidencia no es suficiente devuelve None.

    Con anteojos la confianza se limita porque reflejos/marcos contaminan
    el área del iris.
    """
    if face_roi is None or face_roi.size == 0:
        return None, 0.0

    samples = [
        _sample_iris_eye(face_roi, 0.35),
        _sample_iris_eye(face_roi, 0.65),
    ]

    classified = [
        _classify_eye_sample(sample)
        for sample in samples
        if sample is not None
    ]

    classified = [
        (label, conf)
        for label, conf in classified
        if label is not None
    ]

    if not classified:
        print("[EYE 4A] sin muestra confiable")
        return None, 0.0

    labels = [x[0] for x in classified]

    # Si ambos ojos coinciden, buena evidencia.
    if len(labels) >= 2 and labels[0] == labels[1]:
        label = labels[0]
        confidence = min(
            0.72,
            sum(x[1] for x in classified) / len(classified) + 0.08,
        )
    else:
        # Resolver desacuerdos hacia familias más amplias.
        label_set = set(labels)

        if label_set <= {"gray", "gray_green", "gray_blue"}:
            label = "gray"
            confidence = 0.52
        elif label_set <= {"dark_brown", "brown", "hazel"}:
            label = "hazel" if "hazel" in label_set else "brown"
            confidence = 0.50
        elif len(classified) == 1:
            label, confidence = classified[0]
            confidence *= 0.82
        else:
            # Reflejo/ambigüedad: no inventar.
            print(
                "[EYE 4A] desacuerdo="
                + ",".join(labels)
                + " => unknown"
            )
            return None, 0.0

    if glasses is True:
        confidence = min(
            confidence,
            0.60,
        )

    print(
        "[EYE 4A] "
        f"samples={labels} "
        f"=> {label} "
        f"conf={confidence:.2f}"
    )

    return label, confidence


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

    jaw_left_dark = _dark_ratio(jaw_left, 88)
    jaw_right_dark = _dark_ratio(jaw_right, 88)
    chin_dark = _dark_ratio(chin, 88)

    jaw_scores = [jaw_left_dark, jaw_right_dark, chin_dark]

    # CHECK FACE 4A:
    # el ROI grande incluía labios/sombras y podía inventar bigote.
    # Pedimos señal bilateral y razonablemente simétrica por ENCIMA del labio.
    must_left = _crop(
        face_roi,
        0.34*w,
        0.53*h,
        0.49*w,
        0.62*h,
    )
    must_right = _crop(
        face_roi,
        0.51*w,
        0.53*h,
        0.66*w,
        0.62*h,
    )

    must_left_dark = _dark_ratio(must_left, 90)
    must_right_dark = _dark_ratio(must_right, 90)
    must_max = max(must_left_dark, must_right_dark)
    must_min = min(must_left_dark, must_right_dark)
    must_symmetry = (
        must_min / max(0.001, must_max)
    )

    moustache = bool(
        must_dark >= 0.22
        and must_min >= 0.10
        and must_symmetry >= 0.50
    )

    # V5: una sombra puntual, pelo largo entrando por un lateral o la propia
    # boca ya no alcanzan para declarar barba. Pedimos evidencia bilateral
    # o una zona central de mentón realmente densa.
    # CHECK HAIR 3A:
    # El mentón oscuro por sí solo NO alcanza para declarar barba.
    # En fotos con pelo largo/trenzas y sombras laterales generaba falsos
    # positivos. Exigimos soporte bilateral de mandíbula.
    beard = bool(
        (jaw_left_dark > 0.15 and jaw_right_dark > 0.15)
        or (
            chin_dark > 0.20
            and min(jaw_left_dark, jaw_right_dark) > 0.105
        )
    )

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

    # -------- eye color
    eye_color, eye_conf = _estimate_eye_color(
        face_roi,
        glasses=glasses,
    )
    traits["eye_color"] = eye_color
    confidence["eye_color"] = eye_conf

    # -------- facial hair
    facial = _estimate_facial_hair(face_roi)
    confidence.update(facial.pop("_confidence"))
    traits.update(facial)

    # V2: no inventamos lo que todavía no podemos medir bien.
    traits["freckles"] = None
    traits["age_group"] = None

    confidence["freckles"] = 0.0
    confidence["age_group"] = 0.0

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
