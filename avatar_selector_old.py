from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


# Expo Heads V5
# Matching estructural: el color NO participa del ranking porque se aplica
# después, desde la cámara, sobre el template seleccionado.

# CHECK AVATAR 1A
# Priorizamos la estructura visible del avatar. El color sigue fuera del
# ranking porque se aplica después mediante recolor.
FIELD_WEIGHTS: Dict[str, float] = {
    "bald": 34.0,

    # CHECK HAIR 2E:
    # El peinado deja de ser solo "un bloque importante" y pasa a actuar
    # como núcleo duro del matching. Family + length + framing + bangs deben
    # poder derrotar coincidencias más triviales como anteojos/no barba.
    "hair_length": 20.0,
    "hair_texture": 12.0,
    "hair_shape_family": 34.0,
    "hair_volume": 8.0,
    "bangs": 10.0,
    "hair_tied": 12.0,
    "parting": 5.0,
    "face_framing": 8.0,

    "glasses": 20.0,
    "beard": 20.0,
    "moustache": 9.0,
    "facial_hair_style": 5.0,
    "freckles": 2.0,
}

# Solo usamos filtro duro para rasgos cuya contradicción cambia muchísimo
# la silueta. Barba/bigote/pelo se resuelven por scoring para no encerrar
# prematuramente la búsqueda en un subconjunto incorrecto.
STRICT_ORDER = (
    "bald",
    "glasses",
)

HAIR_LENGTH_ORDER = ["bald", "very_short", "short", "medium", "long"]

HAIR_TEXTURE_EQUIVALENTS = {
    "none": "none",
    "straight": "straight",
    "lacio": "straight",
    "wavy": "wavy",
    "ondulado": "wavy",
    "curly": "curly",
    "rizado": "curly",
    "coily": "curly",
    "afro": "curly",
    "braided": "braided",
    "braids": "braided",
    "trenzas": "braided",
    "spiky": "spiky",
}


HAIR_SHAPE_EQUIVALENTS = {
    "none": "none",
    "bald": "none",
    "buzz": "buzz",
    "buzz_cut": "buzz",
    "crop": "crop",
    "short_crop": "crop",
    "side_part": "side_part",
    "sidepart": "side_part",
    "quiff": "quiff",
    "pompadour": "pompadour",
    "afro": "afro",
    "bob": "bob",
    "long_loose": "long_loose",
    "loose_long": "long_loose",
    "long_layered": "long_layered",
    "layered_long": "long_layered",
    "fringe_forward": "fringe_forward",
    "forward_fringe": "fringe_forward",
    "ponytail": "ponytail",
    "high_ponytail": "ponytail",
    "bun": "bun",
    "high_bun": "bun",
    "half_up": "half_up",
    "halfup": "half_up",
    "braids": "braids",
    "braided": "braids",
    "cornrows": "braids",
    "locs": "locs",
    "dreadlocks": "locs",
    "messy_short": "messy_short",
    "messy_medium": "messy_medium",
    "tied_back": "tied_back",
}

HAIR_VOLUME_ORDER = ["low", "medium", "high"]
FACE_FRAMING_ORDER = ["none", "light", "strong"]

BANGS_EQUIVALENTS = {
    "none": "none",
    "short": "short",
    "straight": "straight",
    "side": "side",
    "curtain": "curtain",
}

PARTING_EQUIVALENTS = {
    "none": "none",
    "center": "center",
    "centre": "center",
    "middle": "center",
    "side": "side",
}

HAIR_TIED_EQUIVALENTS = {
    "none": "none",
    "ponytail": "ponytail",
    "bun": "bun",
    "half_up": "half_up",
    "halfup": "half_up",
    "tied_back": "tied_back",
    "tied": "tied_back",
}

LEGACY_VISUAL_HAIR_STYLE_TO_FAMILY = {
    "spiky_short": "messy_short",
    "dreadlocks": "locs",
    "layered_medium": "long_layered",
    "high_ponytail": "ponytail",
    "afro": "afro",
    "bald": "none",
    "braids_cornrows": "braids",
    "shoulder_length_straight": "long_loose",
    "messy_medium": "messy_medium",
    "high_bun_ponytail": "bun",
}


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
            "breakdown": self.breakdown,
            "accessories": self.accessories,
        }


def _normalize_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "si", "sí"}:
            return True
        if v in {"false", "0", "no"}:
            return False
    return bool(value)


