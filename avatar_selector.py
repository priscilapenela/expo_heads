from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


# ============================================================
# EXPO HEADS — AVATAR SELECTOR HAIR V4
# ============================================================
#
# Objetivos de esta versión:
# - El PEINADO domina la selección.
# - No usar filtros duros que puedan eliminar el avatar correcto.
# - Hair V3: style_family, shape_family, tied, braids, bangs, etc.
# - Compatible con catálogos Hair V2 anteriores.
# - Los colores NO participan del ranking: el launcher recolorea después.
# - "None" / "unknown" = dato desconocido, NO falso.
# - Penalizaciones fuertes para contradicciones visuales importantes.
#
# La puntuación final queda normalizada a 0..100.
# ============================================================


# ------------------------------------------------------------
# PESOS GLOBALES
# ------------------------------------------------------------
# El pelo representa aproximadamente 60% de la identidad estructural.
# Anteojos + vello facial + detalles completan el resto.
BLOCK_WEIGHTS: Dict[str, float] = {
    "hair": 60.0,
    "glasses": 20.0,
    "facial_hair": 17.0,
    "freckles": 3.0,
}

# Distribución interna del bloque HAIR.
# Total = 60.
HAIR_WEIGHTS: Dict[str, float] = {
    "hair_style_family": 15.0,
    "hair_shape_family": 7.0,
    "hair_length": 9.0,
    "hair_texture": 9.0,
    "hair_tied": 6.0,
    "braid_style": 5.0,
    "braid_count": 3.0,
    "bangs": 2.0,
    "parting": 1.0,
    "face_framing": 1.0,
    "hair_volume": 2.0,
}

# Vello facial: total interno normalizado a 1 antes de multiplicar por 17.
FACIAL_HAIR_WEIGHTS: Dict[str, float] = {
    "beard": 0.50,
    "moustache": 0.25,
    "facial_hair_style": 0.25,
}

BOOLEAN_FIELDS = {
    "bald",
    "glasses",
    "beard",
    "moustache",
    "freckles",
}

UNKNOWN_VALUES = {
    "",
    "unknown",
    "desconocido",
    "n/a",
    "na",
    "?",
}

HAIR_LENGTH_ORDER = ["bald", "very_short", "short", "medium", "long"]

HAIR_TEXTURE_ALIASES = {
    "none": "none",
    "straight": "straight",
    "lacio": "straight",
    "lisa": "straight",
    "wavy": "wavy",
    "ondulado": "wavy",
    "curly": "curly",
    "rizado": "curly",
    "rulos": "curly",
    "coily": "coily",
    "afro": "coily",
    "braided": "braided",
    "braids": "braided",
    "trenzas": "braided",
    "locs": "locs",
    "dreadlocks": "locs",
    "dreads": "locs",
    "spiky": "spiky",
}

HAIR_TIED_ALIASES = {
    "none": "none",
    "loose": "none",
    "suelto": "none",
    "ponytail": "ponytail",
    "cola": "ponytail",
    "low_ponytail": "ponytail",
    "high_ponytail": "ponytail",
    "double_ponytail": "double_ponytail",
    "pigtails": "double_ponytail",
    "bun": "bun",
    "rodete": "bun",
    "moño": "bun",
    "half_up": "half_up",
    "half-up": "half_up",
    "braid": "braids",
    "braids": "braids",
    "trenzas": "braids",
    "twin_braids": "braids",
    "tied": "tied_back",
    "tied_back": "tied_back",
}

BRAID_COUNT_ALIASES = {
    "0": "none",
    "none": "none",
    "1": "single",
    "one": "single",
    "single": "single",
    "simple": "single",
    "2": "double",
    "two": "double",
    "double": "double",
    "twin": "double",
    "multiple": "multiple",
    "many": "multiple",
}

BRAID_STYLE_ALIASES = {
    "none": "none",
    "single": "single_braid",
    "single_braid": "single_braid",
    "side_braid": "side_braid",
    "double_braid": "twin_braids",
    "double_braids": "twin_braids",
    "two_braids": "twin_braids",
    "twin_braids": "twin_braids",
    "cornrow": "cornrows",
    "cornrows": "cornrows",
    "box_braids": "box_braids",
    "microbraids": "microbraids",
    "locs": "locs",
    "dreadlocks": "locs",
    "dreads": "locs",
}

PARTING_ALIASES = {
    "center": "middle",
    "centre": "middle",
    "middle": "middle",
    "medio": "middle",
    "side": "side",
    "lateral": "side",
    "none": "none",
}

