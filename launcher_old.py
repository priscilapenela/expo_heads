"""Expo Heads UNO - launcher portable + matching + recoloreado dinámico."""

from pathlib import Path
import os
import subprocess
import sqlite3
from datetime import datetime
import math
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

import pygame
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


from avatar_selector import AvatarSelector
from face_analyzer import analyze_face


BASE_DIR = Path(__file__).resolve().parent
AVATARS_DIR = BASE_DIR / "data" / "avatars"
CAPTURES_DIR = BASE_DIR / "data" / "captures"
AVATAR_CATALOG_FILE = BASE_DIR / "avatars_catalog.json"
GAME_EXE_1V1 = "head_football_patched_v5_1v1.exe"
GAME_EXE_TOP1 = "head_football_patched_v5_top1_ai.exe"
INFO_DIR = BASE_DIR / "data" / "info_files"
CURRENT_SETTINGS_FILE = INFO_DIR / "tren_igra_postavke.txt"
RESULT_INFO_FILE = INFO_DIR / "cijeli_game_łnfo.txt"

# Base única y canónica de Expo Heads. ranking.db queda fuera de uso porque
# pertenecía al launcher provisional y guardaba resultados 0-0 incorrectos.
DB_FILE = BASE_DIR / "data" / "expo_heads.db"
AVATAR_DIR = BASE_DIR / "data" / "avatars"

SCREEN_W, SCREEN_H = 1200, 700
FPS = 60
MAX_NAME_LENGTH = 15
TOP1_NAME = "TOP #1"

# Slots de runtime ya validados por la versión estable.
# La cámara sobrescribe 21/22 solamente durante el uso normal del launcher,
# evitando tocar los sprites base igrac1/igrac2.
DEFAULT_PLAYER_AVATAR = "data/images/igrac1.png"
RUNTIME_PLAYER_AVATAR_P1 = "data/images/igrac21.png"
RUNTIME_PLAYER_AVATAR_P2 = "data/images/igrac22.png"

# Alias conservados por compatibilidad con versiones previas.
MANUAL_1V1_AVATAR_P1 = RUNTIME_PLAYER_AVATAR_P1
MANUAL_1V1_AVATAR_P2 = RUNTIME_PLAYER_AVATAR_P2

# El motor precarga igrac1.png ... igrac23.png. El slot 23 se reserva
# temporalmente para el avatar UUID del TOP #1 y siempre se restaura.
TOP1_RUNTIME_AVATAR = "data/images/igrac23.png"
TOP1_RUNTIME_BACKUP = "igrac23.expo_original.png"
TOP1_RUNTIME_STAGE = "igrac23.expo_stage.png"

# Webcam comprobada en Windows con camera_diagnostic.py.
CAMERA_INDEX = 0
CAMERA_INDICES = (0, 1, 2, 3)
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Guía facial estilo reconocimiento bancario.
FACE_GUIDE_W = 250
FACE_GUIDE_H = 340
FACE_MIN_W = 60
FACE_MAX_W = 300
FACE_CENTER_TOL_X = 95
FACE_CENTER_TOL_Y = 100

# === PALETA RETRO ARCADE (A juego con los botones del juego) ===
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (15, 15, 25)

# Colores de paneles y marquesinas
PANEL_BG = (14, 24, 40)
PANEL_BORDER_LIGHT = (40, 105, 175)
PANEL_BORDER_DARK = (6, 12, 22)

# Colores de botones y textos principales
BTN_ORANGE = (215, 75, 20)
BTN_ORANGE_LIGHT = (245, 110, 45)
BTN_ORANGE_DARK = (130, 35, 10)
BTN_ORANGE_HOVER = (245, 110, 45)

BTN_YELLOW = (235, 185, 25)
BTN_YELLOW_LIGHT = (255, 220, 70)
BTN_YELLOW_DARK = (150, 110, 10)
BTN_YELLOW_HOVER = (255, 220, 70)

BTN_GRAY_BG = (32, 32, 44)
BTN_GRAY_HOVER = (48, 48, 62)

GRAY = (160, 160, 170)
DARK_GRAY = (40, 40, 40)

# Luces y Podio
NEON_CYAN = (0, 240, 255)
NEON_PINK = (255, 0, 128)
ARCADE_GREEN = (50, 255, 60)
ARCADE_GREEN_DIM = (15, 110, 25)
GOLD = (255, 205, 20)
SILVER = (210, 220, 235)
BRONZE = (215, 125, 50)
ACCENT = (0, 170, 255)
ACCENT_2 = (220, 40, 80)


# ==========================================
# AVATARES RECOLOREABLES - PALETA OFICIAL
# ==========================================
#
# A partir de esta versión, los templates oficiales de Expo Heads deben
# utilizar estos colores marcador. El launcher reemplaza esos colores por
# los tonos detectados en la fotografía del jugador.
#
# El negro, el blanco y los píxeles transparentes NO se recolorean.
#
# IMPORTANTE:
# - Los PNG oficiales deben ser RGBA.
# - El tamaño oficial de biblioteca es 70x70.
# - El launcher igualmente fuerza la salida final a 70x70.
#
# Se mantiene compatibilidad con los dos templates POC anteriores mediante
# un fallback HSV. Los nuevos lotes deben usar esta paleta exacta.

AVATAR_OUTPUT_SIZE = 70
AVATAR_MARKER_TOLERANCE = 10

AVATAR_MARKERS = {
    "skin_base":    (255,   0, 255),  # magenta
    "skin_shadow":  (170,   0, 170),
    "hair_base":    (  0, 255,   0),  # verde
    "hair_shadow":  (  0, 130,   0),
    "beard_base":   (  0,  80, 255),  # azul
    "beard_shadow": (  0,  40, 150),
    "iris":         (  0, 255, 255),  # cyan
    "glasses":      (255, 255,   0),  # amarillo
}


def _crop_array(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1 = max(0, min(w, int(round(x1))))
    y1 = max(0, min(h, int(round(y1))))
    x2 = max(0, min(w, int(round(x2))))
    y2 = max(0, min(h, int(round(y2))))
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]


def _median_color(pixels, fallback):
    if pixels is None or len(pixels) == 0:
        return np.array(fallback, dtype=np.float32)
    return np.median(pixels.astype(np.float32), axis=0)


def _bgr_to_rgb(color):
    return (
        int(color[2]),
        int(color[1]),
        int(color[0]),
    )


def _rgb_to_bgr(color):
    return (
        int(color[2]),
        int(color[1]),
        int(color[0]),
    )


def _ensure_rgb(color):
    return tuple(
        int(max(0, min(255, round(float(channel)))))
        for channel in color
    )


def _darken_rgb(color, amount=0.20):
    arr = np.array(color, dtype=np.float32)
    return tuple(
        np.clip(arr * (1.0 - amount), 0, 255)
        .astype(np.uint8)
        .tolist()
    )


def _skin_mask_ycrcb(bgr_img):
    """Máscara tolerante de piel usada solamente para estimar color."""
    ycrcb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2YCrCb)
    lower = np.array([0, 135, 85], dtype=np.uint8)
    upper = np.array([255, 180, 135], dtype=np.uint8)
    return cv2.inRange(ycrcb, lower, upper) > 0


def _near_marker_mask(rgb, marker, tolerance=AVATAR_MARKER_TOLERANCE):
    marker_arr = np.array(marker, dtype=np.int16)
    delta = np.abs(rgb.astype(np.int16) - marker_arr)
    return np.max(delta, axis=2) <= int(tolerance)


def _legacy_hsv_mask(hsv, alpha, h_low, h_high, s_min=60, v_min=20):
    if h_low <= h_high:
        hue_mask = (
            (hsv[..., 0] >= h_low)
            & (hsv[..., 0] <= h_high)
        )
    else:
        hue_mask = (
            (hsv[..., 0] >= h_low)
            | (hsv[..., 0] <= h_high)
        )

    return (
        (alpha > 0)
        & hue_mask
        & (hsv[..., 1] >= s_min)
        & (hsv[..., 2] >= v_min)
    )


def _recolor_mask_with_shading(rgb, mask, target_rgb):
    """
    Fallback para los templates POC viejos.

    Conserva diferencias de luminosidad internas del color marcador para
    mantener sombras y luces aunque el template no use la paleta exacta.
    """
    if not np.any(mask):
        return rgb

    region = rgb[mask].astype(np.float32)
    brightness = region.mean(axis=1)

    bmin = float(brightness.min())
    bmax = float(brightness.max())

    if bmax - bmin < 1e-6:
        normalized = np.full_like(brightness, 0.5)
    else:
        normalized = (brightness - bmin) / (bmax - bmin)

    factor = 0.72 + (0.48 * normalized)
    target = np.array(target_rgb, dtype=np.float32)
    rgb[mask] = np.clip(
        target * factor[:, None],
        0,
        255,
    ).astype(np.uint8)

    return rgb