def _normalize_length(value: Any, bald: Optional[bool] = None) -> Optional[str]:
    if bald is True:
        return "bald"
    if value is None:
        return None
    v = str(value).strip().lower()
    aliases = {
        "none": "bald",
        "bald": "bald",
        "calvo": "bald",
        "very_short": "very_short",
        "very short": "very_short",
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
    if value is None:
        return None
    v = str(value).strip().lower()
    return HAIR_TEXTURE_EQUIVALENTS.get(v, v)


def _normalize_label(value: Any) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if v in {"", "unknown", "none_detected", "n/a", "na"}:
        return None
    return v


def _normalize_hair_shape(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return HAIR_SHAPE_EQUIVALENTS.get(v, v)


def _normalize_hair_volume(value: Any) -> Optional[str]:
    return _normalize_label(value)


def _normalize_bangs(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return BANGS_EQUIVALENTS.get(v, v)


def _normalize_parting(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return PARTING_EQUIVALENTS.get(v, v)


def _normalize_hair_tied(value: Any) -> Optional[str]:
    v = _normalize_label(value)
    if v is None:
        return None
    return HAIR_TIED_EQUIVALENTS.get(v, v)


def _normalize_face_framing(value: Any) -> Optional[str]:
    return _normalize_label(value)


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


def _field_confidence(field: str, confidences: Dict[str, float]) -> float:
    if field in confidences:
        return confidences[field]
    if field == "facial_hair_style":
        return max(confidences.get("beard", 0.0), confidences.get("moustache", 0.0), 0.7)
    # Si el analizador viejo no informa confianza, no anulamos el rasgo.
    return 1.0


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

    # Similaridad firmada:
    # medium<->long sigue siendo razonablemente parecido;
    # long<->short ya es una contradicción visual fuerte.
    distance = abs(ia - ib)
    if distance == 1:
        return 0.55
    if distance == 2:
        return -0.65
    if distance == 3:
        return -0.90
    return -1.0

def _texture_similarity(a: Any, b: Any) -> float:
    a = _normalize_texture(a)
    b = _normalize_texture(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    # La textura también usa similitud firmada. Wavy/curly son vecinos;
    # straight/curly es una contradicción fuerte.
    similarities = {
        frozenset(("wavy", "curly")): 0.55,
        frozenset(("straight", "wavy")): 0.30,
        frozenset(("straight", "curly")): -0.80,
        frozenset(("braided", "curly")): 0.20,
        frozenset(("braided", "wavy")): -0.25,
        frozenset(("braided", "straight")): -0.65,
        frozenset(("spiky", "straight")): 0.15,
        frozenset(("spiky", "wavy")): -0.35,
        frozenset(("spiky", "curly")): -0.65,
    }
    return similarities.get(frozenset((a, b)), -0.75)



def _ordered_similarity(a: Any, b: Any, order: List[str]) -> float:
    a = _normalize_label(a)
    b = _normalize_label(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    try:
        distance = abs(order.index(a) - order.index(b))
    except ValueError:
        return -0.65
    return 0.45 if distance == 1 else -0.75


def _hair_shape_similarity(a: Any, b: Any) -> float:
    a = _normalize_hair_shape(a)
    b = _normalize_hair_shape(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    partial = {
        frozenset(("long_loose", "long_layered")): 0.72,
        frozenset(("ponytail", "tied_back")): 0.58,
        frozenset(("bun", "half_up")): 0.42,
        frozenset(("ponytail", "half_up")): 0.38,
        frozenset(("crop", "messy_short")): 0.50,
        frozenset(("crop", "side_part")): 0.35,
        frozenset(("quiff", "pompadour")): 0.68,
        frozenset(("side_part", "quiff")): 0.42,
        frozenset(("braids", "locs")): 0.30,
        frozenset(("bob", "long_layered")): 0.45,
        frozenset(("bob", "long_loose")): 0.32,
        frozenset(("messy_medium", "long_layered")): 0.42,
        frozenset(("messy_medium", "long_loose")): 0.35,
        frozenset(("messy_medium", "bob")): 0.28,
    }
    pair = frozenset((a, b))
    if pair in partial:
        return partial[pair]

    tied = {"ponytail", "bun", "half_up", "tied_back"}
    loose = {"long_loose", "long_layered", "bob"}
    if (a in tied and b in loose) or (b in tied and a in loose):
        return -0.90

    if "none" in {a, b}:
        return -1.0
    if {a, b} & {"afro", "braids", "locs"}:
        return -0.80
    return -0.65


def _bangs_similarity(a: Any, b: Any) -> float:
    a = _normalize_bangs(a)
    b = _normalize_bangs(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    pair = frozenset((a, b))
    partial = {
        frozenset(("curtain", "side")): 0.55,
        frozenset(("curtain", "straight")): 0.30,
        frozenset(("short", "straight")): 0.45,
        frozenset(("short", "side")): 0.25,
    }
    if pair in partial:
        return partial[pair]
    return -0.85 if "none" in {a, b} else -0.55


def _hair_tied_similarity(a: Any, b: Any) -> float:
    a = _normalize_hair_tied(a)
    b = _normalize_hair_tied(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    if "none" in {a, b}:
        return -1.0
    partial = {
        frozenset(("ponytail", "tied_back")): 0.62,
        frozenset(("ponytail", "half_up")): 0.35,
        frozenset(("bun", "half_up")): 0.42,
        frozenset(("bun", "tied_back")): 0.25,
    }
    return partial.get(frozenset((a, b)), -0.45)


def _parting_similarity(a: Any, b: Any) -> float:
    a = _normalize_parting(a)
    b = _normalize_parting(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    return -0.45 if "none" in {a, b} else -0.50


def _candidate_trait(avatar: Dict[str, Any], field: str) -> Any:
    traits = avatar.get("traits", {}) or {}
    if traits.get(field) is not None:
        return traits.get(field)

    visual = avatar.get("visual_metadata")
    if not isinstance(visual, dict):
        visual = {}

    if field == "hair_shape_family":
        style = _normalize_label(visual.get("hair_style"))
        return LEGACY_VISUAL_HAIR_STYLE_TO_FAMILY.get(style)

    if field == "hair_tied":
        family = _candidate_trait(avatar, "hair_shape_family")
        if family in {"ponytail", "bun", "half_up", "tied_back"}:
            return family
        if family is not None:
            return "none"

    return None


def _has_hair_v2_metadata(avatar: Dict[str, Any]) -> bool:
    """
    Un avatar se considera Hair V2-ready si tiene al menos una señal fina de
    peinado además de length/texture. Esto sirve para no premiar de más un
    template con metadatos incompletos cuando el detector sí aportó detalle.
    """
    for field in (
        "hair_shape_family",
        "hair_volume",
        "bangs",
        "hair_tied",
        "parting",
        "face_framing",
    ):
        if _candidate_trait(avatar, field) is not None:
            return True
    return False


def _length_order_value(value: Any) -> Optional[int]:
    v = _normalize_length(value)
    if v is None:
        return None
    try:
        return HAIR_LENGTH_ORDER.index(v)
    except ValueError:
        return None

def _facial_hair_similarity(detected: Any, candidate: Any) -> float:
    if detected is None or candidate is None:
        return 0.0

    a = str(detected).strip().lower()
    b = str(candidate).strip().lower()

    if a == b:
        return 1.0

    # "beard" es un descriptor relativamente genérico. Una full_beard
    # sigue siendo mucho más parecida que "none".
    partials = {
        ("beard", "full_beard"): 0.75,
        ("full_beard", "beard"): 0.75,
        ("beard", "goatee"): 0.35,
        ("goatee", "beard"): 0.35,
        ("full_beard", "goatee"): 0.15,
        ("goatee", "full_beard"): 0.15,
    }
    if (a, b) in partials:
        return partials[(a, b)]

    if "none" in {a, b}:
        return -1.0
    if "moustache" in {a, b}:
        return -0.65
    return -0.50

def _similarity(field: str, detected: Any, candidate: Any) -> float:
    if detected is None or candidate is None:
        return 0.0
    if field == "hair_length":
        return _length_similarity(detected, candidate)
    if field == "hair_texture":
        return _texture_similarity(detected, candidate)
    if field == "hair_shape_family":
        return _hair_shape_similarity(detected, candidate)
    if field == "hair_volume":
        return _ordered_similarity(
            _normalize_hair_volume(detected),
            _normalize_hair_volume(candidate),
            HAIR_VOLUME_ORDER,
        )
    if field == "bangs":
        return _bangs_similarity(detected, candidate)
    if field == "hair_tied":
        return _hair_tied_similarity(detected, candidate)
    if field == "parting":
        return _parting_similarity(detected, candidate)
    if field == "face_framing":
        return _ordered_similarity(
            _normalize_face_framing(detected),
            _normalize_face_framing(candidate),
            FACE_FRAMING_ORDER,
        )
    if field == "facial_hair_style":
        return _facial_hair_similarity(detected, candidate)
    if field in {"bald", "glasses", "beard", "moustache", "freckles"}:
        return 1.0 if _normalize_bool(detected) == _normalize_bool(candidate) else -1.0
    return 1.0 if str(detected).strip().lower() == str(candidate).strip().lower() else -1.0


def _avatar_accessories(avatar: Dict[str, Any]) -> List[str]:
    """Une accesorios del esquema viejo y de visual_metadata sin duplicados."""
    out: List[str] = []

    for value in avatar.get("accessories") or []:
        value = str(value)
        if value not in out:
            out.append(value)

    visual = avatar.get("visual_metadata")
    if isinstance(visual, dict):
        for value in visual.get("accessories") or []:
            value = str(value)
            if value not in out:
                out.append(value)

    return out


class AvatarSelector:
    def __init__(self, catalog_path: str | Path):
        self.catalog_path = Path(catalog_path)
        self.catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        if not isinstance(self.catalog, list):
            raise ValueError("El catálogo debe ser una lista JSON.")

    def _prepare_detected(self, detected_traits: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key in FIELD_WEIGHTS:
            value = detected_traits.get(key)

            if key in {"bald", "glasses", "beard", "moustache", "freckles"}:
                value = _normalize_bool(value) if value is not None else None
            elif key == "hair_length":
                value = _normalize_length(
                    value,
                    _normalize_bool(detected_traits.get("bald")),
                )
            elif key == "hair_texture":
                value = _normalize_texture(value)
            elif key == "hair_shape_family":
                value = _normalize_hair_shape(value)
            elif key == "hair_volume":
                value = _normalize_hair_volume(value)
            elif key == "bangs":
                value = _normalize_bangs(value)
            elif key == "hair_tied":
                value = _normalize_hair_tied(value)
            elif key == "parting":
                value = _normalize_parting(value)
            elif key == "face_framing":
                value = _normalize_face_framing(value)

            out[key] = value
        return out

    def _strict_filter(
        self,
        detected: Dict[str, Any],
        confidences: Dict[str, float],
        avatars: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Filtro conservador.

        Solo calvicie y anteojos pueden reducir el pool de forma dura cuando
        la detección es suficientemente confiable. Pelo/barba/bigote se dejan
        al scoring para evitar el problema anterior: filtrar primero por barba
        podía eliminar todos los avatares con el peinado correcto.
        """
        remaining = avatars[:]

        for field in STRICT_ORDER:
            value = detected.get(field)
            if value is None:
                continue

            conf = _field_confidence(field, confidences)

            if field == "glasses":
                min_conf = 0.88 if value is True else 0.72
            else:  # bald
                min_conf = 0.78

            if conf < min_conf:
                continue

            compatible = [
                avatar
                for avatar in remaining
                if avatar.get("traits", {}).get(field) is not None
                and _normalize_bool(avatar.get("traits", {}).get(field)) == value
            ]

            # Fallback seguro: nunca vaciamos el catálogo.
            if compatible:
                remaining = compatible

        return remaining

    def score_avatar(
        self,
        detected: Dict[str, Any],
        confidences: Dict[str, float],
        avatar: Dict[str, Any],
    ) -> Candidate:
        traits = avatar.get("traits", {})
        score = 0.0
        max_score = 0.0
        matched: List[str] = []
        partial: List[str] = []
        mismatched: List[str] = []

        # Subtotales de UI / debug.
        breakdown = {
            "skin": 0.0,
            "hair": 0.0,
            "glasses": 0.0,
            "facial_hair": 0.0,
            "hair_shape_family": 0.0,
            "hair_length": 0.0,
            "hair_texture": 0.0,
            "hair_volume": 0.0,
            "bangs": 0.0,
            "hair_tied": 0.0,
            "parting": 0.0,
            "face_framing": 0.0,
        }

        for field, base_weight in FIELD_WEIGHTS.items():
            detected_value = detected.get(field)
            if detected_value is None:
                continue

            conf = _field_confidence(field, confidences)

            # Si el analizador explícitamente tiene poca confianza, el rasgo
            # no participa. Si no informa confianza, _field_confidence devuelve 1.
            if conf < 0.45:
                continue

            candidate_value = _candidate_trait(avatar, field)
            if candidate_value is None:
                continue

            effective_weight = base_weight * conf
            max_score += effective_weight

            sim = _similarity(field, detected_value, candidate_value)
            contribution = effective_weight * sim

            # Bald/glasses son rasgos visualmente muy notorios: una
            # contradicción confirmada recibe un pequeño castigo adicional.
            if sim < 0.0 and field in {"bald", "glasses"}:
                contribution *= 1.15

            score += contribution

            if sim >= 0.999:
                matched.append(field)
            elif sim > 0.0:
                partial.append(field)
            elif sim < 0.0:
                mismatched.append(field)

            positive = max(0.0, contribution)
            if field in breakdown:
                breakdown[field] += positive

            if field in {
                "bald",
                "hair_length",
                "hair_texture",
                "hair_shape_family",
                "hair_volume",
                "bangs",
                "hair_tied",
                "parting",
                "face_framing",
            }:
                breakdown["hair"] += positive
            elif field == "glasses":
                breakdown["glasses"] += positive
            elif field in {"beard", "moustache", "facial_hair_style"}:
                breakdown["facial_hair"] += positive

        # CHECK HAIR 2B: refuerzo específico del peinado.
        detected_family = detected.get("hair_shape_family")
        candidate_family = _candidate_trait(avatar, "hair_shape_family")
        family_conf = _field_confidence("hair_shape_family", confidences)

        if (
            detected_family is not None
            and candidate_family is not None
            and family_conf >= 0.55
        ):
            family_sim = _hair_shape_similarity(detected_family, candidate_family)
            if family_sim >= 0.999:
                score += 8.0 * family_conf
            elif family_sim <= -0.80:
                score -= 8.0 * family_conf

        detected_tied = detected.get("hair_tied")
        candidate_tied = _candidate_trait(avatar, "hair_tied")
        tied_conf = _field_confidence("hair_tied", confidences)

        if (
            detected_tied is not None
            and candidate_tied is not None
            and tied_conf >= 0.55
        ):
            if _hair_tied_similarity(detected_tied, candidate_tied) <= -0.90:
                score -= 5.0 * tied_conf

        # CHECK HAIR 2E: gating suave pero contundente del peinado.
        hair_shape_conf = _field_confidence("hair_shape_family", confidences)
        hair_length_conf = _field_confidence("hair_length", confidences)
        bangs_conf = _field_confidence("bangs", confidences)
        framing_conf = _field_confidence("face_framing", confidences)
        tied_conf = _field_confidence("hair_tied", confidences)

        detected_family = detected.get("hair_shape_family")
        candidate_family = _candidate_trait(avatar, "hair_shape_family")
        detected_length = detected.get("hair_length")
        candidate_length = _candidate_trait(avatar, "hair_length")
        detected_bangs = detected.get("bangs")
        candidate_bangs = _candidate_trait(avatar, "bangs")
        detected_framing = detected.get("face_framing")
        candidate_framing = _candidate_trait(avatar, "face_framing")
        detected_tied = detected.get("hair_tied")
        candidate_tied = _candidate_trait(avatar, "hair_tied")

        v2_ready = _has_hair_v2_metadata(avatar)

        # Si el detector aporta bastante detalle de peinado, un avatar sin
        # metadata Hair V2 queda en desventaja frente a otro igual de bueno
        # pero mejor anotado.
        detailed_hair_signal = (
            (detected_family is not None and hair_shape_conf >= 0.58)
            or (detected_bangs is not None and detected_bangs != "none" and bangs_conf >= 0.58)
            or (detected_framing is not None and detected_framing != "none" and framing_conf >= 0.60)
            or (detected_tied is not None and tied_conf >= 0.60)
        )
        if detailed_hair_signal and not v2_ready:
            score -= 10.0

        # Penalización fuerte por familia incompatible.
        if detected_family is not None and candidate_family is not None and hair_shape_conf >= 0.58:
            family_sim = _hair_shape_similarity(detected_family, candidate_family)
            if family_sim <= -0.80:
                score -= 12.0 * hair_shape_conf
            elif family_sim <= -0.60:
                score -= 7.0 * hair_shape_conf
            elif family_sim >= 0.999:
                score += 6.0 * hair_shape_conf

        # Si la silueta detectada parece suelta/encuadrando la cara, castigar
        # peinados demasiado cortos o compactos.
        loose_families = {"bob", "long_loose", "long_layered", "messy_medium"}
        compact_families = {"crop", "messy_short", "buzz", "side_part", "quiff"}
        if (
            detected_family in loose_families
            and hair_shape_conf >= 0.58
            and candidate_family in compact_families
        ):
            score -= 14.0 * hair_shape_conf

        # Gating por largo: medium/long no debería terminar en very_short/short
        # salvo que el resto de señales sea extremadamente fuerte.
        dl = _length_order_value(detected_length)
        cl = _length_order_value(candidate_length)
        if dl is not None and cl is not None and hair_length_conf >= 0.72:
            if dl >= HAIR_LENGTH_ORDER.index("medium") and cl <= HAIR_LENGTH_ORDER.index("short"):
                score -= 10.0 * hair_length_conf
            elif dl == HAIR_LENGTH_ORDER.index("long") and cl < HAIR_LENGTH_ORDER.index("medium"):
                score -= 12.0 * hair_length_conf

        # Bangs y framing son claves cuando están presentes.
        if (
            detected_bangs is not None
            and detected_bangs != "none"
            and bangs_conf >= 0.60
        ):
            if candidate_bangs is None:
                score -= 3.0
            else:
                bang_sim = _bangs_similarity(detected_bangs, candidate_bangs)
                if bang_sim <= -0.60:
                    score -= 7.0 * bangs_conf
                elif bang_sim >= 0.999:
                    score += 3.0 * bangs_conf

        if (
            detected_framing is not None
            and detected_framing == "strong"
            and framing_conf >= 0.65
        ):
            if candidate_framing is None:
                score -= 3.5
            else:
                frame_sim = _ordered_similarity(
                    _normalize_face_framing(detected_framing),
                    _normalize_face_framing(candidate_framing),
                    FACE_FRAMING_ORDER,
                )
                if frame_sim <= -0.70:
                    score -= 8.0 * framing_conf
                elif frame_sim <= 0.0:
                    score -= 5.0 * framing_conf
                elif frame_sim >= 0.999:
                    score += 3.0 * framing_conf

        # Si se detectó pelo recogido, que eso pese mucho.
        if detected_tied is not None and tied_conf >= 0.60:
            if candidate_tied is None:
                score -= 2.0
            else:
                tied_sim = _hair_tied_similarity(detected_tied, candidate_tied)
                if tied_sim <= -0.90:
                    score -= 8.0 * tied_conf
                elif tied_sim >= 0.999:
                    score += 4.0 * tied_conf

        # Si anteojos no pudieron determinarse (None o confianza muy baja),
        # preferimos levemente el template que no inventa un accesorio facial.
        glasses_conf = _field_confidence("glasses", confidences)
        glasses_unknown = detected.get("glasses") is None or glasses_conf < 0.45
        if glasses_unknown and _normalize_bool(traits.get("glasses")) is True:
            score -= 5.0

        # Preferimos templates simples cuando dos estructuras están parejas.
        # Se consideran tanto accesorios del esquema viejo como visual_metadata.
        accessories = _avatar_accessories(avatar)
        detected_accessories = detected.get("accessories") or []
        if not detected_accessories and accessories:
            score -= 5.0 * len(accessories)

        confidence = max(0.0, min(1.0, score / max_score)) if max_score > 0 else 0.0

        return Candidate(
            avatar_id=str(avatar["id"]),
            file=str(avatar["file"]),
            score=score,
            max_score=max_score,
            confidence=confidence,
            matched=matched,
            partial=partial,
            mismatched=mismatched,
            avatar_traits=traits,
            breakdown=breakdown,
            accessories=accessories,
        )

    def rank(self, detected_traits: Dict[str, Any], top_k: int = 3) -> List[Candidate]:
        prepared = self._prepare_detected(detected_traits)
        confidences = _confidence_map(detected_traits)
        pool = self._strict_filter(prepared, confidences, self.catalog)

        candidates = [
            self.score_avatar(prepared, confidences, avatar)
            for avatar in pool
        ]
        candidates.sort(
            key=lambda c: (
                c.score,
                c.confidence,
                len(c.matched),
                -len(c.accessories),
                c.avatar_id,
            ),
            reverse=True,
        )
        return candidates[:top_k]

    def best_match(self, detected_traits: Dict[str, Any]) -> Candidate:
        result = self.rank(detected_traits, top_k=1)
        if not result:
            raise RuntimeError("El catálogo no tiene candidatos disponibles.")
        return result[0]
