from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


# Expo Heads V5
# Matching estructural: el color NO participa del ranking porque se aplica
# después, desde la cámara, sobre el template seleccionado.

FIELD_WEIGHTS: Dict[str, float] = {
    "bald": 30.0,
    "hair_length": 26.0,
    "hair_texture": 18.0,
    "glasses": 28.0,
    "beard": 15.0,
    "moustache": 10.0,
    "facial_hair_style": 8.0,
    "freckles": 3.0,
}

# Orden determinista. Nunca usar set acá: el orden importa.
STRICT_ORDER = (
    "bald",
    "glasses",
    "beard",
    "moustache",
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
    distance = abs(ia - ib)
    if distance == 1:
        return 0.55
    if distance == 2:
        return 0.12
    return 0.0


def _texture_similarity(a: Any, b: Any) -> float:
    a = _normalize_texture(a)
    b = _normalize_texture(b)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    # Ondulado/rizado son visualmente vecinos y se admite match parcial.
    neighbors = {
        frozenset(("wavy", "curly")): 0.48,
        frozenset(("straight", "wavy")): 0.32,
    }
    return neighbors.get(frozenset((a, b)), 0.0)


def _similarity(field: str, detected: Any, candidate: Any) -> float:
    if detected is None or candidate is None:
        return 0.0
    if field == "hair_length":
        return _length_similarity(detected, candidate)
    if field == "hair_texture":
        return _texture_similarity(detected, candidate)
    if field in {"bald", "glasses", "beard", "moustache", "freckles"}:
        return 1.0 if _normalize_bool(detected) == _normalize_bool(candidate) else 0.0
    return 1.0 if str(detected).strip().lower() == str(candidate).strip().lower() else 0.0


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
                value = _normalize_length(value, _normalize_bool(detected_traits.get("bald")))
            elif key == "hair_texture":
                value = _normalize_texture(value)
            out[key] = value
        return out

    def _strict_filter(
        self,
        detected: Dict[str, Any],
        confidences: Dict[str, float],
        avatars: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        remaining = avatars[:]

        for field in STRICT_ORDER:
            value = detected.get(field)
            if value is None:
                continue

            conf = _field_confidence(field, confidences)

            # Anteojos y calvicie son rasgos visuales muy fuertes.
            # Con el analizador V4, un FALSE de anteojos con alta confianza
            # debe excluir templates con anteojos si hay alternativas.
            if field == "glasses":
                min_conf = 0.88 if value is True else 0.72
            elif field == "bald":
                min_conf = 0.78
            else:
                min_conf = 0.68

            if conf < min_conf:
                continue

            compatible = [
                avatar
                for avatar in remaining
                if avatar.get("traits", {}).get(field) is not None
                and _normalize_bool(avatar.get("traits", {}).get(field)) == value
            ]

            if compatible:
                remaining = compatible

        # Segundo filtro: peinado. Solo lo hacemos cuando el analizador está
        # suficientemente seguro y siempre con fallback si el catálogo no
        # posee esa combinación exacta. Textura va primero: visualmente es más
        # importante que confundir medium con short por unos pocos píxeles.
        texture = detected.get("hair_texture")
        texture_conf = _field_confidence("hair_texture", confidences)
        if texture not in (None, "none") and texture_conf >= 0.66:
            compatible = [
                avatar for avatar in remaining
                if _normalize_texture(avatar.get("traits", {}).get("hair_texture")) == texture
            ]
            if compatible:
                remaining = compatible

        length = detected.get("hair_length")
        length_conf = _field_confidence("hair_length", confidences)
        if length not in (None, "bald") and length_conf >= 0.74:
            compatible = [
                avatar for avatar in remaining
                if _normalize_length(avatar.get("traits", {}).get("hair_length")) == length
            ]
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

        # Subtotales de UI / debug
        breakdown = {"skin": 0.0, "hair": 0.0, "glasses": 0.0, "facial_hair": 0.0}

        for field, base_weight in FIELD_WEIGHTS.items():
            detected_value = detected.get(field)
            if detected_value is None:
                continue

            conf = _field_confidence(field, confidences)
            if conf <= 0.0:
                continue

            # Evita que una inferencia floja domine el ranking.
            effective_weight = base_weight * max(0.22, conf)
            candidate_value = traits.get(field)
            if candidate_value is None:
                continue

            max_score += effective_weight
            sim = _similarity(field, detected_value, candidate_value)

            if sim >= 0.999:
                score += effective_weight
                matched.append(field)
            elif sim > 0.0:
                score += effective_weight * sim
                partial.append(field)
            else:
                # Los booleanos visualmente fuertes reciben penalización alta.
                penalty_mult = 1.25 if field in {"glasses", "bald"} else 0.82
                score -= effective_weight * penalty_mult
                mismatched.append(field)

            contribution = max(0.0, effective_weight * sim)
            if field in {"bald", "hair_length", "hair_texture"}:
                breakdown["hair"] += contribution
            elif field == "glasses":
                breakdown["glasses"] += contribution
            elif field in {"beard", "moustache", "facial_hair_style"}:
                breakdown["facial_hair"] += contribution

        # Preferimos un template simple cuando dos estructuras empatan. Un
        # accesorio no detectado (coleta/piercing/etc.) no debería ganar por azar.
        accessories = avatar.get("accessories") or []
        detected_accessories = detected.get("accessories") or []
        if not detected_accessories and accessories:
            score -= 12.0 * len(accessories)

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
            accessories=list(accessories),
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