def recolor_avatar_template(template_path, output_path, colors, avatar_traits=None):
    """
    Recoloreado V2 robusto para los templates Expo Heads.

    Problema corregido respecto de V1:
    los PNG generados no contienen siempre el RGB marcador EXACTO. Por ejemplo,
    la piel puede ser (254, 32, 253) en vez de (255, 0, 255). V1 detectaba
    unos pocos píxeles exactos, declaraba "semantic" y dejaba casi todo verde /
    magenta sin modificar.

    V2 combina:
      - marcadores RGB exactos/tolerantes;
      - familias HSV amplias para magenta, verde, azul, cyan y amarillo;
      - sombreado relativo del template;
      - metadata estructural para no recolorear accesorios amarillos/azules
        cuando el avatar no tiene anteojos o barba.

    La salida SIEMPRE es RGBA 70x70.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)
    avatar_traits = avatar_traits or {}

    img = cv2.imread(str(template_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(f"No se pudo abrir el template: {template_path}")

    if img.ndim != 3 or img.shape[2] not in (3, 4):
        raise RuntimeError(f"Template inválido: {template_path}")

    if img.shape[2] == 4:
        rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
    else:
        rgb_only = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        alpha = np.full(rgb_only.shape[:2], 255, dtype=np.uint8)
        rgba = np.dstack([rgb_only, alpha])

    rgb = rgba[..., :3].copy()
    alpha = rgba[..., 3].copy()
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    visible = alpha > 0
    near_black = visible & (rgb[..., 0] < 22) & (rgb[..., 1] < 22) & (rgb[..., 2] < 22)
    near_white = visible & (rgb[..., 0] > 225) & (rgb[..., 1] > 225) & (rgb[..., 2] > 225)

    # Marcadores exactos/tolerantes, si existen.
    exact = {
        name: (_near_marker_mask(rgb, marker, tolerance=18) & visible)
        for name, marker in AVATAR_MARKERS.items()
    }

    # Familias cromáticas reales presentes en los PNG generados.
    # OpenCV usa H 0..179.
    skin_hsv = (
        _legacy_hsv_mask(hsv, alpha, 140, 179, s_min=65, v_min=30)
        | _legacy_hsv_mask(hsv, alpha, 0, 4, s_min=80, v_min=40)
    )
    hair_hsv = _legacy_hsv_mask(hsv, alpha, 35, 92, s_min=55, v_min=20)
    beard_hsv = _legacy_hsv_mask(hsv, alpha, 95, 138, s_min=55, v_min=20)
    iris_hsv = _legacy_hsv_mask(hsv, alpha, 78, 104, s_min=45, v_min=35)
    glasses_hsv = _legacy_hsv_mask(hsv, alpha, 17, 38, s_min=65, v_min=45)

    skin_mask = skin_hsv | exact["skin_base"] | exact["skin_shadow"]
    hair_mask = hair_hsv | exact["hair_base"] | exact["hair_shadow"]
    beard_mask = beard_hsv | exact["beard_base"] | exact["beard_shadow"]
    iris_mask = iris_hsv | exact["iris"]
    glasses_mask = glasses_hsv | exact["glasses"]

    # Nunca tocar contornos negros ni blanco del ojo.
    for mask in (skin_mask, hair_mask, beard_mask, iris_mask, glasses_mask):
        mask[near_black] = False
        mask[near_white] = False

    # No confundir aros/accesorios amarillos con anteojos.
    if not bool(avatar_traits.get("glasses", False)):
        glasses_mask[:] = False

    # No confundir detalles azules con barba si el JSON dice que no tiene.
    has_facial_hair = bool(avatar_traits.get("beard", False) or avatar_traits.get("moustache", False))
    if not has_facial_hair:
        beard_mask[:] = False

    # Si es calvo, cualquier verde aislado es accesorio/artefacto, no cabello.
    if bool(avatar_traits.get("bald", False)):
        hair_mask[:] = False

    mask_counts = {
        "skin": int(np.count_nonzero(skin_mask)),
        "hair": int(np.count_nonzero(hair_mask)),
        "beard": int(np.count_nonzero(beard_mask)),
        "iris": int(np.count_nonzero(iris_mask)),
        "glasses": int(np.count_nonzero(glasses_mask)),
    }

    # Recoloreamos preservando las luces/sombras originales de cada región.
    rgb = _recolor_mask_with_shading(rgb, skin_mask, colors["skin_rgb"])
    rgb = _recolor_mask_with_shading(rgb, hair_mask, colors["hair_rgb"])
    if has_facial_hair:
        rgb = _recolor_mask_with_shading(rgb, beard_mask, colors["beard_rgb"])
    rgb = _recolor_mask_with_shading(rgb, iris_mask, colors["eye_rgb"])
    if bool(avatar_traits.get("glasses", False)):
        rgb = _recolor_mask_with_shading(rgb, glasses_mask, colors["glasses_rgb"])

    changed_semantic_pixels = sum(mask_counts.values())
    if changed_semantic_pixels < 12:
        mode = "passthrough"
    else:
        mode = "semantic_hsv"

    print(
        "[RECOLOR MASKS] "
        + " ".join(f"{key}={value}" for key, value in mask_counts.items())
    )
    print(
        f"[RECOLOR COLORS] skin={colors['skin_rgb']} hair={colors['hair_rgb']} "
        f"eyes={colors['eye_rgb']} glasses={colors['glasses_rgb']} beard={colors['beard_rgb']}"
    )

    out_rgba = np.dstack([rgb, alpha])

    if out_rgba.shape[1] != AVATAR_OUTPUT_SIZE or out_rgba.shape[0] != AVATAR_OUTPUT_SIZE:
        out_rgba = cv2.resize(
            out_rgba,
            (AVATAR_OUTPUT_SIZE, AVATAR_OUTPUT_SIZE),
            interpolation=cv2.INTER_NEAREST,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(
        str(output_path),
        cv2.cvtColor(out_rgba, cv2.COLOR_RGBA2BGRA),
    )
    if not ok:
        raise RuntimeError(f"No se pudo guardar el avatar recoloreado: {output_path}")

    return output_path, mode


# ==========================================
# BASE DE DATOS Y LÓGICA DE ARCHIVOS
# ==========================================

def _open_db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_columns(conn, table_name):
    return {row[1] for row in conn.execute(f'PRAGMA table_info("{table_name}")')}


def _ensure_column(conn, table_name, column_name, definition):
    if column_name not in _table_columns(conn, table_name):
        conn.execute(
            f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'
        )


def _find_player_by_name(conn, name):
    wanted = name.strip().casefold()
    for player_id, player_name, current_avatar in conn.execute(
        "SELECT id, nombre, avatar_actual_id FROM jugadores ORDER BY fecha_creacion, id"
    ):
        if player_name.strip().casefold() == wanted:
            return player_id, player_name, current_avatar
    return None


def _get_or_create_player(conn, name, legacy=False):
    name = name.strip() or "Jugador"
    current = _find_player_by_name(conn, name)
    if current is not None:
        return current[0]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    if legacy:
        player_id = str(uuid5(NAMESPACE_URL, f"expo-heads:{name.casefold()}"))
    else:
        player_id = str(uuid4())
    conn.execute(
        '''INSERT INTO jugadores
           (id, nombre, avatar_actual_id, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, NULL, ?, ?)''',
        (player_id, name, now, now),
    )
    return player_id


def _backfill_player_ids(conn):
    """Asigna UUID estables a los resultados creados antes del CHECK 4."""
    names = []
    for table_name in ("ranking", "partidas"):
        names.extend(
            row[0]
            for row in conn.execute(
                f'SELECT jugador FROM "{table_name}" WHERE jugador IS NOT NULL'
            )
            if row[0].strip()
        )

    for name in names:
        player_id = _get_or_create_player(conn, name, legacy=True)
        for table_name in ("ranking", "partidas"):
            rows = conn.execute(
                f'SELECT id, jugador FROM "{table_name}" WHERE jugador_id IS NULL'
            ).fetchall()
            for row_id, row_name in rows:
                if row_name.strip().casefold() == name.strip().casefold():
                    conn.execute(
                        f'UPDATE "{table_name}" SET jugador_id=? WHERE id=?',
                        (player_id, row_id),
                    )


def init_db():
    """Crea/migra la base única sin perder partidas ni récords anteriores."""
    with _open_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS partidas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            jugador TEXT NOT NULL,
                            goles INTEGER NOT NULL,
                            goles_recibidos INTEGER NOT NULL,
                            modo TEXT NOT NULL,
                            imagen TEXT,
                            fecha TEXT NOT NULL
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS ranking (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            jugador TEXT NOT NULL UNIQUE,
                            goles_max INTEGER NOT NULL,
                            goles_recibidos INTEGER NOT NULL,
                            imagen TEXT,
                            fecha_record TEXT NOT NULL
                        )''')

        conn.execute('''CREATE TABLE IF NOT EXISTS jugadores (
                            id TEXT PRIMARY KEY,
                            nombre TEXT NOT NULL,
                            avatar_actual_id TEXT,
                            fecha_creacion TEXT NOT NULL,
                            fecha_actualizacion TEXT NOT NULL
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS avatares (
                            id TEXT PRIMARY KEY,
                            jugador_id TEXT NOT NULL,
                            archivo TEXT NOT NULL UNIQUE,
                            fecha_creacion TEXT NOT NULL,
                            activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
                            FOREIGN KEY (jugador_id) REFERENCES jugadores(id)
                        )''')

        _ensure_column(conn, "partidas", "jugador_id", "TEXT")
        _ensure_column(conn, "partidas", "avatar_id", "TEXT")
        _ensure_column(conn, "ranking", "jugador_id", "TEXT")
        _ensure_column(conn, "ranking", "avatar_id", "TEXT")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_partidas_jugador_id ON partidas(jugador_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_partidas_avatar_id ON partidas(avatar_id)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_ranking_jugador_id "
            "ON ranking(jugador_id) WHERE jugador_id IS NOT NULL"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_avatares_jugador_id ON avatares(jugador_id)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_avatares_activo_por_jugador "
            "ON avatares(jugador_id) WHERE activo=1"
        )
        _backfill_player_ids(conn)



def reset_turn_data():
    """
    Reinicia solamente los datos competitivos del turno actual.

    Borra:
    - partidas
    - ranking
    - avatares UUID archivados de jugadores
    - jugadores

    Conserva:
    - avatars_catalog.json
    - templates avatar_XXXX.png de la biblioteca
    - ejecutables
    - configuración base del juego
    - assets del launcher

    Los PNG archivados de jugadores usan UUID como nombre. Se eliminan
    solamente esos archivos, nunca los templates avatar_XXXX.png.
    """
    archived_files = []

    with _open_db() as conn:
        # Guardamos las rutas antes de borrar las filas para poder limpiar
        # solamente los avatares archivados de jugadores.
        archived_files = [
            row[0]
            for row in conn.execute(
                "SELECT archivo FROM avatares WHERE archivo IS NOT NULL"
            ).fetchall()
            if row[0]
        ]

        # Orden importante por las relaciones entre tablas.
        conn.execute("DELETE FROM partidas")
        conn.execute("DELETE FROM ranking")
        conn.execute("DELETE FROM avatares")
        conn.execute("DELETE FROM jugadores")

        # Reinicia los IDs autoincrementales de las tablas que los usan.
        try:
            conn.execute(
                "DELETE FROM sqlite_sequence "
                "WHERE name IN ('partidas', 'ranking')"
            )
        except sqlite3.OperationalError:
            # sqlite_sequence puede no existir todavía en una DB recién creada.
            pass

    deleted_avatar_files = 0

    # Primera pasada: elimina exactamente los archivos que estaban registrados.
    for avatar_file in archived_files:
        candidate = resolve_ranking_avatar_path(avatar_file)
        if candidate is None:
            continue

        # Seguridad adicional: solamente UUIDs dentro de data/avatars.
        try:
            UUID(candidate.stem)
        except (ValueError, AttributeError):
            continue

        try:
            candidate.unlink()
            deleted_avatar_files += 1
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(f"[RESET TURNO] No se pudo borrar {candidate}: {exc}")

    # Segunda pasada: limpia UUID huérfanos de resets/crashes anteriores.
    if AVATAR_DIR.is_dir():
        for candidate in AVATAR_DIR.glob("*.png"):
            try:
                UUID(candidate.stem)
            except (ValueError, AttributeError):
                continue

            try:
                candidate.unlink()
                deleted_avatar_files += 1
            except FileNotFoundError:
                pass
            except OSError as exc:
                print(f"[RESET TURNO] No se pudo borrar {candidate}: {exc}")

    print(
        "[RESET TURNO] Base reiniciada correctamente. "
        f"Avatares archivados eliminados: {deleted_avatar_files}"
    )

    return deleted_avatar_files


def register_player_avatar(name, avatar_id, avatar_file):
    """Registra la identidad del jugador y enlaza su PNG UUID actual."""
    name = validate_name(name)
    try:
        UUID(str(avatar_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("El avatar_id no es un UUID válido.") from exc

    expected_file = f"data/avatars/{avatar_id}.png"
    if avatar_file != expected_file:
        raise ValueError("El archivo del avatar no coincide con su UUID.")
    absolute_file = BASE_DIR.joinpath(*avatar_file.split("/"))
    if not absolute_file.is_file():
        raise FileNotFoundError(f"No se encontró el avatar archivado {avatar_file}.")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    with _open_db() as conn:
        player_id = _get_or_create_player(conn, name)
        existing_avatar = conn.execute(
            "SELECT jugador_id, archivo FROM avatares WHERE id=?",
            (avatar_id,),
        ).fetchone()
        if existing_avatar is not None and existing_avatar != (player_id, avatar_file):
            raise ValueError("El UUID del avatar ya está vinculado a otro jugador.")

        conn.execute("UPDATE avatares SET activo=0 WHERE jugador_id=?", (player_id,))
        if existing_avatar is None:
            conn.execute(
                '''INSERT INTO avatares
                   (id, jugador_id, archivo, fecha_creacion, activo)
                   VALUES (?, ?, ?, ?, 1)''',
                (avatar_id, player_id, avatar_file, now),
            )
        else:
            conn.execute("UPDATE avatares SET activo=1 WHERE id=?", (avatar_id,))

        conn.execute(
            '''UPDATE jugadores
               SET nombre=?, avatar_actual_id=?, fecha_actualizacion=?
               WHERE id=?''',
            (name, avatar_id, now, player_id),
        )
        return player_id


def save_score(player_id, name, mode, gf, gc, avatar_id=None, avatar_file=None):
    """Guarda una partida vinculada y actualiza la mejor marca personal."""
    name = validate_name(name)
    gf = int(gf)
    gc = int(gc)
    if gf < 0 or gc < 0:
        raise ValueError("Los goles no pueden ser negativos.")

    match_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    with _open_db() as conn:
        player = conn.execute(
            "SELECT id FROM jugadores WHERE id=?",
            (player_id,),
        ).fetchone()
        if player is None:
            raise ValueError("El jugador no está registrado en la base.")
        if avatar_id is not None:
            avatar = conn.execute(
                "SELECT id FROM avatares WHERE id=? AND jugador_id=?",
                (avatar_id, player_id),
            ).fetchone()
            if avatar is None:
                raise ValueError("El avatar no pertenece al jugador indicado.")

        conn.execute(
            '''INSERT INTO partidas
               (jugador, goles, goles_recibidos, modo, imagen, fecha, jugador_id, avatar_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, gf, gc, mode, avatar_file, match_date, player_id, avatar_id),
        )

        current = conn.execute(
            '''SELECT id, goles_max, goles_recibidos, avatar_id
               FROM ranking
               WHERE jugador_id=?
               ORDER BY id ASC
               LIMIT 1''',
            (player_id,),
        ).fetchone()

        if current is None:
            conn.execute(
                '''INSERT INTO ranking
                   (jugador, goles_max, goles_recibidos, imagen, fecha_record,
                    jugador_id, avatar_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (name, gf, gc, avatar_file, match_date, player_id, avatar_id),
            )
        else:
            row_id, previous_gf, previous_gc, record_avatar_id = current
            is_better = gf > previous_gf or (gf == previous_gf and gc < previous_gc)
            if is_better:
                conn.execute(
                    '''UPDATE ranking
                       SET jugador=?, goles_max=?, goles_recibidos=?, imagen=?, fecha_record=?,
                           jugador_id=?, avatar_id=?
                       WHERE id=?''',
                    (
                        name, gf, gc, avatar_file, match_date,
                        player_id, avatar_id, row_id,
                    ),
                )
            elif record_avatar_id is None and avatar_id is not None:
                # Completa la relación de récords heredados sin alterar su marca ni fecha.
                conn.execute(
                    '''UPDATE ranking
                       SET imagen=?, avatar_id=?
                       WHERE id=?''',
                    (avatar_file, avatar_id, row_id),
                )

def get_top_ranking(limit=10):
    """Devuelve el ranking: goles DESC, recibidos ASC y fecha ASC."""
    with _open_db() as conn:
        return conn.execute(
            '''SELECT r.jugador, r.goles_max, r.goles_recibidos, r.fecha_record,
                      COALESCE(a.archivo, r.imagen)
               FROM ranking AS r
               LEFT JOIN avatares AS a ON a.id = r.avatar_id
               ORDER BY r.goles_max DESC, r.goles_recibidos ASC, r.fecha_record ASC
               LIMIT ?''',
            (int(limit),),
        ).fetchall()


def get_top1_identity():
    with _open_db() as conn:
        row = conn.execute(
            '''SELECT r.jugador, r.jugador_id,
                      COALESCE(r.avatar_id, j.avatar_actual_id),
                      COALESCE(record_avatar.archivo, current_avatar.archivo, r.imagen)
               FROM ranking AS r
               LEFT JOIN jugadores AS j ON j.id = r.jugador_id
               LEFT JOIN avatares AS record_avatar ON record_avatar.id = r.avatar_id
               LEFT JOIN avatares AS current_avatar ON current_avatar.id = j.avatar_actual_id
               ORDER BY r.goles_max DESC, r.goles_recibidos ASC, r.fecha_record ASC
               LIMIT 1'''
        ).fetchone()
    if row is None:
        return None
    return {
        "name": row[0],
        "player_id": row[1],
        "avatar_id": row[2],
        "avatar_file": row[3],
    }


def get_top1_name():
    top = get_top1_identity()
    return top["name"] if top else TOP1_NAME


def format_db_date(value):
    try:
        return datetime.fromisoformat(str(value)).strftime("%d/%m %H:%M")
    except (TypeError, ValueError):
        return str(value)[:16]


def _result_info_paths():
    """
    Lista todas las fuentes válidas de resultado del juego.

    El EXE actual deja data/info_files/cijeli_game_łnfo.txt vacío al finalizar,
    pero sí escribe el marcador real en data/replays/recent/*nfo.txt.
    Por eso se monitorean ambas ubicaciones.
    """
    paths = [RESULT_INFO_FILE]

    if INFO_DIR.is_dir():
        for candidate in INFO_DIR.glob("cijeli_game_*nfo.txt"):
            if candidate.is_file() and candidate not in paths:
                paths.append(candidate)

    replay_dir = BASE_DIR / "data" / "replays" / "recent"
    if replay_dir.is_dir():
        for candidate in replay_dir.glob("*nfo.txt"):
            if candidate.is_file() and candidate not in paths:
                paths.append(candidate)

    return paths
def snapshot_match_results():
    """Toma una huella de sólo lectura para no aceptar un resultado anterior."""
    snapshot = {}
    for path in _result_info_paths():
        try:
            stat = path.stat()
            snapshot[str(path.resolve())] = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            pass
    return snapshot


def _read_result_file(path):
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    for line in reversed(raw.splitlines() or [raw]):
        parts = [part.strip() for part in line.strip().split("|")]
        if len(parts) < 4:
            continue
        try:
            g1 = int(parts[2])
            g2 = int(parts[3])
        except ValueError:
            continue
        if g1 < 0 or g2 < 0:
            continue
        return {"p1": parts[0], "p2": parts[1], "g1": g1, "g2": g2}
    return None


def parse_match_results(previous_snapshot=None, expected_players=None):
    """Lee el marcador real del *_łnfo actualizado por el último partido."""
    candidates = []
    for path in _result_info_paths():
        try:
            stat = path.stat()
        except OSError:
            continue

        signature = (stat.st_mtime_ns, stat.st_size)
        key = str(path.resolve())
        if previous_snapshot is not None and previous_snapshot.get(key) == signature:
            continue
        candidates.append((stat.st_mtime_ns, path))

    for _mtime, path in sorted(candidates, reverse=True):
        result = _read_result_file(path)
        if result is None:
            continue
        if expected_players:
            expected_p1, expected_p2 = expected_players
            if (result["p1"].casefold() != expected_p1.strip().casefold()
                    or result["p2"].casefold() != expected_p2.strip().casefold()):
                continue
        return result
    return None

def asset_path(filename):
    folder = BASE_DIR / "data" / "images"
    direct = folder / filename
    if direct.exists():
        return direct
    if folder.exists():
        wanted = filename.casefold()
        for candidate in folder.iterdir():
            if candidate.is_file() and candidate.name.casefold() == wanted:
                return candidate
    return direct


def resolve_ranking_avatar_path(avatar_file):
    """Resuelve de forma segura un avatar guardado para mostrarlo en el ranking."""
    if not isinstance(avatar_file, str) or not avatar_file.strip():
        return None

    relative = Path(avatar_file.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        return None
    if len(relative.parts) < 3 or relative.parts[0:2] not in (
            ("data", "avatars"), ("data", "images")):
        return None
    if relative.suffix.casefold() != ".png":
        return None

    candidate = (BASE_DIR / relative).resolve()
    allowed_roots = (
        (BASE_DIR / "data" / "avatars").resolve(),
        (BASE_DIR / "data" / "images").resolve(),
    )
    try:
        if not any(candidate.is_relative_to(root) for root in allowed_roots):
            return None
    except AttributeError:
        # Compatibilidad con Python 3.8.
        if not any(root == candidate or root in candidate.parents for root in allowed_roots):
            return None

    return candidate if candidate.is_file() else None

LOGO_FILE = asset_path("naslov2.png")
BG_FILE = asset_path("pozadina.png")
BTN_TOP1_FILE = asset_path("bot1vstop.png")
BTN_1V1_FILE = asset_path("bot1vs1.png")

def validate_name(name):
    name = name.strip()
    if not name:
        raise ValueError("El nombre no puede estar vacío.")
    if any(char in name for char in "|\r\n"):
        raise ValueError("El nombre no puede contener | ni saltos de línea.")
    return name


def validate_avatar_path(image_path):
    """Valida una ruta compatible con el diccionario de sprites del motor."""
    if not isinstance(image_path, str) or not image_path:
        raise ValueError("La ruta del avatar no puede estar vacía.")
    if any(char in image_path for char in "|\r\n"):
        raise ValueError("La ruta del avatar contiene caracteres inválidos.")
    if not image_path.startswith("data/images/") or ".." in Path(image_path).parts:
        raise ValueError("El avatar debe estar dentro de data/images.")

    absolute_path = BASE_DIR.joinpath(*image_path.split("/"))
    if not absolute_path.is_file():
        raise FileNotFoundError(f"No se encontró el avatar {image_path}.")
    return image_path


def init_avatar_storage():
    """Crea únicamente la carpeta permanente de avatares si no existe."""
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)


def archive_avatar_png(image_path):
    """Copia un cabezón a data/avatars con UUID y sin sobrescribir archivos."""
    image_path = validate_avatar_path(image_path)
    source = BASE_DIR.joinpath(*image_path.split("/"))
    payload = source.read_bytes()
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"El avatar {image_path} no es un PNG válido.")

    init_avatar_storage()
    for _attempt in range(10):
        avatar_id = str(uuid4())
        destination = AVATAR_DIR / f"{avatar_id}.png"
        try:
            with destination.open("xb") as output:
                output.write(payload)
        except FileExistsError:
            continue

        relative_path = f"data/avatars/{avatar_id}.png"
        return avatar_id, relative_path

    raise OSError("No se pudo reservar un UUID único para el avatar.")


def _line_ending(line):
    if line.endswith(b"\r\n"):
        return b"\r\n"
    if line.endswith(b"\n"):
        return b"\n"
    if line.endswith(b"\r"):
        return b"\r"
    return b""


def write_match_players(
    player_1,
    player_2,
    player_1_image,
    player_2_image,
    settings_path=CURRENT_SETTINGS_FILE,
):
    """Escribe nombres y avatares juntos, conservando el resto del archivo."""
    player_1 = validate_name(player_1)
    player_2 = validate_name(player_2)
    player_1_image = validate_avatar_path(player_1_image)
    player_2_image = validate_avatar_path(player_2_image)
    path = Path(settings_path)

    if not path.is_file():
        raise FileNotFoundError(f"No se encontró {path}")

    original = path.read_bytes()
    lines = original.splitlines(keepends=True)
    if len(lines) < 5:
        raise ValueError("El archivo de configuración no tiene las cinco líneas esperadas.")

    lines[3] = (
        f"{player_1}|{player_2}".encode("utf-8")
        + _line_ending(lines[3])
    )
    lines[4] = (
        f"{player_1_image}|{player_2_image}".encode("utf-8")
        + _line_ending(lines[4])
    )
    updated = b"".join(lines)

    temp_path = path.with_name(path.name + ".expo_tmp")
    try:
        temp_path.write_bytes(updated)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_player_names(player_1, player_2, settings_path=CURRENT_SETTINGS_FILE):
    """Compatibilidad: actualiza nombres y conserva los avatares configurados."""
    path = Path(settings_path)
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró {path}")
    lines = path.read_bytes().splitlines()
    if len(lines) < 5:
        raise ValueError("El archivo de configuración no tiene las cinco líneas esperadas.")
    images = lines[4].decode("utf-8", errors="strict").split("|")
    if len(images) < 2:
        raise ValueError("La línea de avatares no tiene dos rutas.")
    write_match_players(player_1, player_2, images[0], images[1], path)


def _runtime_avatar_paths():
    image_dir = BASE_DIR / "data" / "images"
    return (
        image_dir / Path(TOP1_RUNTIME_AVATAR).name,
        image_dir / TOP1_RUNTIME_BACKUP,
        image_dir / TOP1_RUNTIME_STAGE,
    )


def recover_top1_runtime_avatar():
    """Restaura el slot si Windows o el launcher se cerraron durante una partida."""
    slot, backup, stage = _runtime_avatar_paths()
    if backup.is_file():
        os.replace(backup, slot)
    if stage.exists():
        stage.unlink()


def prepare_top1_runtime_avatar(avatar_file):
    """Inyecta una copia temporal del PNG UUID en un slot que el motor conoce."""
    if not isinstance(avatar_file, str) or not avatar_file.startswith("data/avatars/"):
        raise ValueError("El TOP #1 no tiene una ruta de avatar válida.")
    if ".." in Path(avatar_file).parts:
        raise ValueError("La ruta del avatar TOP #1 no es segura.")

    source = BASE_DIR.joinpath(*avatar_file.split("/"))
    avatar_root = AVATAR_DIR.resolve()
    try:
        source.resolve().relative_to(avatar_root)
    except ValueError as exc:
        raise ValueError("El avatar TOP #1 está fuera de data/avatars.") from exc
    if not source.is_file():
        raise FileNotFoundError(f"No se encontró el avatar del TOP #1: {avatar_file}")

    payload = source.read_bytes()
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("El archivo del TOP #1 no es un PNG válido.")

    recover_top1_runtime_avatar()
    slot, backup, stage = _runtime_avatar_paths()
    if not slot.is_file():
        raise FileNotFoundError(f"No se encontró el slot temporal {TOP1_RUNTIME_AVATAR}.")

    stage.write_bytes(payload)
    os.replace(slot, backup)
    try:
        os.replace(stage, slot)
    except Exception:
        os.replace(backup, slot)
        raise
    return True


def restore_top1_runtime_avatar():
    slot, backup, stage = _runtime_avatar_paths()
    if backup.is_file():
        os.replace(backup, slot)
    if stage.exists():
        stage.unlink()


def launch_game(exe_name, runtime_avatar_file=None):
    exe_path = BASE_DIR / exe_name
    if not exe_path.is_file():
        raise FileNotFoundError(f"No se encontró {exe_name}.")

    img_dir = BASE_DIR / "data" / "images"
    bg_launcher = img_dir / "pozadina.png"
    bg_game = img_dir / "pozadina2.png"
    bg_tmp = img_dir / "pozadina_tmp.png"

    swapped = False
    avatar_swapped = False
    if bg_launcher.exists() and bg_game.exists():
        try:
            os.replace(bg_launcher, bg_tmp)
            os.replace(bg_game, bg_launcher)
            swapped = True
        except Exception as e:
            print(f"Aviso: Falló el intercambio de fondos: {e}")

    try:
        if runtime_avatar_file:
            prepare_top1_runtime_avatar(runtime_avatar_file)
            avatar_swapped = True
            print(f"[TOP1] Avatar cargado temporalmente: {runtime_avatar_file}")
        process = subprocess.Popen([str(exe_path)], cwd=str(BASE_DIR))
        return process.wait()
    finally:
        if avatar_swapped:
            try:
                restore_top1_runtime_avatar()
                print("[TOP1] Slot temporal restaurado correctamente")
            except Exception as e:
                print(f"Error crítico al restaurar el avatar TOP #1: {e}")
        if swapped:
            try:
                os.replace(bg_launcher, bg_game)
                os.replace(bg_tmp, bg_launcher)
            except Exception as e:
                print(f"Error crítico al restaurar fondos: {e}")


# ==========================================
# COMPONENTES VISUALES PIXEL ART
# ==========================================

def draw_arcade_panel(surface, rect, bg_color=PANEL_BG, border_color=BLACK, border_w=4, highlight_color=PANEL_BORDER_LIGHT, shadow_color=PANEL_BORDER_DARK):
    pygame.draw.rect(surface, BLACK, rect.move(5, 5))
    pygame.draw.rect(surface, border_color, rect)
    
    inner = rect.inflate(-border_w * 2, -border_w * 2)
    pygame.draw.rect(surface, bg_color, inner)
    
    pygame.draw.line(surface, highlight_color, (inner.x, inner.y), (inner.right - 1, inner.y), 3)
    pygame.draw.line(surface, highlight_color, (inner.x, inner.y), (inner.x, inner.bottom - 1), 3)
    pygame.draw.line(surface, shadow_color, (inner.x + 1, inner.bottom - 2), (inner.right - 1, inner.bottom - 2), 3)
    pygame.draw.line(surface, shadow_color, (inner.right - 2, inner.y + 1), (inner.right - 2, inner.bottom - 1), 3)


class Button:
    def __init__(self, x, y, width, height, text, font, color=WHITE, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER, border_color=BLACK, border_w=4):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.bg = bg
        self.hover_bg = hover_bg
        self.border_color = border_color
        self.border_w = border_w
        self.hovered = False

    def draw(self, surface):
        bg = self.hover_bg if self.hovered else self.bg
        highlight = tuple(min(c + 50, 255) for c in bg)
        shadow = tuple(max(c - 40, 0) for c in bg)

        draw_arcade_panel(
            surface, self.rect,
            bg_color=bg, border_color=self.border_color,
            border_w=self.border_w, highlight_color=highlight, shadow_color=shadow
        )

        text_surface = self.font.render(self.text, True, self.color)
        text_shadow = self.font.render(self.text, True, BLACK)
        t_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_shadow, t_rect.move(2, 2))
        surface.blit(text_surface, t_rect)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


class ImageButton:
    def __init__(self, center_x, center_y, image_path, scale_w=420):
        raw = pygame.image.load(str(image_path)).convert_alpha()
        scale_h = int(raw.get_height() * (scale_w / raw.get_width()))
        self.image = pygame.transform.smoothscale(raw, (scale_w, scale_h))
        self.image_hover = self.image.copy()
        overlay = pygame.Surface(self.image_hover.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 35))
        self.image_hover.blit(overlay, (0, 0))
        self.rect = self.image.get_rect(center=(center_x, center_y))
        self.hovered = False

    def draw(self, surface):
        surface.blit(self.image_hover if self.hovered else self.image, self.rect)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


class Launcher:
    def __init__(self):
        init_db()
        init_avatar_storage()
        recover_top1_runtime_avatar()
        pygame.init()

        AVATARS_DIR.mkdir(parents=True, exist_ok=True)
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

        self.avatar_selector = AvatarSelector(AVATAR_CATALOG_FILE)

        self.avatar_p1 = None
        self.avatar_p2 = None
        self.avatar_match_p1 = None
        self.avatar_match_p2 = None

        self.face_cascades = []

        if (
            cv2 is not None
            and hasattr(cv2, "CascadeClassifier")
            and hasattr(cv2, "data")
            and hasattr(cv2.data, "haarcascades")
        ):
            cascade_files = [
                "haarcascade_frontalface_default.xml",
                "haarcascade_frontalface_alt2.xml",
            ]

            for cascade_file in cascade_files:
                cascade_path = Path(cv2.data.haarcascades) / cascade_file
                cascade = cv2.CascadeClassifier(str(cascade_path))

                if not cascade.empty():
                    self.face_cascades.append(cascade)

        # Compatibilidad con código anterior.
        self.face_cascade = self.face_cascades[0] if self.face_cascades else None

        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Expo Heads UNO")
        self.clock = pygame.time.Clock()

        pixel_font = self._find_pixel_font()
        self.font_title = pygame.font.SysFont(pixel_font, 46, bold=True)
        self.font_subtitle = pygame.font.SysFont(pixel_font, 22)
        self.font_button = pygame.font.SysFont(pixel_font, 26, bold=True)
        self.font_small = pygame.font.SysFont(pixel_font, 18, bold=True)
        self.font_hud_title = pygame.font.SysFont(pixel_font, 22, bold=True)
        self.font_hud_row = pygame.font.SysFont(pixel_font, 16, bold=True)
        self.font_mini = pygame.font.SysFont(pixel_font, 12, bold=True)

        self.running = True
        self.state = "menu"
        self.prev_state = "menu"
        self.game_mode = None
        self.p1_name = ""
        self.p2_name = ""
        self.active_input = 1
        self.finished_mode = ""
        self.status_message = ""
        self.score_saved = False
        
        self.cam = None
        self.cam_surface = None
        self.cam_frame = None
        self.camera_backend_name = ""
        self.camera_index = None
        self.detected_face = None
        self.face_ready = False
        self.face_status = "CENTRA TU CARA EN EL OVALO"
        self.active_camera = 1
        self.photo_p1 = None
        self.photo_p2 = None
        self.player_p1_id = None
        self.player_p2_id = None
        self.avatar_p1_id = None
        self.avatar_p2_id = None
        self.avatar_p1_file = None
        self.avatar_p2_file = None
        self.ranking_avatar_cache = {}

        self.ranking_box_rect = pygame.Rect(900, 22, 275, 195)

        # CHECK FINAL 1: reset del turno. Se mantiene arriba a la izquierda
        # para no interferir con el ranking ni con los botones centrales.
        self.btn_reset_turn = Button(
            18, 18, 165, 42,
            "RESET TURNO",
            self.font_mini,
            color=WHITE,
            bg=(92, 24, 32),
            hover_bg=(150, 35, 48),
            border_color=BLACK,
            border_w=3,
        )
        self.menu_notice = ""
        self.menu_notice_until = 0

        self.bg_image = self._load_background()
        self.logo_image = self._load_logo()
        self._create_menu_buttons()

    @staticmethod
    def _find_pixel_font():
        available = {name.casefold(): name for name in pygame.font.get_fonts()}
        for wanted in ("pressstart2p", "pixelifysans", "vt323"):
            if wanted in available:
                return available[wanted]
        return "Courier"

    def _load_background(self):
        if not BG_FILE.is_file():
            return None
        try:
            image = pygame.image.load(str(BG_FILE)).convert()
            image = pygame.transform.scale(image, (SCREEN_W, SCREEN_H))
            overlay = pygame.Surface((SCREEN_W, SCREEN_H))
            overlay.fill(BLACK)
            overlay.set_alpha(100)
            image.blit(overlay, (0, 0))
            return image
        except pygame.error:
            return None

    @staticmethod
    def _load_logo():
        if not LOGO_FILE.is_file():
            return None
        try:
            raw = pygame.image.load(str(LOGO_FILE)).convert_alpha()
            logo_w = 540
            logo_h = int(raw.get_height() * (logo_w / raw.get_width()))
            return pygame.transform.smoothscale(raw, (logo_w, logo_h))
        except pygame.error:
            return None

    def _create_menu_buttons(self):
        center_x = SCREEN_W // 2
        if BTN_TOP1_FILE.is_file() and BTN_1V1_FILE.is_file():
            self.btn_top1 = ImageButton(center_x, 430, BTN_TOP1_FILE)
            self.btn_1v1 = ImageButton(center_x, 525, BTN_1V1_FILE)
        else:
            self.btn_top1 = Button(center_x - 210, 397, 420, 66, "1 VS TOP #1", self.font_button, bg=BTN_ORANGE, hover_bg=BTN_ORANGE_HOVER)
            self.btn_1v1 = Button(center_x - 210, 497, 420, 66, "1 VS 1", self.font_button, bg=BTN_YELLOW, hover_bg=BTN_YELLOW_HOVER)

        self.btn_exit = Button(
            center_x - 100, 610, 200, 46, "SALIR", self.font_small, 
            color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER, border_color=BLACK, border_w=4
        )

    def _draw_bg(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(DARK_BG)

    def _draw_title(self):
        if self.logo_image:
            rect = self.logo_image.get_rect(center=(SCREEN_W // 2, 120))
            self.screen.blit(self.logo_image, rect)
        else:
            title = self.font_title.render("EXPO HEADS", True, WHITE)
            self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 100)))

    def _load_ranking_avatar(self, avatar_file, max_size):
        """Carga una miniatura una sola vez y conserva su proporción original."""
        cache_key = (avatar_file, int(max_size))
        if cache_key in self.ranking_avatar_cache:
            return self.ranking_avatar_cache[cache_key]

        avatar_path = resolve_ranking_avatar_path(avatar_file)
        if avatar_path is None:
            return None

        try:
            raw = pygame.image.load(str(avatar_path)).convert_alpha()
            width, height = raw.get_size()
            if width <= 0 or height <= 0:
                self.ranking_avatar_cache[cache_key] = None
                return None

            scale = min(max_size / width, max_size / height)
            target_size = (
                max(1, int(round(width * scale))),
                max(1, int(round(height * scale))),
            )
            thumbnail = pygame.transform.smoothscale(raw, target_size)
            self.ranking_avatar_cache[cache_key] = thumbnail
            return thumbnail
        except (OSError, pygame.error):
            # Un PNG viejo o dañado no debe impedir que abra el launcher.
            self.ranking_avatar_cache[cache_key] = None
            return None

    def _draw_ranking_avatar(self, avatar_file, rect, border_color):
        """Dibuja la miniatura o una silueta segura cuando no hay avatar."""
        shadow = rect.move(2, 2)
        pygame.draw.rect(self.screen, BLACK, shadow)
        pygame.draw.rect(self.screen, (8, 14, 25), rect)
        pygame.draw.rect(self.screen, border_color, rect, 2)

        thumbnail = self._load_ranking_avatar(avatar_file, min(rect.width, rect.height) - 4)
        if thumbnail is not None:
            image_rect = thumbnail.get_rect(center=rect.center)
            self.screen.blit(thumbnail, image_rect)
            return

        # Fallback neutral para jugadores heredados sin PNG asociado.
        cx, cy = rect.center
        pygame.draw.circle(self.screen, GRAY, (cx, cy - 3), 6, 2)
        pygame.draw.arc(self.screen, GRAY, (cx - 9, cy + 4, 18, 12), 0, math.pi, 2)

    def _draw_ranking_hud(self):
        r = self.ranking_box_rect

        draw_arcade_panel(
            self.screen, r,
            bg_color=PANEL_BG,
            border_color=BLACK,
            border_w=4,
            highlight_color=PANEL_BORDER_LIGHT,
            shadow_color=PANEL_BORDER_DARK
        )

        time_ms = pygame.time.get_ticks()
        pulse = (math.sin(time_ms * 0.006) + 1) / 2
        r_g = int(ARCADE_GREEN_DIM[0] + (ARCADE_GREEN[0] - ARCADE_GREEN_DIM[0]) * pulse)
        g_g = int(ARCADE_GREEN_DIM[1] + (ARCADE_GREEN[1] - ARCADE_GREEN_DIM[1]) * pulse)
        b_g = int(ARCADE_GREEN_DIM[2] + (ARCADE_GREEN[2] - ARCADE_GREEN_DIM[2]) * pulse)
        neon_color = (r_g, g_g, b_g)

        title_surf = self.font_hud_title.render("RANKING", True, neon_color)
        title_shadow = self.font_hud_title.render("RANKING", True, BLACK)
        title_rect = title_surf.get_rect(center=(r.centerx, r.y + 24))
        self.screen.blit(title_shadow, title_rect.move(2, 2))
        self.screen.blit(title_surf, title_rect)

        line_y = r.y + 46
        pygame.draw.line(self.screen, BTN_YELLOW_DARK, (r.x + 14, line_y + 1), (r.right - 14, line_y + 1), 3)
        pygame.draw.line(self.screen, BTN_YELLOW, (r.x + 14, line_y), (r.right - 14, line_y), 2)

        top3 = get_top_ranking(3)
        podium = [("1ST", GOLD), ("2ND", SILVER), ("3RD", BRONZE)]

        row_y = r.y + 58
        for i in range(3):
            pos_label, color = podium[i]

            if i < len(top3):
                p_name, gf, _gc, _date, avatar_file = top3[i]
                display_name = (p_name[:7] + "..") if len(p_name) > 8 else p_name
                score_label = f"{gf} goles"
            else:
                avatar_file = None
                display_name = "------"
                score_label = "- goles"

            avatar_rect = pygame.Rect(r.x + 47, row_y - 3, 31, 31)
            self._draw_ranking_avatar(avatar_file, avatar_rect, color)

            text_y = row_y + 4

            pos_surf = self.font_hud_row.render(pos_label, True, color)
            pos_shadow = self.font_hud_row.render(pos_label, True, BLACK)
            
            name_surf = self.font_hud_row.render(display_name, True, WHITE)
            name_shadow = self.font_hud_row.render(display_name, True, BLACK)
            
            score_surf = self.font_hud_row.render(score_label, True, BTN_ORANGE_LIGHT)
            score_shadow = self.font_hud_row.render(score_label, True, BLACK)

            self.screen.blit(pos_shadow, (r.x + 13, text_y + 1))
            self.screen.blit(pos_surf, (r.x + 12, text_y))

            self.screen.blit(name_shadow, (r.x + 86, text_y + 1))
            self.screen.blit(name_surf, (r.x + 85, text_y))

            score_rect = score_surf.get_rect(right=r.right - 12, top=text_y)
            self.screen.blit(score_shadow, score_rect.move(1, 1))
            self.screen.blit(score_surf, score_rect)

            row_y += 36

        if (time_ms // 500) % 2 == 0:
            click_surf = self.font_mini.render("CLICK VER TOP 10", True, GRAY)
            self.screen.blit(click_surf, click_surf.get_rect(center=(r.centerx, r.bottom - 13)))

    def _screen_menu(self, events):
        self._draw_bg()
        self._draw_title()
        self._draw_ranking_hud()

        mouse = pygame.mouse.get_pos()

        self.btn_reset_turn.update(mouse)
        self.btn_reset_turn.draw(self.screen)

        for button in (self.btn_top1, self.btn_1v1, self.btn_exit):
            button.update(mouse)
            button.draw(self.screen)

        if self.menu_notice and pygame.time.get_ticks() < self.menu_notice_until:
            notice = self.font_mini.render(self.menu_notice, True, ARCADE_GREEN)
            notice_bg = pygame.Rect(18, 66, notice.get_width() + 18, 28)
            pygame.draw.rect(self.screen, (8, 14, 25), notice_bg)
            pygame.draw.rect(self.screen, ARCADE_GREEN_DIM, notice_bg, 2)
            self.screen.blit(notice, (notice_bg.x + 9, notice_bg.y + 7))
        elif self.menu_notice:
            self.menu_notice = ""

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_reset_turn.clicked(mouse):
                    self.state = "confirm_reset"
                elif self.btn_1v1.clicked(mouse):
                    self.game_mode = "1v1"
                    self.p1_name = ""
                    self.p2_name = ""
                    self.photo_p1 = None
                    self.photo_p2 = None
                    self.avatar_p1 = None
                    self.avatar_p2 = None
                    self.avatar_match_p1 = None
                    self.avatar_match_p2 = None
                    self.player_p1_id = None
                    self.player_p2_id = None
                    self.avatar_p1_id = None
                    self.avatar_p2_id = None
                    self.avatar_p1_file = None
                    self.avatar_p2_file = None
                    self.active_input = 1
                    self.status_message = ""
                    self.state = "input_1v1"
                elif self.btn_top1.clicked(mouse):
                    self.game_mode = "top1"
                    self.p1_name = ""
                    self.photo_p1 = None
                    self.avatar_p1 = None
                    self.avatar_match_p1 = None
                    self.player_p1_id = None
                    self.avatar_p1_id = None
                    self.avatar_p1_file = None
                    self.status_message = ""
                    self.state = "input_top1"
                elif self.ranking_box_rect.collidepoint(mouse):
                    self.state = "ranking"
                elif self.btn_exit.clicked(mouse):
                    self.state = "confirm_exit"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "confirm_exit"

    def _clear_turn_runtime_state(self):
        """Limpia cualquier referencia en memoria después de reiniciar el turno."""
        self._close_camera()

        self.game_mode = None
        self.p1_name = ""
        self.p2_name = ""
        self.active_input = 1

        self.photo_p1 = None
        self.photo_p2 = None
        self.avatar_p1 = None
        self.avatar_p2 = None
        self.avatar_match_p1 = None
        self.avatar_match_p2 = None

        self.player_p1_id = None
        self.player_p2_id = None
        self.avatar_p1_id = None
        self.avatar_p2_id = None
        self.avatar_p1_file = None
        self.avatar_p2_file = None

        self.match_results = None
        self.score_saved = False
        self.finished_mode = ""
        self.status_message = ""

        # Obliga a recargar las miniaturas del ranking vacío/nuevo.
        self.ranking_avatar_cache.clear()

        # Por seguridad, restaura cualquier slot TOP #1 que haya quedado staged.
        try:
            recover_top1_runtime_avatar()
        except OSError as exc:
            print(f"[RESET TURNO] Aviso restaurando TOP #1: {exc}")

    def _screen_confirm_reset(self, events):
        """Confirmación explícita para evitar resets accidentales."""
        self._draw_bg()
        self._draw_title()

        panel = pygame.Rect(
            SCREEN_W // 2 - 360,
            SCREEN_H // 2 - 155,
            720,
            310,
        )
        draw_arcade_panel(
            self.screen,
            panel,
            bg_color=PANEL_BG,
            border_color=ACCENT_2,
            border_w=5,
            highlight_color=(245, 70, 100),
            shadow_color=(80, 10, 25),
        )

        title = self.font_subtitle.render(
            "REINICIAR TURNO?",
            True,
            ACCENT_2,
        )
        self.screen.blit(
            title,
            title.get_rect(center=(SCREEN_W // 2, panel.y + 52)),
        )

        lines = (
            "SE BORRARAN JUGADORES, PARTIDAS Y RANKING ACTUAL.",
            "LA BIBLIOTECA DE AVATARES Y EL JUEGO NO SE TOCAN.",
            "ESTA ACCION NO SE PUEDE DESHACER.",
        )
        for index, line in enumerate(lines):
            color = WHITE if index < 2 else BTN_YELLOW_LIGHT
            surf = self.font_small.render(line, True, color)
            self.screen.blit(
                surf,
                surf.get_rect(
                    center=(
                        SCREEN_W // 2,
                        panel.y + 103 + index * 30,
                    )
                ),
            )

        btn_cancel = Button(
            SCREEN_W // 2 - 245,
            panel.bottom - 76,
            210,
            52,
            "CANCELAR",
            self.font_small,
            color=GRAY,
            bg=BTN_GRAY_BG,
            hover_bg=BTN_GRAY_HOVER,
        )
        btn_confirm = Button(
            SCREEN_W // 2 + 35,
            panel.bottom - 76,
            210,
            52,
            "REINICIAR",
            self.font_small,
            color=WHITE,
            bg=(130, 25, 38),
            hover_bg=(205, 38, 58),
        )

        mouse = pygame.mouse.get_pos()
        for button in (btn_cancel, btn_confirm):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_cancel.clicked(mouse):
                    self.state = "menu"
                elif btn_confirm.clicked(mouse):
                    try:
                        reset_turn_data()
                        self._clear_turn_runtime_state()
                        self.menu_notice = "TURNO REINICIADO - RANKING VACIO"
                        self.menu_notice_until = pygame.time.get_ticks() + 4500
                        self.state = "menu"
                    except (OSError, sqlite3.Error) as exc:
                        self.status_message = f"ERROR AL REINICIAR: {exc}"
                        print(f"[RESET TURNO] ERROR: {exc}")
                        self.state = "menu"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "menu"

    def _draw_silhouette(self, rect, color, photo=None):
        draw_arcade_panel(self.screen, rect, bg_color=PANEL_BG, border_color=color, border_w=4)
        
        if photo:
            photo_rect = photo.get_rect(center=rect.center)
            self.screen.blit(photo, photo_rect)
            pygame.draw.rect(self.screen, color, photo_rect, 2)
        else:
            cx, cy = rect.center
            pygame.draw.circle(self.screen, GRAY, (cx, cy - 25), 35, 4)
            pygame.draw.arc(self.screen, GRAY, (cx - 55, cy + 10, 110, 80), 0, math.pi, 4)
            
            time_ms = pygame.time.get_ticks()
            if (time_ms // 500) % 2 == 0:
                text = self.font_mini.render("CLICK FOTO", True, WHITE)
                self.screen.blit(text, text.get_rect(center=(cx, rect.bottom - 20)))

    def _close_camera(self):
        """Libera la webcam de OpenCV de forma segura."""
        if self.cam is not None:
            try:
                self.cam.release()
            except Exception:
                pass
        self.cam = None
        self.cam_surface = None
        self.cam_frame = None
        self.camera_backend_name = ""
        self.camera_index = None
        self.detected_face = None
        self.face_ready = False
        self.face_status = "CENTRA TU CARA EN EL OVALO"

    def _open_camera(self, player_num):
        """Abre la primera webcam disponible usando OpenCV.

        Prioriza DirectShow en Windows y el índice 0, pero prueba otros
        backends/índices para mantener el launcher portable entre equipos.
        """
        if cv2 is None:
            self.status_message = (
                "OPENCV NO ESTA INSTALADO. EJECUTA: python -m pip install opencv-python"
            )
            return

        self._close_camera()

        backends = [
            ("DirectShow", cv2.CAP_DSHOW),
            ("Media Foundation", cv2.CAP_MSMF),
            ("AUTO", cv2.CAP_ANY),
        ]

        selected_cam = None
        selected_backend = ""
        selected_index = None

        for camera_index in CAMERA_INDICES:
            for backend_name, backend in backends:
                cam = cv2.VideoCapture(camera_index, backend)

                if not cam.isOpened():
                    cam.release()
                    continue

                cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

                ok, frame = cam.read()
                if not ok or frame is None:
                    cam.release()
                    continue

                selected_cam = cam
                selected_backend = backend_name
                selected_index = camera_index
                self.cam_frame = cv2.flip(frame, 1)
                break

            if selected_cam is not None:
                break

        if selected_cam is None:
            self.status_message = "NO SE PUDO ABRIR NINGUNA CAMARA CON OPENCV."
            return

        self.cam = selected_cam
        self.camera_backend_name = selected_backend
        self.camera_index = selected_index
        self.active_camera = player_num
        self.prev_state = self.state
        self.status_message = ""
        self.state = "camera"

    @staticmethod
    def _opencv_frame_to_pygame(frame_bgr):
        """Convierte BGR de OpenCV a Surface de Pygame."""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]

        # copy() desacopla la Surface del buffer temporal de NumPy/OpenCV.
        return pygame.image.frombuffer(
            frame_rgb.tobytes(),
            (w, h),
            "RGB"
        ).copy()

    def _detect_target_face(self, frame_bgr):
        """
        Detección facial tolerante para webcam de evento.

        Estrategia:
        - prueba dos Haar Cascades frontales;
        - usa imagen normal y ecualizada;
        - parámetros más permisivos;
        - entre varias caras elige la más grande/cercana al centro;
        - muestra estados separados para detección y alineación.
        """
        self.detected_face = None
        self.face_ready = False

        cascades = getattr(self, "face_cascades", [])
        if not cascades:
            self.face_status = "DETECTOR FACIAL NO DISPONIBLE"
            return

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # Dos versiones de contraste ayudan mucho con webcams y luz variable.
        equalized = cv2.equalizeHist(gray)

        detected = []

        for cascade in cascades:
            for img in (gray, equalized):
                faces = cascade.detectMultiScale(
                    img,
                    scaleFactor=1.05,
                    minNeighbors=3,
                    minSize=(45, 45),
                    flags=cv2.CASCADE_SCALE_IMAGE,
                )

                for face in faces:
                    x, y, w, h = [int(v) for v in face]
                    detected.append((x, y, w, h))

        if not detected:
            self.face_status = "NO SE DETECTA ROSTRO - MIRA DE FRENTE"
            return

        frame_h, frame_w = frame_bgr.shape[:2]
        guide_cx = frame_w // 2
        guide_cy = frame_h // 2

        # Priorizamos:
        # 1) tamaño de la cara
        # 2) cercanía al centro
        def face_priority(face):
            x, y, w, h = face
            cx = x + w / 2
            cy = y + h / 2

            dist = (
                (cx - guide_cx) ** 2 +
                (cy - guide_cy) ** 2
            ) ** 0.5

            area = w * h

            return area - (dist * 120)

        x, y, w, h = max(detected, key=face_priority)

        self.detected_face = (x, y, w, h)

        face_cx = x + w // 2
        face_cy = y + h // 2

        dx = face_cx - guide_cx
        dy = face_cy - guide_cy

        # Primero informamos que efectivamente hay cara detectada.
        if abs(dx) > FACE_CENTER_TOL_X:
            self.face_status = "ROSTRO DETECTADO - CENTRATE"
            return

        if abs(dy) > FACE_CENTER_TOL_Y:
            self.face_status = "ROSTRO DETECTADO - AJUSTA ALTURA"
            return

        if w < FACE_MIN_W:
            self.face_status = "ROSTRO DETECTADO - ACERCATE"
            return

        if w > FACE_MAX_W:
            self.face_status = "ROSTRO DETECTADO - ALEJATE"
            return

        self.face_ready = True
        self.face_status = "ROSTRO OK - PRESIONA ESPACIO"

    def _draw_face_guide(self, camera_rect):
        """
        Dibuja una máscara oscura exterior y un óvalo transparente,
        similar a una interfaz de reconocimiento facial bancario.
        """
        # Coordenadas del óvalo en la Surface de cámara.
        local_cx = camera_rect.width // 2
        local_cy = camera_rect.height // 2

        guide_rect_local = pygame.Rect(
            local_cx - FACE_GUIDE_W // 2,
            local_cy - FACE_GUIDE_H // 2,
            FACE_GUIDE_W,
            FACE_GUIDE_H,
        )

        # Máscara: oscurece todo, luego "perfora" el óvalo.
        mask = pygame.Surface(
            (camera_rect.width, camera_rect.height),
            pygame.SRCALPHA
        )
        mask.fill((0, 0, 0, 145))
        pygame.draw.ellipse(
            mask,
            (0, 0, 0, 0),
            guide_rect_local
        )

        self.screen.blit(mask, camera_rect.topleft)

        guide_rect_screen = guide_rect_local.move(
            camera_rect.x,
            camera_rect.y
        )

        color = ARCADE_GREEN if self.face_ready else BTN_ORANGE_LIGHT
        pygame.draw.ellipse(self.screen, color, guide_rect_screen, 5)

        # Pequeñas marcas laterales tipo UI de escaneo.
        tick = 18
        cx, cy = guide_rect_screen.center
        pygame.draw.line(
            self.screen, color,
            (guide_rect_screen.left - 8, cy),
            (guide_rect_screen.left + tick, cy), 3
        )
        pygame.draw.line(
            self.screen, color,
            (guide_rect_screen.right - tick, cy),
            (guide_rect_screen.right + 8, cy), 3
        )

    def _extract_head_crop(self, frame_bgr):
        """
        Recorta únicamente la cabeza objetivo.

        Se amplía la caja facial hacia arriba y los costados para conservar:
        - pelo
        - anteojos
        - barba
        - forma general de la cabeza

        De esta forma, la multitud del fondo prácticamente desaparece
        del material que utilizará face_analyzer.py.
        """
        if self.detected_face is None:
            return None

        x, y, w, h = self.detected_face
        frame_h, frame_w = frame_bgr.shape[:2]

        # Márgenes amplios para incluir cabello y barba.
        left = int(x - 0.45 * w)
        right = int(x + 1.45 * w)
        top = int(y - 0.65 * h)
        bottom = int(y + 1.45 * h)

        left = max(0, left)
        top = max(0, top)
        right = min(frame_w, right)
        bottom = min(frame_h, bottom)

        crop = frame_bgr[top:bottom, left:right].copy()
        if crop.size == 0:
            return None

        # Convertimos a cuadrado agregando borde negro solo si hace falta.
        ch, cw = crop.shape[:2]
        size = max(ch, cw)

        canvas = cv2.copyMakeBorder(
            crop,
            top=(size - ch) // 2,
            bottom=size - ch - (size - ch) // 2,
            left=(size - cw) // 2,
            right=size - cw - (size - cw) // 2,
            borderType=cv2.BORDER_CONSTANT,
            # Gris neutro: el padding negro se confundía con pelo negro y
            # producía falsos "hair_length=long".
            value=(127, 127, 127),
        )

        return canvas

    def _estimate_avatar_colors(self, scan_bgr):
        """
        Estima los colores que personalizarán el template seleccionado.

        El matching estructural sigue perteneciendo a face_analyzer.py +
        AvatarSelector. Esta función SOLO obtiene colores del mismo scan.

        Retorna:
            skin_rgb
            hair_rgb
            eye_rgb
            glasses_rgb
            beard_rgb
        """
        if scan_bgr is None or scan_bgr.size == 0:
            raise RuntimeError("El scan está vacío.")

        gray = cv2.cvtColor(scan_bgr, cv2.COLOR_BGR2GRAY)
        equalized = cv2.equalizeHist(gray)

        detected = []

        for cascade in self.face_cascades:
            for source in (gray, equalized):
                faces = cascade.detectMultiScale(
                    source,
                    scaleFactor=1.08,
                    minNeighbors=4,
                    minSize=(55, 55),
                    flags=cv2.CASCADE_SCALE_IMAGE,
                )

                for face in faces:
                    detected.append(
                        tuple(int(v) for v in face)
                    )

        img_h, img_w = scan_bgr.shape[:2]

        if detected:
            # El scan ya contiene únicamente la cabeza objetivo.
            # Elegimos simplemente la cara de mayor superficie.
            x, y, w, h = max(
                detected,
                key=lambda f: f[2] * f[3],
            )
        else:
            # Fallback seguro: el scan proviene de una cara ya validada por
            # el detector del launcher, por lo que podemos usar el centro.
            x = int(img_w * 0.22)
            y = int(img_h * 0.17)
            w = int(img_w * 0.56)
            h = int(img_h * 0.60)

        skin_mask = _skin_mask_ycrcb(scan_bgr)

        # --------------------------------------------------
        # PIEL - mejillas, evitando ojos/pelo.
        # --------------------------------------------------
        skin_pixels = []

        cheek_specs = [
            (
                x + 0.18 * w,
                y + 0.46 * h,
                x + 0.38 * w,
                y + 0.73 * h,
            ),
            (
                x + 0.62 * w,
                y + 0.46 * h,
                x + 0.82 * w,
                y + 0.73 * h,
            ),
        ]

        for x1, y1, x2, y2 in cheek_specs:
            roi = _crop_array(
                scan_bgr, x1, y1, x2, y2
            )
            roi_mask = _crop_array(
                (skin_mask.astype(np.uint8) * 255),
                x1, y1, x2, y2,
            )

            if roi is None or roi_mask is None:
                continue

            valid = roi_mask > 0
            if np.any(valid):
                skin_pixels.append(roi[valid])

        if skin_pixels:
            skin_pixels = np.concatenate(
                skin_pixels,
                axis=0,
            )
        else:
            face_roi = _crop_array(
                scan_bgr,
                x, y,
                x + w,
                y + h,
            )
            face_mask = _crop_array(
                (skin_mask.astype(np.uint8) * 255),
                x, y,
                x + w,
                y + h,
            )

            if (
                face_roi is not None
                and face_mask is not None
                and np.any(face_mask > 0)
            ):
                skin_pixels = face_roi[
                    face_mask > 0
                ]
            else:
                skin_pixels = np.empty(
                    (0, 3),
                    dtype=np.uint8,
                )

        skin_bgr = _median_color(
            skin_pixels,
            fallback=(145, 175, 220),
        )
        skin_rgb = _ensure_rgb(
            _bgr_to_rgb(skin_bgr)
        )

        # --------------------------------------------------
        # PELO - zona superior y lateral de la cara.
        # --------------------------------------------------
        hair_roi = _crop_array(
            scan_bgr,
            x - 0.12 * w,
            y - 0.42 * h,
            x + 1.12 * w,
            y + 0.24 * h,
        )
        hair_skin_mask = _crop_array(
            (skin_mask.astype(np.uint8) * 255),
            x - 0.12 * w,
            y - 0.42 * h,
            x + 1.12 * w,
            y + 0.24 * h,
        )

        if hair_roi is None:
            hair_rgb = (75, 52, 38)
        else:
            hsv = cv2.cvtColor(
                hair_roi,
                cv2.COLOR_BGR2HSV,
            )

            saturation = hsv[..., 1]
            value = hsv[..., 2]

            not_skin = np.ones(
                hair_roi.shape[:2],
                dtype=bool,
            )

            if hair_skin_mask is not None:
                not_skin = hair_skin_mask == 0

            candidates = (
                not_skin
                & (saturation > 28)
                & (value > 18)
                & (value < 215)
            )

            pixels = hair_roi[candidates]

            if len(pixels) < 80:
                candidates = (
                    not_skin
                    & (value > 18)
                    & (value < 210)
                )
                pixels = hair_roi[candidates]

            hair_bgr = _median_color(
                pixels,
                fallback=(45, 65, 90),
            )
            hair_rgb = _ensure_rgb(
                _bgr_to_rgb(hair_bgr)
            )

        # --------------------------------------------------
        # OJOS - aproximación. Es el dato menos confiable,
        # pero solo modifica la pequeña región de iris.
        # --------------------------------------------------
        eye_roi = _crop_array(
            scan_bgr,
            x + 0.17 * w,
            y + 0.27 * h,
            x + 0.83 * w,
            y + 0.54 * h,
        )

        eye_rgb = (92, 72, 52)

        if eye_roi is not None:
            eye_hsv = cv2.cvtColor(
                eye_roi,
                cv2.COLOR_BGR2HSV,
            )
            saturation = eye_hsv[..., 1]
            value = eye_hsv[..., 2]

            candidates = (
                (saturation > 20)
                & (value > 25)
                & (value < 195)
            )

            pixels = eye_roi[candidates]

            if len(pixels) > 20:
                eye_bgr = _median_color(
                    pixels,
                    fallback=(52, 72, 92),
                )
                eye_rgb = _ensure_rgb(
                    _bgr_to_rgb(eye_bgr)
                )

        # --------------------------------------------------
        # ANTEOJOS - estimación opcional; si no hay evidencia
        # suficiente usamos un tono derivado del pelo.
        # --------------------------------------------------
        glasses_rgb = _darken_rgb(
            hair_rgb,
            0.35,
        )

        if eye_roi is not None:
            eye_hsv = cv2.cvtColor(
                eye_roi,
                cv2.COLOR_BGR2HSV,
            )
            saturation = eye_hsv[..., 1]
            value = eye_hsv[..., 2]

            candidates = (
                (value > 15)
                & (value < 145)
                & (saturation > 10)
            )

            pixels = eye_roi[candidates]

            if len(pixels) > 30:
                glasses_bgr = _median_color(
                    pixels,
                    fallback=_rgb_to_bgr(
                        glasses_rgb
                    ),
                )
                glasses_rgb = _ensure_rgb(
                    _bgr_to_rgb(glasses_bgr)
                )

        beard_rgb = _darken_rgb(
            hair_rgb,
            0.18,
        )

        return {
            "skin_rgb": skin_rgb,
            "hair_rgb": hair_rgb,
            "eye_rgb": _ensure_rgb(eye_rgb),
            "glasses_rgb": _ensure_rgb(
                glasses_rgb
            ),
            "beard_rgb": _ensure_rgb(
                beard_rgb
            ),
        }

    def _sanitize_detected_traits(self, detected_traits):
        """
        Limpia falsos positivos antes del selector.

        En particular, los anteojos son un rasgo demasiado fuerte para dejar
        que un TRUE de baja confianza fuerce un avatar con lentes. Los FALSE
        se conservan: si la cámara ve claramente que no hay anteojos, el
        selector filtra todos los templates con lentes cuando existen opciones.
        """
        cleaned = dict(detected_traits or {})
        confidence = cleaned.get("_confidence")
        if not isinstance(confidence, dict):
            confidence = {}

        def conf(field, default=1.0):
            try:
                return float(confidence.get(field, default))
            except (TypeError, ValueError):
                return default

        # Anteojos: TRUE requiere evidencia alta. Si es dudoso queda None y no
        # domina el matching; FALSE sigue siendo una señal estructural fuerte.
        if cleaned.get("glasses") is True and conf("glasses") < 0.90:
            print(
                f"[TRAITS] glasses=True descartado por baja confianza "
                f"({conf('glasses'):.2f})"
            )
            cleaned["glasses"] = None

        # Vello facial: evita bigotes/barbas inventados por sombras o cabello.
        if cleaned.get("beard") is True and conf("beard") < 0.70:
            print(f"[TRAITS] beard=True descartado ({conf('beard'):.2f})")
            cleaned["beard"] = False
        if cleaned.get("moustache") is True and conf("moustache") < 0.70:
            print(f"[TRAITS] moustache=True descartado ({conf('moustache'):.2f})")
            cleaned["moustache"] = False

        # Calvicie también requiere evidencia razonable.
        if cleaned.get("bald") is True and conf("bald") < 0.78:
            print(f"[TRAITS] bald=True descartado ({conf('bald'):.2f})")
            cleaned["bald"] = False

        # No hacemos competir datos internos contra los rasgos del catálogo.
        cleaned["_confidence"] = confidence
        return cleaned

    def _capture_current_player(self):
        """
        Flujo definitivo de Expo Heads:

        1. Guarda captura RAW.
        2. Extrae/normaliza la cabeza objetivo.
        3. Guarda player_X_scan.png.
        4. face_analyzer.py detecta RASGOS.
        5. AvatarSelector + avatars_catalog.json eligen ESTRUCTURA.
        6. Se estiman COLORES desde el mismo scan.
        7. Se recolorea el template ganador.
        8. Se genera igrac21/igrac22 SIEMPRE en 70x70.
        9. El preview muestra el avatar FINAL recoloreado.

        El ranking y la base archivan posteriormente ese avatar final,
        no el template de biblioteca.
        """
        if self.cam_frame is None:
            self.status_message = "NO HAY FRAME DE CAMARA."
            return False

        if not self.face_ready or self.detected_face is None:
            self.status_message = self.face_status
            return False

        frame = self.cam_frame.copy()

        CAPTURES_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
        AVATARS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # --------------------------------------------------
        # 1) RAW para diagnóstico
        # --------------------------------------------------
        raw_path = (
            CAPTURES_DIR
            / f"player_{self.active_camera}_raw.png"
        )
        cv2.imwrite(str(raw_path), frame)

        # --------------------------------------------------
        # 2) Recorte de cabeza
        # --------------------------------------------------
        head_crop = self._extract_head_crop(frame)

        if head_crop is None:
            self.status_message = (
                "NO SE PUDO RECORTAR LA CABEZA."
            )
            return False

        # --------------------------------------------------
        # 3) Scan normalizado 320x320
        # --------------------------------------------------
        scan_path = (
            CAPTURES_DIR
            / f"player_{self.active_camera}_scan.png"
        )

        scan_img = cv2.resize(
            head_crop,
            (320, 320),
            interpolation=cv2.INTER_AREA,
        )

        if not cv2.imwrite(
            str(scan_path),
            scan_img,
        ):
            self.status_message = (
                "NO SE PUDO GUARDAR EL ESCANEO."
            )
            return False

        # --------------------------------------------------
        # 4) RASGOS ESTRUCTURALES
        # --------------------------------------------------
        try:
            detected_traits = analyze_face(
                scan_path
            )
            detected_traits = self._sanitize_detected_traits(detected_traits)
        except Exception as exc:
            print(
                f"[Expo Heads] Error face_analyzer: {exc}"
            )
            self.status_message = (
                f"ERROR ANALIZANDO ROSTRO: {exc}"
            )
            return False

        print()
        print("=" * 68)
        print(
            f"[JUGADOR {self.active_camera}] "
            "RASGOS DETECTADOS"
        )

        for key, value in detected_traits.items():
            print(f"  {key}: {value}")

        # --------------------------------------------------
        # 5) MATCHING ESTRUCTURAL MEDIANTE JSON GLOBAL
        # --------------------------------------------------
        try:
            top_matches = self.avatar_selector.rank(
                detected_traits,
                top_k=3,
            )
        except Exception as exc:
            print(
                f"[Expo Heads] "
                f"Error avatar_selector: {exc}"
            )
            self.status_message = (
                f"ERROR SELECCIONANDO AVATAR: {exc}"
            )
            return False

        if not top_matches:
            self.status_message = (
                "NO HAY AVATARES COMPATIBLES "
                "EN EL CATALOGO."
            )
            return False

        best = top_matches[0]

        print()
        print("TOP MATCHES:")

        for pos, candidate in enumerate(
            top_matches,
            1,
        ):
            print(
                f"  #{pos} {candidate.avatar_id} "
                f"score={candidate.score:.2f} "
                f"confidence="
                f"{candidate.confidence:.1%} "
                f"file={candidate.file}"
            )

            breakdown = getattr(
                candidate,
                "breakdown",
                {},
            )

            if breakdown:
                print(
                    "      "
                    f"piel="
                    f"{breakdown.get('skin', 0):.1f}/40  "
                    f"pelo="
                    f"{breakdown.get('hair', 0):.1f}/30  "
                    f"anteojos="
                    f"{breakdown.get('glasses', 0):.1f}/20  "
                    f"barba="
                    f"{breakdown.get('facial_hair', 0):.1f}/10"
                )

        # --------------------------------------------------
        # 6) Resolver template ganador
        # --------------------------------------------------
        catalog_path_value = Path(best.file)
        candidate_paths = []

        if catalog_path_value.is_absolute():
            candidate_paths.append(
                catalog_path_value
            )
        else:
            candidate_paths.extend([
                BASE_DIR / catalog_path_value,
                BASE_DIR
                / "data"
                / catalog_path_value,
                AVATARS_DIR
                / catalog_path_value.name,
            ])

        selected_avatar_path = next(
            (
                path
                for path in candidate_paths
                if path.is_file()
            ),
            None,
        )

        if selected_avatar_path is None:
            print(
                "[Expo Heads] Paths probados:"
            )
            for path in candidate_paths:
                print(" ", path)

            self.status_message = (
                f"FALTA PNG DEL AVATAR: "
                f"{best.avatar_id}"
            )
            return False

        # --------------------------------------------------
        # 7) COLORES PERSONALIZADOS
        # --------------------------------------------------
        try:
            detected_colors = (
                self._estimate_avatar_colors(
                    scan_img
                )
            )
        except Exception as exc:
            print(
                f"[Expo Heads] "
                f"Error detectando colores: {exc}"
            )
            self.status_message = (
                f"ERROR DETECTANDO COLORES: {exc}"
            )
            return False

        print()
        print("COLORES DETECTADOS:")

        for key, value in detected_colors.items():
            print(f"  {key}: {value}")

        # --------------------------------------------------
        # 8) RECOLOREAR + GENERAR SLOT FINAL 70x70
        # --------------------------------------------------
        runtime_avatar = (
            RUNTIME_PLAYER_AVATAR_P1
            if self.active_camera == 1
            else RUNTIME_PLAYER_AVATAR_P2
        )

        game_path = BASE_DIR.joinpath(
            *runtime_avatar.split("/")
        )
        game_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            final_avatar_path, recolor_mode = (
                recolor_avatar_template(
                    selected_avatar_path,
                    game_path,
                    detected_colors,
                    avatar_traits=getattr(best, "avatar_traits", {}),
                )
            )
        except Exception as exc:
            print(
                f"[Expo Heads] "
                f"Error recoloreando avatar: {exc}"
            )
            self.status_message = (
                f"ERROR RECOLOREANDO AVATAR: {exc}"
            )
            return False

        print()
        print(
            f"[RECOLOR] template="
            f"{best.avatar_id}"
        )
        print(
            f"[RECOLOR] modo={recolor_mode}"
        )
        print(
            f"[RECOLOR] salida="
            f"{final_avatar_path}"
        )
        print(
            f"[RECOLOR] tamaño final="
            f"{AVATAR_OUTPUT_SIZE}x"
            f"{AVATAR_OUTPUT_SIZE}"
        )
        print("=" * 68)
        print()

        # --------------------------------------------------
        # 9) Preview DEL RESULTADO FINAL, no del template
        # --------------------------------------------------
        try:
            avatar_preview = pygame.image.load(
                str(final_avatar_path)
            ).convert_alpha()

            avatar_preview = (
                pygame.transform.scale(
                    avatar_preview,
                    (140, 140),
                )
            )
        except Exception as exc:
            self.status_message = (
                f"ERROR CARGANDO PREVIEW: {exc}"
            )
            return False

        if self.active_camera == 1:
            self.photo_p1 = avatar_preview
            self.avatar_p1 = str(
                final_avatar_path
            )
            self.avatar_match_p1 = best
        else:
            self.photo_p2 = avatar_preview
            self.avatar_p2 = str(
                final_avatar_path
            )
            self.avatar_match_p2 = best

        mode_label = {
            "semantic": "COLOR OK",
            "semantic_hsv": "COLOR OK",
            "legacy_hsv": "COLOR POC",
            "passthrough": "RECOLOR NO APLICADO",
        }.get(
            recolor_mode,
            recolor_mode.upper(),
        )

        self.status_message = (
            f"AVATAR: {best.avatar_id} - "
            f"{best.confidence:.0%} MATCH - "
            f"{mode_label}"
        )

        return True


    def _screen_camera(self, events):
        self.screen.fill(BLACK)

        if self.cam is not None:
            ok, frame = self.cam.read()
            if ok and frame is not None:
                self.cam_frame = cv2.flip(frame, 1)

                # Analizamos únicamente cuál es la cara objetivo.
                self._detect_target_face(self.cam_frame)

                self.cam_surface = self._opencv_frame_to_pygame(
                    self.cam_frame
                )

        camera_rect = None

        if self.cam_surface:
            camera_rect = self.cam_surface.get_rect(
                center=(SCREEN_W // 2, SCREEN_H // 2)
            )
            self.screen.blit(self.cam_surface, camera_rect)

            # DEBUG VISUAL:
            # Si OpenCV detectó una cara, mostramos su caja.
            # Verde = lista para capturar.
            # Amarillo = detectada pero todavía mal posicionada.
            if self.detected_face is not None:
                fx, fy, fw, fh = self.detected_face
                face_box = pygame.Rect(
                    camera_rect.x + fx,
                    camera_rect.y + fy,
                    fw,
                    fh,
                )
                debug_color = ARCADE_GREEN if self.face_ready else BTN_YELLOW
                pygame.draw.rect(self.screen, debug_color, face_box, 2)

            # Oscurecer fondo + óvalo de posicionamiento.
            self._draw_face_guide(camera_rect)

        title = self.font_title.render(
            f"ESCANEO JUGADOR {self.active_camera}",
            True,
            ACCENT
        )
        title_shadow = self.font_title.render(
            f"ESCANEO JUGADOR {self.active_camera}",
            True,
            DARK_GRAY
        )
        t_rect = title.get_rect(center=(SCREEN_W // 2, 48))
        self.screen.blit(title_shadow, t_rect.move(3, 3))
        self.screen.blit(title, t_rect)

        backend_text = self.font_mini.render(
            f"CAMARA {self.camera_index} - {self.camera_backend_name} - DETECTOR V3",
            True,
            GRAY,
        )
        self.screen.blit(
            backend_text,
            backend_text.get_rect(center=(SCREEN_W // 2, 88)),
        )

        # Estado de alineación.
        status_color = ARCADE_GREEN if self.face_ready else BTN_ORANGE_LIGHT
        status_surface = self.font_small.render(
            self.face_status,
            True,
            status_color
        )
        status_bg = pygame.Rect(
            SCREEN_W // 2 - 245,
            SCREEN_H - 112,
            490,
            36,
        )
        pygame.draw.rect(self.screen, BLACK, status_bg)
        pygame.draw.rect(self.screen, status_color, status_bg, 2)
        self.screen.blit(
            status_surface,
            status_surface.get_rect(center=status_bg.center),
        )

        if self.face_ready:
            inst_text = "ESPACIO: CAPTURAR   |   ESC: CANCELAR"
        else:
            inst_text = "ALINEA TU CARA   |   ESC: CANCELAR"

        inst = self.font_small.render(inst_text, True, WHITE)
        self.screen.blit(
            inst,
            inst.get_rect(center=(SCREEN_W // 2, SCREEN_H - 48)),
        )

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.face_ready and self._capture_current_player():
                        self._close_camera()
                        self.state = self.prev_state

                elif event.key == pygame.K_ESCAPE:
                    self._close_camera()
                    self.state = self.prev_state

            elif event.type == pygame.QUIT:
                self._close_camera()
                self.running = False

    def _draw_input_box(self, label, name, x, y, active, color):
        label_surface = self.font_small.render(label, True, color)
        label_shadow = self.font_small.render(label, True, BLACK)
        self.screen.blit(label_shadow, (x + 2, y + 2))
        self.screen.blit(label_surface, (x, y))

        rect = pygame.Rect(x, y + 28, 450, 52)
        highlight = color if active else (50, 60, 80)
        shadow = tuple(max(c - 80, 0) for c in color) if active else (10, 15, 25)
        
        draw_arcade_panel(
            self.screen, rect, bg_color=(10, 15, 25), border_color=BLACK, 
            border_w=3, highlight_color=highlight, shadow_color=shadow
        )

        time_ms = pygame.time.get_ticks()
        cursor = "_" if active and (time_ms // 400) % 2 == 0 else ""
        text_surface = self.font_button.render(name + cursor, True, WHITE)
        self.screen.blit(text_surface, (rect.x + 18, rect.y + 12))
        return rect

    def _draw_status(self, x, y):
        if self.status_message:
            text = self.font_small.render(self.status_message[:82], True, ACCENT_2)
            self.screen.blit(text, text.get_rect(center=(x, y)))

    @staticmethod
    def _valid_input_character(event):
        return bool(event.unicode) and len(event.unicode) == 1 and event.unicode.isprintable() and event.unicode != "|"

    def _screen_input_1v1(self, events):
        self._draw_bg()

        left_panel = pygame.Rect(80, 120, 560, 430)
        cam1_rect = pygame.Rect(700, 120, 400, 195)
        cam2_rect = pygame.Rect(700, 345, 400, 195)

        draw_arcade_panel(self.screen, left_panel, bg_color=PANEL_BG, border_color=BLACK)
        
        t_surf = self.font_button.render("1 VS 1", True, BTN_YELLOW)
        t_shadow = self.font_button.render("1 VS 1", True, BLACK)
        t_pos = t_surf.get_rect(center=(left_panel.centerx, left_panel.y + 35))
        self.screen.blit(t_shadow, t_pos.move(2, 2))
        self.screen.blit(t_surf, t_pos)

        sub_surf = self.font_small.render("INGRESA LOS NOMBRES", True, WHITE)
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(left_panel.centerx, left_panel.y + 70)))

        box_1 = self._draw_input_box("JUGADOR 1:", self.p1_name, left_panel.x + 55, left_panel.y + 95, self.active_input == 1, ACCENT)
        box_2 = self._draw_input_box("JUGADOR 2:", self.p2_name, left_panel.x + 55, left_panel.y + 205, self.active_input == 2, BTN_ORANGE_LIGHT)
        
        self._draw_status(left_panel.centerx, left_panel.y + 325)

        # VOLVER a la izquierda, JUGAR a la derecha
        btn_back = Button(
            left_panel.centerx - 165, left_panel.bottom - 65, 150, 45, "VOLVER", self.font_small, 
            color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER
        )
        can_play = bool(self.p1_name.strip() and self.p2_name.strip() and self.avatar_match_p1 and self.avatar_match_p2)
        btn_play = Button(
            left_panel.centerx + 15, left_panel.bottom - 65, 150, 45, "JUGAR", self.font_button, 
            color=WHITE if can_play else GRAY, 
            bg=(35, 140, 65) if can_play else (40, 40, 50), 
            hover_bg=(45, 175, 80) if can_play else (40, 40, 50)
        )

        self._draw_silhouette(cam1_rect, ACCENT, self.photo_p1)
        self._draw_silhouette(cam2_rect, BTN_ORANGE_LIGHT, self.photo_p2)

        if self.avatar_match_p1:
            match_text = self.font_mini.render(
                f"{self.avatar_match_p1.avatar_id} - {self.avatar_match_p1.confidence:.0%}",
                True,
                ARCADE_GREEN
            )
            self.screen.blit(
                match_text,
                match_text.get_rect(center=(cam1_rect.centerx, cam1_rect.bottom - 12))
            )

        if self.avatar_match_p2:
            match_text = self.font_mini.render(
                f"{self.avatar_match_p2.avatar_id} - {self.avatar_match_p2.confidence:.0%}",
                True,
                ARCADE_GREEN
            )
            self.screen.blit(
                match_text,
                match_text.get_rect(center=(cam2_rect.centerx, cam2_rect.bottom - 12))
            )

        mouse = pygame.mouse.get_pos()
        for button in (btn_play, btn_back):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                can_play = bool(self.p1_name.strip() and self.p2_name.strip() and self.avatar_match_p1 and self.avatar_match_p2)
                if btn_play.clicked(mouse) and can_play:
                    self._start_match_1v1()
                elif btn_back.clicked(mouse):
                    self.state = "menu"
                elif box_1.collidepoint(mouse):
                    self.active_input = 1
                elif box_2.collidepoint(mouse):
                    self.active_input = 2
                elif cam1_rect.collidepoint(mouse):
                    self._open_camera(1)
                elif cam2_rect.collidepoint(mouse):
                    self._open_camera(2)
            elif event.type == pygame.KEYDOWN:
                can_play = bool(self.p1_name.strip() and self.p2_name.strip() and self.avatar_match_p1 and self.avatar_match_p2)
                if event.key == pygame.K_TAB:
                    self.active_input = 2 if self.active_input == 1 else 1
                elif event.key == pygame.K_RETURN and can_play:
                    self._start_match_1v1()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif event.key == pygame.K_BACKSPACE:
                    if self.active_input == 1:
                        self.p1_name = self.p1_name[:-1]
                    else:
                        self.p2_name = self.p2_name[:-1]
                elif self._valid_input_character(event):
                    if self.active_input == 1 and len(self.p1_name) < MAX_NAME_LENGTH:
                        self.p1_name += event.unicode
                    elif self.active_input == 2 and len(self.p2_name) < MAX_NAME_LENGTH:
                        self.p2_name += event.unicode

    def _screen_input_top1(self, events):
        self._draw_bg()

        left_panel = pygame.Rect(80, 150, 560, 380)
        cam1_rect = pygame.Rect(700, 150, 400, 380)

        draw_arcade_panel(self.screen, left_panel, bg_color=PANEL_BG, border_color=BLACK)
        self._draw_silhouette(cam1_rect, ACCENT, self.photo_p1)
        
        t_surf = self.font_button.render("1 VS TOP #1", True, BTN_ORANGE_LIGHT)
        t_shadow = self.font_button.render("1 VS TOP #1", True, BLACK)
        t_pos = t_surf.get_rect(center=(left_panel.centerx, left_panel.y + 40))
        self.screen.blit(t_shadow, t_pos.move(2, 2))
        self.screen.blit(t_surf, t_pos)

        box_1 = self._draw_input_box("TU NOMBRE:", self.p1_name, left_panel.x + 55, left_panel.y + 105, True, ACCENT)
        
        rival_surf = self.font_button.render(f"RIVAL: {get_top1_name()}", True, BTN_YELLOW)
        r_pos = rival_surf.get_rect(center=(left_panel.centerx, left_panel.y + 245))
        self.screen.blit(rival_surf, r_pos)
        
        self._draw_status(left_panel.centerx, left_panel.y + 280)

        # VOLVER a la izquierda, DESAFIAR a la derecha
        btn_back = Button(
            left_panel.centerx - 165, left_panel.bottom - 65, 150, 45, "VOLVER", self.font_small, 
            color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER
        )
        can_play = bool(self.p1_name.strip() and self.avatar_match_p1)
        btn_play = Button(
            left_panel.centerx + 15, left_panel.bottom - 65, 150, 45, "DESAFIAR", self.font_small, 
            color=WHITE if can_play else GRAY, 
            bg=BTN_ORANGE if can_play else (40, 40, 50), 
            hover_bg=BTN_ORANGE_HOVER if can_play else (40, 40, 50)
        )
        
        mouse = pygame.mouse.get_pos()
        for button in (btn_play, btn_back):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                can_play = bool(self.p1_name.strip() and self.avatar_match_p1)
                if btn_play.clicked(mouse) and can_play:
                    self._start_match_top1()
                elif btn_back.clicked(mouse):
                    self.state = "menu"
                elif box_1.collidepoint(mouse):
                    self.active_input = 1
                elif cam1_rect.collidepoint(mouse):
                    self._open_camera(1)
            elif event.type == pygame.KEYDOWN:
                can_play = bool(self.p1_name.strip() and self.avatar_match_p1)
                if event.key == pygame.K_RETURN and can_play:
                    self._start_match_top1()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif event.key == pygame.K_BACKSPACE:
                    self.p1_name = self.p1_name[:-1]
                elif self._valid_input_character(event) and len(self.p1_name) < MAX_NAME_LENGTH:
                    self.p1_name += event.unicode

    def _draw_center_panel(self, title, subtitle="", height=350):
        self._draw_bg()
        panel = pygame.Rect(SCREEN_W // 2 - 400, SCREEN_H // 2 - (height // 2), 800, height)
        draw_arcade_panel(
            self.screen, panel,
            bg_color=PANEL_BG,
            border_color=BLACK,
            border_w=4,
            highlight_color=PANEL_BORDER_LIGHT,
            shadow_color=PANEL_BORDER_DARK
        )

        title_surface = self.font_title.render(title, True, ARCADE_GREEN)
        title_shadow = self.font_title.render(title, True, BLACK)
        t_rect = title_surface.get_rect(center=(SCREEN_W // 2, panel.top + 45))
        self.screen.blit(title_shadow, t_rect.move(3, 3))
        self.screen.blit(title_surface, t_rect)

        if subtitle:
            subtitle_surface = self.font_subtitle.render(subtitle, True, GRAY)
            self.screen.blit(subtitle_surface, subtitle_surface.get_rect(center=(SCREEN_W // 2, panel.top + 85)))

    def _screen_finished(self, events):
        self._draw_center_panel("PARTIDO TERMINADO", self.finished_mode)
        info = self.font_subtitle.render(self.status_message[:86], True, WHITE)
        self.screen.blit(info, info.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 10)))
        
        if self.score_saved:
            saved_text = "PUNTAJE ENVIADO AL RANKING"
            saved_color = NEON_CYAN
        else:
            saved_text = "PUNTAJE NO GUARDADO"
            saved_color = ACCENT_2
        saved_info = self.font_small.render(saved_text, True, saved_color)
        self.screen.blit(saved_info, saved_info.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 45)))

        btn_menu = Button(SCREEN_W // 2 - 250, SCREEN_H // 2 + 92, 220, 58, "MENU", self.font_button)
        btn_exit = Button(SCREEN_W // 2 + 30, SCREEN_H // 2 + 92, 220, 58, "SALIR", self.font_button, bg=ACCENT_2, hover_bg=(245, 55, 95))
        mouse = pygame.mouse.get_pos()
        for button in (btn_menu, btn_exit):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_menu.clicked(mouse):
                    self.state = "menu"
                elif btn_exit.clicked(mouse):
                    self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.state = "menu"

    def _screen_ranking(self, events):
        self._draw_center_panel("TOP 10 GOLEADORES", height=500)
        
        headers = self.font_small.render(f"{'RANK':<5} {'JUGADOR':<16} {'GF':<6} {'GC':<6} FECHA", True, NEON_PINK)
        self.screen.blit(headers, (SCREEN_W // 2 - 320, 185))
        pygame.draw.line(self.screen, NEON_CYAN, (SCREEN_W // 2 - 320, 210), (SCREEN_W // 2 + 320, 210), 3)

        records = get_top_ranking(10)
        y_pos = 225
        for i, (name, gf, gc, m_date, _image) in enumerate(records):
            date_str = format_db_date(m_date)
            row_text = f"#{i+1:02d}   {name.upper()[:15]:<16} {gf:<6} {gc:<6} {date_str}"
            
            color = GOLD if i == 0 else SILVER if i == 1 else BRONZE if i == 2 else NEON_CYAN
            
            row_surf = self.font_small.render(row_text, True, color)
            self.screen.blit(row_surf, (SCREEN_W // 2 - 320, y_pos))
            y_pos += 28

        btn_back = Button(SCREEN_W // 2 - 100, 520, 200, 45, "VOLVER", self.font_small, color=GRAY, bg=BTN_GRAY_BG, hover_bg=BTN_GRAY_HOVER)
        mouse = pygame.mouse.get_pos()
        btn_back.update(mouse)
        btn_back.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_back.clicked(mouse):
                    self.state = "menu"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "menu"

    def _screen_confirm_exit(self, events):
        self._draw_center_panel("CONTINUAR?", "O QUIERES SALIR DEL JUEGO?")
        btn_yes = Button(SCREEN_W // 2 - 260, SCREEN_H // 2 + 60, 220, 58, "SALIR", self.font_button, bg=ACCENT_2, hover_bg=(245, 55, 95))
        btn_no = Button(SCREEN_W // 2 + 40, SCREEN_H // 2 + 60, 220, 58, "VOLVER", self.font_button)
        mouse = pygame.mouse.get_pos()
        for button in (btn_yes, btn_no):
            button.update(mouse)
            button.draw(self.screen)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_yes.clicked(mouse):
                    self.running = False
                elif btn_no.clicked(mouse):
                    self.state = "menu"
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    self.state = "menu"
                elif event.key in (pygame.K_RETURN, pygame.K_y, pygame.K_s):
                    self.running = False

    def _run_match(
        self,
        mode_label,
        exe_name,
        player_1,
        player_2,
        player_1_image=DEFAULT_PLAYER_AVATAR,
        player_2_image=DEFAULT_PLAYER_AVATAR,
        runtime_avatar_file=None,
    ):
        try:
            write_match_players(
                player_1,
                player_2,
                player_1_image,
                player_2_image,
            )
            previous_results = snapshot_match_results()
            self.score_saved = False
            pygame.display.iconify()
            
            return_code = launch_game(exe_name, runtime_avatar_file)

            if return_code == 0:
                result = parse_match_results(
                    previous_results,
                    expected_players=(player_1, player_2),
                )
                if result is None:
                    self.status_message = "NO SE PUDO LEER EL MARCADOR FINAL"
                else:
                    g1, g2 = result["g1"], result["g2"]
                    self.match_results = (g1, g2)
                    self.status_message = f"MARCADOR FINAL: {g1} - {g2}"
                    if self.game_mode == "1v1":
                        save_score(
                            self.player_p1_id,
                            player_1,
                            "1 VS 1",
                            g1,
                            g2,
                            self.avatar_p1_id,
                            self.avatar_p1_file,
                        )
                        save_score(
                            self.player_p2_id,
                            player_2,
                            "1 VS 1",
                            g2,
                            g1,
                            self.avatar_p2_id,
                            self.avatar_p2_file,
                        )
                    elif self.game_mode == "top1":
                        save_score(
                            self.player_p1_id,
                            player_1,
                            "1 VS TOP #1",
                            g1,
                            g2,
                            self.avatar_p1_id,
                            self.avatar_p1_file,
                        )
                    self.score_saved = True
            else:
                self.status_message = f"GAME ERROR CODE: {return_code}"

            self.finished_mode = mode_label
            self.state = "finished"
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.finished_mode = mode_label
            self.status_message = str(exc)
            self.state = "finished"
        finally:
            self._restore_window()

    def _start_match_1v1(self):
        # Evita reutilizar por accidente el avatar de un participante anterior.
        if self.avatar_match_p1 is None or self.avatar_match_p2 is None:
            self.status_message = "ESCANEA EL ROSTRO DE AMBOS JUGADORES ANTES DE JUGAR"
            return

        try:
            self.avatar_p1_id, self.avatar_p1_file = archive_avatar_png(
                RUNTIME_PLAYER_AVATAR_P1
            )
            self.avatar_p2_id, self.avatar_p2_file = archive_avatar_png(
                RUNTIME_PLAYER_AVATAR_P2
            )
            self.player_p1_id = register_player_avatar(
                self.p1_name.strip(),
                self.avatar_p1_id,
                self.avatar_p1_file,
            )
            self.player_p2_id = register_player_avatar(
                self.p2_name.strip(),
                self.avatar_p2_id,
                self.avatar_p2_file,
            )
            print(f"[AVATAR] J1 guardado: {self.avatar_p1_file}")
            print(f"[AVATAR] J2 guardado: {self.avatar_p2_file}")
            print(f"[PLAYER] J1 vinculado: {self.player_p1_id}")
            print(f"[PLAYER] J2 vinculado: {self.player_p2_id}")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status_message = f"ERROR GUARDANDO AVATARES: {exc}"
            return

        self._run_match(
            "1 VS 1",
            GAME_EXE_1V1,
            self.p1_name.strip(),
            self.p2_name.strip(),
            RUNTIME_PLAYER_AVATAR_P1,
            RUNTIME_PLAYER_AVATAR_P2,
        )

    def _start_match_top1(self):
        if self.avatar_match_p1 is None:
            self.status_message = "ESCANEA TU ROSTRO ANTES DE DESAFIAR AL TOP #1"
            return

        top1 = get_top1_identity()
        if top1 is None:
            self.status_message = "TODAVÍA NO HAY UN TOP #1 EN EL RANKING"
            return
        if not top1["avatar_id"] or not top1["avatar_file"]:
            self.status_message = "EL TOP #1 TODAVÍA NO TIENE UN AVATAR VINCULADO"
            return

        opponent_name = top1["name"]
        try:
            self.avatar_p1_id, self.avatar_p1_file = archive_avatar_png(
                RUNTIME_PLAYER_AVATAR_P1
            )
            self.player_p1_id = register_player_avatar(
                self.p1_name.strip(),
                self.avatar_p1_id,
                self.avatar_p1_file,
            )
            self.player_p2_id = top1["player_id"]
            self.avatar_p2_id = top1["avatar_id"]
            self.avatar_p2_file = top1["avatar_file"]
            print(f"[PLAYER] Retador vinculado: {self.player_p1_id}")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status_message = f"ERROR VINCULANDO JUGADOR: {exc}"
            return

        self._run_match(
            "1 VS TOP #1",
            GAME_EXE_TOP1,
            self.p1_name.strip(),
            opponent_name,
            RUNTIME_PLAYER_AVATAR_P1,
            TOP1_RUNTIME_AVATAR,
            top1["avatar_file"],
        )

    def _restore_window(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Expo Heads UNO")
        pygame.event.clear()

    def run(self):
        while self.running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            if self.state == "menu":
                self._screen_menu(events)
            elif self.state == "input_1v1":
                self._screen_input_1v1(events)
            elif self.state == "input_top1":
                self._screen_input_top1(events)
            elif self.state == "camera":
                self._screen_camera(events)
            elif self.state == "finished":
                self._screen_finished(events)
            elif self.state == "ranking":
                self._screen_ranking(events)
            elif self.state == "confirm_reset":
                self._screen_confirm_reset(events)
            elif self.state == "confirm_exit":
                self._screen_confirm_exit(events)

            pygame.display.flip()
            self.clock.tick(FPS)

        self._close_camera()
        pygame.quit()


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    Launcher().run()
