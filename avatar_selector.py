"""
Expo Heads — Selector de avatar predefinido
===========================================

foto/cámara
   ↓
detector de rasgos
   ↓
detected_traits
   ↓
filtro de rasgos fuertes
   ↓
ranking ponderado
   ↓
TOP 1 / TOP 3

Este módulo NO analiza la imagen.
Solo selecciona el avatar más parecido a partir de rasgos ya detectados.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


DEFAULT_WEIGHTS: Dict[str, float] = {
    "glasses": 4.0,
    "hair_length": 2.5,
    "hair_color": 2.5,
    "hair_texture": 2.0,
    "bald": 4.0,
    "beard": 3.0,
    "moustache": 2.0,
    "facial_hair_style": 1.5,
    "skin_tone": 1.5,
    "eye_color": 0.5,
    "freckles": 0.5,
    "age_group": 0.75,
    "accessory": 0.25,
}

# Estos rasgos se usan como filtro previo si existen candidatos compatibles.
DEFAULT_STRICT_FIELDS = {
    "glasses",
    "bald",
    "beard",
    "moustache",
}

ORDERS = {
    "hair_length": ["bald", "very_short", "short", "medium", "long"],
    "skin_tone": ["very_light", "light", "medium", "tan", "dark", "very_dark"],
    "age_group": ["child", "teen", "young_adult", "adult", "older_adult"],
}


@dataclass
class Candidate:
    avatar_id: str
    file: str
    score: float
    max_score: float
    confidence: float
    matched: List[str]
    partial: List[str]
    mismatched: List[str]
    avatar_traits: Dict[str, Any]

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
        }


def _ordinal_similarity(field: str, detected: Any, candidate: Any) -> float:
    order = ORDERS[field]

    try:
        a = order.index(detected)
        b = order.index(candidate)
    except ValueError:
        return 0.0

    distance = abs(a - b)

    if distance == 0:
        return 1.0
    if distance == 1:
        return 0.65
    if distance == 2:
        return 0.30
    return 0.0


def trait_similarity(field: str, detected: Any, candidate: Any) -> float:
    if detected is None or candidate is None:
        return 0.0

    if field in ORDERS:
        return _ordinal_similarity(field, detected, candidate)

    if isinstance(detected, bool) or isinstance(candidate, bool):
        return 1.0 if bool(detected) == bool(candidate) else 0.0

    return 1.0 if detected == candidate else 0.0


class AvatarSelector:
    def __init__(
        self,
        catalog_path: str | Path,
        weights: Optional[Dict[str, float]] = None,
        strict_fields: Optional[set[str]] = None,
        mismatch_penalty: float = 0.35,
    ):
        self.catalog_path = Path(catalog_path)
        self.catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))

        if not isinstance(self.catalog, list):
            raise ValueError("El catálogo debe ser una lista JSON.")

        self.weights = DEFAULT_WEIGHTS.copy()
        if weights:
            self.weights.update(weights)

        self.strict_fields = (
            set(DEFAULT_STRICT_FIELDS)
            if strict_fields is None
            else set(strict_fields)
        )

        self.mismatch_penalty = mismatch_penalty

    def _strict_filter(
        self,
        detected_traits: Dict[str, Any],
        avatars: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Aplica filtros fuertes de manera progresiva.

        Regla importante:
        solo aplica un filtro si deja al menos un candidato.
        Así nunca terminamos en cero resultados.
        """
        remaining = avatars[:]

        for field in self.strict_fields:
            if field not in detected_traits:
                continue

            value = detected_traits[field]
            if value is None:
                continue

            compatible = [
                avatar
                for avatar in remaining
                if avatar.get("traits", {}).get(field) == value
            ]

            if compatible:
                remaining = compatible

        return remaining

    def score_avatar(
        self,
        detected_traits: Dict[str, Any],
        avatar: Dict[str, Any],
    ) -> Candidate:
        avatar_traits = avatar.get("traits", {})

        score = 0.0
        max_score = 0.0

        matched = []
        partial = []
        mismatched = []

        for field, detected_value in detected_traits.items():
            if detected_value is None:
                continue

            weight = self.weights.get(field, 1.0)
            max_score += weight

            candidate_value = avatar_traits.get(field)

            if candidate_value is None:
                mismatched.append(f"{field}:sin_metadata")
                continue

            similarity = trait_similarity(field, detected_value, candidate_value)

            if similarity >= 0.999:
                score += weight
                matched.append(field)

            elif similarity > 0:
                score += weight * similarity
                partial.append(field)

            else:
                score -= weight * self.mismatch_penalty
                mismatched.append(field)

        confidence = max(0.0, score / max_score) if max_score else 0.0

        return Candidate(
            avatar_id=str(avatar["id"]),
            file=str(avatar["file"]),
            score=score,
            max_score=max_score,
            confidence=confidence,
            matched=matched,
            partial=partial,
            mismatched=mismatched,
            avatar_traits=avatar_traits,
        )

    def rank(
        self,
        detected_traits: Dict[str, Any],
        top_k: int = 3,
    ) -> List[Candidate]:
        pool = self._strict_filter(detected_traits, self.catalog)

        candidates = [
            self.score_avatar(detected_traits, avatar)
            for avatar in pool
        ]

        candidates.sort(
            key=lambda c: (
                c.score,
                len(c.matched),
                len(c.partial),
                c.avatar_id,
            ),
            reverse=True,
        )

        return candidates[:top_k]

    def best_match(self, detected_traits: Dict[str, Any]) -> Candidate:
        return self.rank(detected_traits, top_k=1)[0]


if __name__ == "__main__":
    selector = AvatarSelector("avatars_catalog.example.json")

    detected_traits = {
        "glasses": True,
        "hair_length": "short",
        "hair_color": "black",
        "hair_texture": "straight",
        "bald": False,
        "beard": False,
        "moustache": False,
        "skin_tone": "medium",
        "eye_color": "brown",
        "freckles": False,
        "age_group": "young_adult",
    }

    print("TOP 3")
    for position, result in enumerate(selector.rank(detected_traits, 3), 1):
        print(
            position,
            result.avatar_id,
            result.file,
            f"{result.confidence:.1%}",
            result.matched,
        )