BANGS_ALIASES = {
    "none": "none",
    "no": "none",
    "straight": "straight",
    "recto": "straight",
    "curtain": "curtain",
    "cortina": "curtain",
    "side": "side",
    "lateral": "side",
    "soft": "soft",
    "short": "short",
}

VOLUME_ORDER = ["low", "medium", "high"]
FRAMING_ORDER = ["light", "medium", "strong"]


@dataclass
class Candidate:
    avatar_id: str
    file: str
    score: float
    max_score: float
    confidence: float
    matched: List[str] = field(default_factory=list)
    partial: List[str] = field(default_factory=list)
    mismatched: List[str] = field(default_factory=list)
    avatar_traits: Dict[str, Any] = field(default_factory=dict)
    breakdown: Dict[str, float] = field(default_factory=dict)
    accessories: List[str] = field(default_factory=list)
    penalties: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "avatar_id": self.avatar_id,
            "file": self.file,
            "score": round(self.score, 3),
            "max_score": round(self.max_score, 3),
            "confidence": round(self.confidence, 4),
            "matched": self.matched,
            "partial": self.partial,
            "mismatched": self.mismatched,
            "traits": self.avatar_traits,
            "breakdown": {
                k: round(v, 3)
                for k, v in self.breakdown.items()
            },
            "penalties": {
                k: round(v, 3)
                for k, v in self.penalties.items()
            },
            "accessories": self.accessories,
        }


# ============================================================
# NORMALIZACIÓN
# ============================================================

def _normalize_label(value: Any) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip().lower().replace(" ", "_")
    if value in UNKNOWN_VALUES:
        return None
    return value


def _normalize_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        v = value.strip().lower()
        if v in UNKNOWN_VALUES:
            return None
        if v in {"true", "1", "yes", "si", "sí"}:
            return True
        if v in {"false", "0", "no"}:
            return False

    return None


def _normalize_length(value: Any, bald: Optional[bool] = None) -> Optional[str]:
    if bald is True:
        return "bald"

    v = _normalize_label(value)
    if v is None:
        return None

    aliases = {
        "none": "bald",
        "bald": "bald",
        "calvo": "bald",
        "very_short": "very_short",
        "veryshort": "very_short",
        "muy_corto": "very_short",
        "short": "short",
        "corto": "short",
        "medium": "medium",
        "medio": "medium",
        "long": "long",
        "largo": "long",
    }
    return aliases.get(v, v)


def _normalize_texture(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return HAIR_TEXTURE_ALIASES.get(v, v)


def _normalize_tied(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return HAIR_TIED_ALIASES.get(v, v)


def _normalize_braid_count(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return BRAID_COUNT_ALIASES.get(v, v)


def _normalize_braid_style(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return BRAID_STYLE_ALIASES.get(v, v)


def _normalize_parting(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return PARTING_ALIASES.get(v, v)


def _normalize_bangs(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return BANGS_ALIASES.get(v, v)


def _normalize_style_family(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None

    aliases = {
        "braids": "braided_long",
        "braided": "braided_long",
        "twin_braids": "braided_long",
        "cornrows": "braided_long",
        "long_loose": "long_layered",
        "dreadlocks": "locs",
        "dreads": "locs",
        "short_locs": "locs",
    }
    return aliases.get(v, v)


def _normalize_shape(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None

    aliases = {
        "long_loose": "long_layered",
        "layered_long": "long_layered",
        "twin_braid": "twin_braids",
        "braided": "braids",
        "dreadlocks": "locs",
        "dreads": "locs",
    }
    return aliases.get(v, v)


def _confidence_map(detected_traits: Dict[str, Any]) -> Dict[str, float]:
    raw = detected_traits.get("_confidence")
    if not isinstance(raw, dict):
        return {}

    out: Dict[str, float] = {}
    for key, value in raw.items():
        try:
            out[key] = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            pass
    return out


def _field_confidence(
    field: str,
    confidences: Dict[str, float],
    default: float = 1.0,
) -> float:
    if field in confidences:
        return max(0.0, min(1.0, confidences[field]))

    # Si el analizador viejo no informa confianza, preservamos compatibilidad.
    if field == "facial_hair_style":
        known = [
            confidences.get("beard"),
            confidences.get("moustache"),
        ]
        known = [x for x in known if x is not None]
        if known:
            return max(known)

    return default


# ============================================================
# FALLBACKS DEL CATÁLOGO
# ============================================================

def _candidate_trait(
    avatar: Dict[str, Any],
    field: str,
) -> Any:
    traits = avatar.get("traits", {}) or {}

    if field in traits and traits.get(field) is not None:
        return traits.get(field)

    shape = _normalize_shape(traits.get("hair_shape_family"))
    style = _normalize_style_family(traits.get("hair_style_family"))

    if field == "hair_style_family":
        if style is not None:
            return style
        mapping = {
            "braids": "braided_long",
            "twin_braids": "braided_long",
            "side_braid": "braided_long",
            "locs": "locs",
            "ponytail": "ponytail",
            "low_ponytail": "ponytail",
            "double_ponytail": "double_ponytail",
            "bun": "bun",
            "half_up": "half_up",
            "bob": "bob",
            "afro": "afro",
            "pixie": "pixie",
            "undercut": "undercut",
            "long_layered": "long_layered",
            "long_straight": "long_straight",
        }
        return mapping.get(shape, shape)

    if field == "hair_tied":
        if shape in {"ponytail", "low_ponytail"}:
            return "ponytail"
        if shape == "double_ponytail":
            return "double_ponytail"
        if shape == "bun":
            return "bun"
        if shape == "half_up":
            return "half_up"
        if shape in {"braids", "twin_braids", "side_braid"}:
            return "braids"
        if shape is not None:
            return "none"

    if field == "braid_count":
        if shape == "twin_braids":
            return "double"
        if shape == "side_braid":
            return "single"
        if shape in {"braids", "locs"}:
            return "multiple"
        if shape is not None:
            return "none"

    if field == "braid_style":
        if shape == "twin_braids":
            return "twin_braids"
        if shape == "side_braid":
            return "side_braid"
        if shape == "braids":
            return "cornrows"
        if shape == "locs":
            return "locs"
        if shape is not None:
            return "none"

    return None


# ============================================================
# SIMILITUDES
# ============================================================

def _ordinal_similarity(
    a: Any,
    b: Any,
    order: List[str],
    adjacent: float = 0.55,
) -> float:
    a = _normalize_label(a)
    b = _normalize_label(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    try:
        ia = order.index(a)
        ib = order.index(b)
    except ValueError:
        return 0.0

    dist = abs(ia - ib)
    if dist == 1:
        return adjacent
    if dist == 2:
        return 0.15
    return 0.0


def _length_similarity(a: Any, b: Any) -> float:
    a = _normalize_length(a)
    b = _normalize_length(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    try:
        ia = HAIR_LENGTH_ORDER.index(a)
        ib = HAIR_LENGTH_ORDER.index(b)
    except ValueError:
        return 0.0

    d = abs(ia - ib)
    if d == 1:
        return 0.60
    if d == 2:
        return 0.12
    return 0.0


def _texture_similarity(a: Any, b: Any) -> float:
    a = _normalize_texture(a)
    b = _normalize_texture(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    partial = {
        frozenset(("straight", "wavy")): 0.60,
        frozenset(("wavy", "curly")): 0.48,
        frozenset(("curly", "coily")): 0.70,
        frozenset(("braided", "locs")): 0.35,
    }
    return partial.get(frozenset((a, b)), 0.0)


def _style_family_similarity(a: Any, b: Any) -> float:
    a = _normalize_style_family(a)
    b = _normalize_style_family(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    partial = {
        frozenset(("long_layered", "long_wavy")): 0.82,
        frozenset(("long_layered", "long_curly")): 0.58,
        frozenset(("long_straight", "long_layered")): 0.72,
        frozenset(("long_straight", "long_wavy")): 0.55,
        frozenset(("long_wavy", "long_curly")): 0.55,
        frozenset(("medium_curly", "short_curly")): 0.45,
        frozenset(("medium_curly", "long_curly")): 0.55,
        frozenset(("short_straight", "pixie")): 0.60,
        frozenset(("short_straight", "undercut")): 0.42,
        frozenset(("bob", "layered_medium")): 0.55,
        frozenset(("ponytail", "double_ponytail")): 0.48,
        frozenset(("ponytail", "half_up")): 0.35,
        frozenset(("braided_long", "ponytail")): 0.18,
        frozenset(("braided_long", "locs")): 0.28,
        frozenset(("locs", "medium_curly")): 0.18,
    }
    return partial.get(frozenset((a, b)), 0.0)


def _shape_similarity(a: Any, b: Any) -> float:
    a = _normalize_shape(a)
    b = _normalize_shape(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    partial = {
        frozenset(("long_layered", "long_straight")): 0.72,
        frozenset(("long_layered", "ponytail")): 0.25,
        frozenset(("messy_short", "crop")): 0.55,
        frozenset(("rounded_crop", "crop")): 0.62,
        frozenset(("messy_medium", "layered_medium")): 0.62,
        frozenset(("bob", "asymmetric_bob")): 0.72,
        frozenset(("braids", "twin_braids")): 0.60,
        frozenset(("braids", "side_braid")): 0.50,
    }
    return partial.get(frozenset((a, b)), 0.0)


def _tied_similarity(a: Any, b: Any) -> float:
    a = _normalize_tied(a)
    b = _normalize_tied(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    partial = {
        frozenset(("ponytail", "double_ponytail")): 0.45,
        frozenset(("ponytail", "half_up")): 0.28,
        frozenset(("bun", "half_up")): 0.35,
        frozenset(("braids", "tied_back")): 0.25,
    }
    return partial.get(frozenset((a, b)), 0.0)


def _braid_count_similarity(a: Any, b: Any) -> float:
    a = _normalize_braid_count(a)
    b = _normalize_braid_count(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    if "none" in {a, b}:
        return 0.0

    partial = {
        frozenset(("single", "double")): 0.20,
        frozenset(("double", "multiple")): 0.45,
        frozenset(("single", "multiple")): 0.12,
    }
    return partial.get(frozenset((a, b)), 0.0)


def _braid_style_similarity(a: Any, b: Any) -> float:
    a = _normalize_braid_style(a)
    b = _normalize_braid_style(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    if "none" in {a, b}:
        return 0.0

    partial = {
        frozenset(("twin_braids", "single_braid")): 0.18,
        frozenset(("twin_braids", "side_braid")): 0.22,
        frozenset(("twin_braids", "cornrows")): 0.16,
        frozenset(("cornrows", "box_braids")): 0.48,
        frozenset(("box_braids", "microbraids")): 0.58,
        frozenset(("locs", "box_braids")): 0.22,
    }
    return partial.get(frozenset((a, b)), 0.0)


def _bangs_similarity(a: Any, b: Any) -> float:
    a = _normalize_bangs(a)
    b = _normalize_bangs(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    partial = {
        frozenset(("curtain", "side")): 0.55,
        frozenset(("curtain", "soft")): 0.72,
        frozenset(("straight", "short")): 0.60,
        frozenset(("straight", "curtain")): 0.35,
        frozenset(("side", "soft")): 0.55,
    }
    return partial.get(frozenset((a, b)), 0.0)


def _parting_similarity(a: Any, b: Any) -> float:
    a = _normalize_parting(a)
    b = _normalize_parting(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    if {a, b} == {"middle", "side"}:
        return 0.35
    return 0.0


def _facial_style_similarity(a: Any, b: Any) -> float:
    a = _normalize_label(a)
    b = _normalize_label(b)

    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    beard_family = {
        "beard",
        "short_beard",
        "full_beard",
        "goatee",
    }

    if a in beard_family and b in beard_family:
        # "beard" del analizador suele ser genérico.
        if "beard" in {a, b}:
            return 0.75
        return 0.48

    return 0.0


def _similarity(field: str, detected: Any, candidate: Any) -> float:
    if detected is None or candidate is None:
        return 0.0

    if field == "hair_length":
        return _length_similarity(detected, candidate)

    if field == "hair_texture":
        return _texture_similarity(detected, candidate)

    if field == "hair_style_family":
        return _style_family_similarity(detected, candidate)

    if field == "hair_shape_family":
        return _shape_similarity(detected, candidate)

    if field == "hair_tied":
        return _tied_similarity(detected, candidate)

    if field == "braid_count":
        return _braid_count_similarity(detected, candidate)

    if field == "braid_style":
        return _braid_style_similarity(detected, candidate)

    if field == "bangs":
        return _bangs_similarity(detected, candidate)

    if field == "parting":
        return _parting_similarity(detected, candidate)

    if field == "hair_volume":
        return _ordinal_similarity(
            detected,
            candidate,
            VOLUME_ORDER,
            adjacent=0.62,
        )

    if field == "face_framing":
        return _ordinal_similarity(
            detected,
            candidate,
            FRAMING_ORDER,
            adjacent=0.65,
        )

    if field in BOOLEAN_FIELDS:
        d = _normalize_bool(detected)
        c = _normalize_bool(candidate)
        if d is None or c is None:
            return 0.0
        return 1.0 if d == c else 0.0

    if field == "facial_hair_style":
        return _facial_style_similarity(detected, candidate)

    d = _normalize_label(detected)
    c = _normalize_label(candidate)
    if d is None or c is None:
        return 0.0
    return 1.0 if d == c else 0.0


# ============================================================
# SCORING
# ============================================================

def _active_weighted_score(
    fields: Dict[str, float],
    detected: Dict[str, Any],
    confidences: Dict[str, float],
    avatar: Dict[str, Any],
    matched: List[str],
    partial: List[str],
    mismatched: List[str],
) -> tuple[float, float]:
    """
    Devuelve:
      points, possible_points

    El peso de un rasgo se escala con la confianza del analizador.
    Si el rasgo detectado es desconocido, NO participa.
    """
    points = 0.0
    possible = 0.0

    for field, weight in fields.items():
        d = detected.get(field)
        if d is None:
            continue

        c = _candidate_trait(avatar, field)
        if c is None:
            continue

        conf = _field_confidence(field, confidences)
        if conf <= 0.0:
            continue

        # Un rasgo con baja confianza aporta poco, no se fuerza un mínimo alto.
        effective = weight * conf
        possible += effective

        sim = _similarity(field, d, c)
        points += effective * sim

        if sim >= 0.999:
            matched.append(field)
        elif sim > 0.0:
            partial.append(field)
        else:
            mismatched.append(field)

    return points, possible


def _binary_block_score(
    field: str,
    detected: Dict[str, Any],
    confidences: Dict[str, float],
    avatar: Dict[str, Any],
    block_weight: float,
    matched: List[str],
    mismatched: List[str],
) -> tuple[float, float]:
    d = detected.get(field)
    if d is None:
        return 0.0, 0.0

    c = _candidate_trait(avatar, field)
    if c is None:
        return 0.0, 0.0

    conf = _field_confidence(field, confidences)
    if conf <= 0.0:
        return 0.0, 0.0

    possible = block_weight * conf
    sim = _similarity(field, d, c)
    points = possible * sim

    if sim >= 0.999:
        matched.append(field)
    else:
        mismatched.append(field)

    return points, possible


def _compute_penalties(
    detected: Dict[str, Any],
    confidences: Dict[str, float],
    avatar: Dict[str, Any],
) -> Dict[str, float]:
    """
    Penaliza contradicciones visuales claras.

    IMPORTANTÍSIMO:
    - Las penalizaciones también se escalan por confianza.
    - Nunca se penaliza un rasgo desconocido.
    """
    p: Dict[str, float] = {}

    def conf(field: str) -> float:
        return _field_confidence(field, confidences)

    # --------------------------------------------------------
    # BALD
    # --------------------------------------------------------
    d_bald = detected.get("bald")
    c_bald = _candidate_trait(avatar, "bald")

    if d_bald is not None and c_bald is not None and conf("bald") >= 0.88:
        if _normalize_bool(d_bald) != _normalize_bool(c_bald):
            p["bald"] = 25.0 * conf("bald")

    # --------------------------------------------------------
    # LARGO
    # --------------------------------------------------------
    d_len = _normalize_length(detected.get("hair_length"))
    c_len = _normalize_length(_candidate_trait(avatar, "hair_length"))
    len_conf = conf("hair_length")

    if d_len is not None and c_len is not None and len_conf >= 0.55:
        if {d_len, c_len} == {"long", "short"}:
            p["hair_length"] = 13.0 * len_conf
        elif "bald" in {d_len, c_len} and d_len != c_len:
            p["hair_length"] = 22.0 * len_conf

    # --------------------------------------------------------
    # TEXTURA
    # --------------------------------------------------------
    d_tex = _normalize_texture(detected.get("hair_texture"))
    c_tex = _normalize_texture(_candidate_trait(avatar, "hair_texture"))
    tex_conf = conf("hair_texture")

    if d_tex is not None and c_tex is not None and tex_conf >= 0.55:
        opposite = (
            {d_tex, c_tex} in (
                {"straight", "curly"},
                {"straight", "coily"},
            )
        )
        if opposite:
            p["hair_texture"] = 13.0 * tex_conf
        elif {d_tex, c_tex} == {"wavy", "coily"}:
            p["hair_texture"] = 8.0 * tex_conf

    # --------------------------------------------------------
    # PEINADO ATADO
    # --------------------------------------------------------
    d_tied = _normalize_tied(detected.get("hair_tied"))
    c_tied = _normalize_tied(_candidate_trait(avatar, "hair_tied"))
    tied_conf = conf("hair_tied")

    if d_tied is not None and c_tied is not None and tied_conf >= 0.60:
        if d_tied == "none" and c_tied not in {"none", "tied_back"}:
            p["hair_tied"] = 8.0 * tied_conf
        elif d_tied not in {"none", "tied_back"} and c_tied != d_tied:
            p["hair_tied"] = 10.0 * tied_conf

    # --------------------------------------------------------
    # TRENZAS
    # --------------------------------------------------------
    d_braid_style = _normalize_braid_style(detected.get("braid_style"))
    c_braid_style = _normalize_braid_style(
        _candidate_trait(avatar, "braid_style")
    )
    braid_style_conf = conf("braid_style")

    if (
        d_braid_style == "twin_braids"
        and braid_style_conf >= 0.68
        and c_braid_style != "twin_braids"
    ):
        p["twin_braids"] = 15.0 * braid_style_conf

    d_braid_count = _normalize_braid_count(detected.get("braid_count"))
    c_braid_count = _normalize_braid_count(
        _candidate_trait(avatar, "braid_count")
    )
    braid_count_conf = conf("braid_count")

    if (
        d_braid_count == "double"
        and braid_count_conf >= 0.68
        and c_braid_count not in {"double", "multiple"}
    ):
        p["braid_count"] = 9.0 * braid_count_conf

    # --------------------------------------------------------
    # FLEQUILLO
    # --------------------------------------------------------
    d_bangs = _normalize_bangs(detected.get("bangs"))
    c_bangs = _normalize_bangs(_candidate_trait(avatar, "bangs"))
    bangs_conf = conf("bangs")

    if d_bangs is not None and c_bangs is not None and bangs_conf >= 0.60:
        if d_bangs != "none" and c_bangs == "none":
            p["bangs"] = 5.0 * bangs_conf
        elif d_bangs == "none" and c_bangs != "none":
            p["bangs"] = 3.0 * bangs_conf

    # --------------------------------------------------------
    # ANTEOJOS
    # --------------------------------------------------------
    d_glasses = _normalize_bool(detected.get("glasses"))
    c_glasses = _normalize_bool(_candidate_trait(avatar, "glasses"))
    glasses_conf = conf("glasses")

    if (
        d_glasses is not None
        and c_glasses is not None
        and glasses_conf >= 0.65
        and d_glasses != c_glasses
    ):
        # Falta de anteojos cuando fueron detectados es más grave que
        # agregar anteojos cuando el detector dijo que no.
        p["glasses"] = (
            12.0 if d_glasses is True else 7.0
        ) * glasses_conf

    # --------------------------------------------------------
    # BARBA / BIGOTE
    # --------------------------------------------------------
    for field, base in (("beard", 8.0), ("moustache", 5.0)):
        d = _normalize_bool(detected.get(field))
        c = _normalize_bool(_candidate_trait(avatar, field))
        field_conf = conf(field)

        if (
            d is not None
            and c is not None
            and field_conf >= 0.65
            and d != c
        ):
            p[field] = base * field_conf

    # --------------------------------------------------------
    # ACCESORIOS NO DETECTADOS
    # --------------------------------------------------------
    accessories = avatar.get("accessories") or []
    detected_accessories = detected.get("accessories") or []

    # Penalización deliberadamente pequeña: no debe destruir un buen peinado.
    if not detected_accessories and accessories:
        p["extra_accessories"] = min(4.0, 1.25 * len(accessories))

    return p


class AvatarSelector:
    def __init__(self, catalog_path: str | Path):
        self.catalog_path = Path(catalog_path)
        self.catalog = json.loads(
            self.catalog_path.read_text(encoding="utf-8")
        )

        if not isinstance(self.catalog, list):
            raise ValueError(
                "El catálogo debe ser una lista JSON en la raíz."
            )

        if not self.catalog:
            raise ValueError(
                "El catálogo de avatares está vacío."
            )

        for i, avatar in enumerate(self.catalog):
            if not isinstance(avatar, dict):
                raise ValueError(
                    f"Entrada {i} del catálogo no es un objeto."
                )
            if not avatar.get("id") or not avatar.get("file"):
                raise ValueError(
                    f"Entrada {i} sin id/file."
                )
            if not isinstance(avatar.get("traits", {}), dict):
                raise ValueError(
                    f"Entrada {avatar.get('id')} tiene traits inválido."
                )

    def _prepare_detected(
        self,
        detected_traits: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normaliza el resultado del face_analyzer.

        Los campos desconocidos se mantienen en None para que NO afecten
        al ranking.
        """
        bald = _normalize_bool(detected_traits.get("bald"))

        out: Dict[str, Any] = {
            "bald": bald,
            "hair_length": _normalize_length(
                detected_traits.get("hair_length"),
                bald,
            ),
            "hair_texture": _normalize_texture(
                detected_traits.get("hair_texture")
            ),
            "hair_style_family": _normalize_style_family(
                detected_traits.get("hair_style_family")
                or detected_traits.get("hair_shape_family")
            ),
            "hair_shape_family": _normalize_shape(
                detected_traits.get("hair_shape_family")
            ),
            "hair_volume": _normalize_label(
                detected_traits.get("hair_volume")
            ),
            "bangs": _normalize_bangs(
                detected_traits.get("bangs")
            ),
            "hair_tied": _normalize_tied(
                detected_traits.get("hair_tied")
            ),
            "braid_count": _normalize_braid_count(
                detected_traits.get("braid_count")
            ),
            "braid_style": _normalize_braid_style(
                detected_traits.get("braid_style")
            ),
            "parting": _normalize_parting(
                detected_traits.get("parting")
            ),
            "face_framing": _normalize_label(
                detected_traits.get("face_framing")
            ),
            "glasses": _normalize_bool(
                detected_traits.get("glasses")
            ),
            "beard": _normalize_bool(
                detected_traits.get("beard")
            ),
            "moustache": _normalize_bool(
                detected_traits.get("moustache")
            ),
            "facial_hair_style": _normalize_label(
                detected_traits.get("facial_hair_style")
            ),
            "freckles": _normalize_bool(
                detected_traits.get("freckles")
            ),
        }

        # ----------------------------------------------------
        # Fallbacks estructurales
        # ----------------------------------------------------
        # Si Hair V3 todavía no fue informado por el analizador,
        # derivamos algunas estructuras a partir de Hair V2.
        shape = out.get("hair_shape_family")

        if out.get("hair_tied") is None and shape is not None:
            if shape in {"ponytail", "low_ponytail"}:
                out["hair_tied"] = "ponytail"
            elif shape == "double_ponytail":
                out["hair_tied"] = "double_ponytail"
            elif shape == "bun":
                out["hair_tied"] = "bun"
            elif shape == "half_up":
                out["hair_tied"] = "half_up"
            elif shape in {"braids", "twin_braids", "side_braid"}:
                out["hair_tied"] = "braids"

        if out.get("braid_count") is None:
            if shape == "twin_braids":
                out["braid_count"] = "double"
            elif shape == "side_braid":
                out["braid_count"] = "single"

        if out.get("braid_style") is None:
            if shape == "twin_braids":
                out["braid_style"] = "twin_braids"
            elif shape == "side_braid":
                out["braid_style"] = "side_braid"

        return out

    def score_avatar(
        self,
        detected: Dict[str, Any],
        confidences: Dict[str, float],
        avatar: Dict[str, Any],
    ) -> Candidate:
        traits = avatar.get("traits", {}) or {}

        matched: List[str] = []
        partial: List[str] = []
        mismatched: List[str] = []

        breakdown = {
            "skin": 0.0,  # se conserva por compatibilidad con UI/debug viejo.
            "hair": 0.0,
            "glasses": 0.0,
            "facial_hair": 0.0,
            "freckles": 0.0,
        }

        # ----------------------------------------------------
        # HAIR
        # ----------------------------------------------------
        hair_points, hair_possible = _active_weighted_score(
            HAIR_WEIGHTS,
            detected,
            confidences,
            avatar,
            matched,
            partial,
            mismatched,
        )

        if hair_possible > 0:
            # Reescalamos el subtotal activo al bloque máximo de 60.
            hair_ratio = hair_points / hair_possible
            breakdown["hair"] = (
                BLOCK_WEIGHTS["hair"] * hair_ratio
            )

        # ----------------------------------------------------
        # GLASSES
        # ----------------------------------------------------
        glasses_points, glasses_possible = _binary_block_score(
            "glasses",
            detected,
            confidences,
            avatar,
            BLOCK_WEIGHTS["glasses"],
            matched,
            mismatched,
        )

        if glasses_possible > 0:
            breakdown["glasses"] = (
                BLOCK_WEIGHTS["glasses"]
                * (glasses_points / glasses_possible)
            )

        # ----------------------------------------------------
        # FACIAL HAIR
        # ----------------------------------------------------
        facial_points = 0.0
        facial_possible = 0.0

        for field, local_weight in FACIAL_HAIR_WEIGHTS.items():
            d = detected.get(field)
            if d is None:
                continue

            c = _candidate_trait(avatar, field)
            if c is None:
                continue

            field_conf = _field_confidence(
                field,
                confidences,
            )
            if field_conf <= 0.0:
                continue

            possible = local_weight * field_conf
            sim = _similarity(field, d, c)

            facial_points += possible * sim
            facial_possible += possible

            if sim >= 0.999:
                matched.append(field)
            elif sim > 0:
                partial.append(field)
            else:
                mismatched.append(field)

        if facial_possible > 0:
            breakdown["facial_hair"] = (
                BLOCK_WEIGHTS["facial_hair"]
                * (facial_points / facial_possible)
            )

        # ----------------------------------------------------
        # FRECKLES
        # ----------------------------------------------------
        freckles_points, freckles_possible = _binary_block_score(
            "freckles",
            detected,
            confidences,
            avatar,
            BLOCK_WEIGHTS["freckles"],
            matched,
            mismatched,
        )

        if freckles_possible > 0:
            breakdown["freckles"] = (
                BLOCK_WEIGHTS["freckles"]
                * (freckles_points / freckles_possible)
            )

        base_score = sum(breakdown.values())

        penalties = _compute_penalties(
            detected,
            confidences,
            avatar,
        )

        penalty_total = sum(penalties.values())

        # ----------------------------------------------------
        # BONUS ESTRUCTURA MUY DISTINTIVA
        # ----------------------------------------------------
        # Twin braids debe poder imponerse a coincidencias triviales.
        bonus = 0.0

        d_braid_style = _normalize_braid_style(
            detected.get("braid_style")
        )
        c_braid_style = _normalize_braid_style(
            _candidate_trait(avatar, "braid_style")
        )
        braid_conf = _field_confidence(
            "braid_style",
            confidences,
        )

        if (
            d_braid_style == "twin_braids"
            and c_braid_style == "twin_braids"
            and braid_conf >= 0.68
        ):
            bonus += 8.0 * braid_conf

        d_style = _normalize_style_family(
            detected.get("hair_style_family")
        )
        c_style = _normalize_style_family(
            _candidate_trait(avatar, "hair_style_family")
        )
        style_conf = _field_confidence(
            "hair_style_family",
            confidences,
        )

        if (
            d_style is not None
            and d_style == c_style
            and style_conf >= 0.72
        ):
            bonus += 4.0 * style_conf

        score = max(
            0.0,
            min(
                100.0,
                base_score + bonus - penalty_total,
            ),
        )

        # El launcher ya trata confidence como 0..1.
        confidence = score / 100.0

        accessories = avatar.get("accessories") or []

        return Candidate(
            avatar_id=str(avatar["id"]),
            file=str(avatar["file"]),
            score=score,
            max_score=100.0,
            confidence=confidence,
            matched=matched,
            partial=partial,
            mismatched=mismatched,
            avatar_traits=traits,
            breakdown=breakdown,
            accessories=list(accessories),
            penalties=penalties,
        )

    def rank(
        self,
        detected_traits: Dict[str, Any],
        top_k: int = 3,
    ) -> List[Candidate]:
        detected = self._prepare_detected(
            detected_traits
        )
        confidences = _confidence_map(
            detected_traits
        )

        # ----------------------------------------------------
        # SIN FILTROS DUROS
        # ----------------------------------------------------
        # Todos los avatares compiten.
        #
        # Esto evita que un único falso positivo del analizador
        # (bald, beard, glasses, etc.) elimine para siempre
        # el peinado correcto.
        candidates = [
            self.score_avatar(
                detected,
                confidences,
                avatar,
            )
            for avatar in self.catalog
        ]

        candidates.sort(
            key=lambda c: (
                c.score,
                c.breakdown.get("hair", 0.0),
                c.breakdown.get("glasses", 0.0),
                c.breakdown.get("facial_hair", 0.0),
                len(c.matched),
                -sum(c.penalties.values()),
                -len(c.accessories),
                c.avatar_id,
            ),
            reverse=True,
        )

        return candidates[:max(1, int(top_k))]

    def best_match(
        self,
        detected_traits: Dict[str, Any],
    ) -> Candidate:
        result = self.rank(
            detected_traits,
            top_k=1,
        )

        if not result:
            raise RuntimeError(
                "El catálogo no tiene candidatos disponibles."
            )

        return result[0]
