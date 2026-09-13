
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import json


PRIORITY_WEIGHTS = {
    "skin": 40.0,
    "hair": 30.0,
    "glasses": 20.0,
    "facial_hair": 10.0,
}

HAIR_FIELD_WEIGHTS = {
    "hair_length": 0.40,
    "hair_color": 0.35,
    "bald": 0.15,
    "hair_texture": 0.10,
}

FACIAL_HAIR_FIELD_WEIGHTS = {
    "beard": 0.60,
    "moustache": 0.25,
    "facial_hair_style": 0.15,
}

ORDERS = {
    "skin_tone": ["very_light", "light", "medium", "tan", "dark", "very_dark"],
    "hair_length": ["bald", "very_short", "short", "medium", "long"],
}

HAIR_COLOR_SIMILARITY = {
    frozenset(("black", "dark_brown")): 0.70,
    frozenset(("dark_brown", "brown")): 0.80,
    frozenset(("brown", "red")): 0.25,
    frozenset(("blond", "gray")): 0.25,
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
    breakdown: Dict[str, float]

    def as_dict(self):
        return {
            "avatar_id": self.avatar_id,
            "file": self.file,
            "score": round(self.score, 3),
            "max_score": round(self.max_score, 3),
            "confidence": round(self.confidence, 4),
            "matched": self.matched,
            "partial": self.partial,
            "mismatched": self.mismatched,
            "breakdown": {
                k: round(v, 3)
                for k, v in self.breakdown.items()
            },
            "traits": self.avatar_traits,
        }


def _ordinal_similarity(field: str, detected: Any, candidate: Any) -> float:
    order = ORDERS[field]
    try:
        a = order.index(detected)
        b = order.index(candidate)
    except ValueError:
        return 0.0

    d = abs(a - b)

    if d == 0:
        return 1.0
    if d == 1:
        return 0.55
    if d == 2:
        return 0.15
    return 0.0


def trait_similarity(field: str, detected: Any, candidate: Any) -> float:
    if detected is None or candidate is None:
        return 0.0

    if field in ORDERS:
        return _ordinal_similarity(field, detected, candidate)

    if field == "hair_color":
        if detected == candidate:
            return 1.0

        return HAIR_COLOR_SIMILARITY.get(
            frozenset((str(detected), str(candidate))),
            0.0
        )

    if isinstance(detected, bool) or isinstance(candidate, bool):
        return 1.0 if bool(detected) == bool(candidate) else 0.0

    return 1.0 if detected == candidate else 0.0


def _group_similarity(
    detected_traits: Dict[str, Any],
    candidate_traits: Dict[str, Any],
    fields: Dict[str, float],
):
    """
    Promedio ponderado de los campos disponibles.

    Si un campo detectado es None, no penaliza.
    El peso interno se redistribuye entre los campos disponibles.
    """
    total_internal_weight = 0.0
    accumulated = 0.0
    compared_fields = []

    for field, internal_weight in fields.items():
        detected_value = detected_traits.get(field)
        candidate_value = candidate_traits.get(field)

        if detected_value is None or candidate_value is None:
            continue

        total_internal_weight += internal_weight
        similarity = trait_similarity(
            field,
            detected_value,
            candidate_value,
        )

        accumulated += internal_weight * similarity
        compared_fields.append((field, similarity))

    if total_internal_weight <= 0:
        return None, compared_fields

    return accumulated / total_internal_weight, compared_fields


class AvatarSelector:
    """
    V3 - prioridades explícitas por grupo:

    1) tono de piel = 40%
    2) pelo = 30%
    3) anteojos = 20%
    4) barba/bigote = 10%

    Esto evita que muchos rasgos secundarios juntos
    terminen dominando un rasgo prioritario.
    """

    def __init__(self, catalog_path: str | Path):
        self.catalog_path = Path(catalog_path)
        self.catalog = json.loads(
            self.catalog_path.read_text(encoding="utf-8")
        )

        if not isinstance(self.catalog, list):
            raise ValueError("El catálogo debe ser una lista JSON.")

    def score_avatar(self, detected_traits, avatar):
        candidate_traits = avatar.get("traits", {})

        score = 0.0
        max_score = 0.0

        matched = []
        partial = []
        mismatched = []

        breakdown = {
            "skin": 0.0,
            "hair": 0.0,
            "glasses": 0.0,
            "facial_hair": 0.0,
        }

        # --------------------------------------------------
        # 1) PIEL - 40 puntos
        # --------------------------------------------------
        detected_skin = detected_traits.get("skin_tone")
        candidate_skin = candidate_traits.get("skin_tone")

        if detected_skin is not None and candidate_skin is not None:
            sim = trait_similarity(
                "skin_tone",
                detected_skin,
                candidate_skin,
            )

            group_score = PRIORITY_WEIGHTS["skin"] * sim
            score += group_score
            max_score += PRIORITY_WEIGHTS["skin"]
            breakdown["skin"] = group_score

            if sim >= 0.999:
                matched.append("skin_tone")
            elif sim > 0:
                partial.append("skin_tone")
            else:
                mismatched.append("skin_tone")

        # --------------------------------------------------
        # 2) PELO - 30 puntos
        # --------------------------------------------------
        hair_sim, hair_fields = _group_similarity(
            detected_traits,
            candidate_traits,
            HAIR_FIELD_WEIGHTS,
        )

        if hair_sim is not None:
            group_score = PRIORITY_WEIGHTS["hair"] * hair_sim
            score += group_score
            max_score += PRIORITY_WEIGHTS["hair"]
            breakdown["hair"] = group_score

            for field, sim in hair_fields:
                if sim >= 0.999:
                    matched.append(field)
                elif sim > 0:
                    partial.append(field)
                else:
                    mismatched.append(field)

        # --------------------------------------------------
        # 3) ANTEOJOS - 20 puntos
        # --------------------------------------------------
        detected_glasses = detected_traits.get("glasses")
        candidate_glasses = candidate_traits.get("glasses")

        if detected_glasses is not None and candidate_glasses is not None:
            sim = trait_similarity(
                "glasses",
                detected_glasses,
                candidate_glasses,
            )

            group_score = PRIORITY_WEIGHTS["glasses"] * sim
            score += group_score
            max_score += PRIORITY_WEIGHTS["glasses"]
            breakdown["glasses"] = group_score

            if sim >= 0.999:
                matched.append("glasses")
            else:
                mismatched.append("glasses")

        # --------------------------------------------------
        # 4) BARBA/BIGOTE - 10 puntos
        # --------------------------------------------------
        facial_sim, facial_fields = _group_similarity(
            detected_traits,
            candidate_traits,
            FACIAL_HAIR_FIELD_WEIGHTS,
        )

        if facial_sim is not None:
            group_score = (
                PRIORITY_WEIGHTS["facial_hair"] *
                facial_sim
            )

            score += group_score
            max_score += PRIORITY_WEIGHTS["facial_hair"]
            breakdown["facial_hair"] = group_score

            for field, sim in facial_fields:
                if sim >= 0.999:
                    matched.append(field)
                elif sim > 0:
                    partial.append(field)
                else:
                    mismatched.append(field)

        confidence = (
            max(0.0, min(1.0, score / max_score))
            if max_score > 0
            else 0.0
        )

        return Candidate(
            avatar_id=str(avatar["id"]),
            file=str(avatar["file"]),
            score=score,
            max_score=max_score,
            confidence=confidence,
            matched=matched,
            partial=partial,
            mismatched=mismatched,
            avatar_traits=candidate_traits,
            breakdown=breakdown,
        )

    def rank(self, detected_traits, top_k=3):
        candidates = [
            self.score_avatar(detected_traits, avatar)
            for avatar in self.catalog
        ]

        candidates.sort(
            key=lambda c: (
                c.score,
                c.breakdown["skin"],
                c.breakdown["hair"],
                c.breakdown["glasses"],
                c.breakdown["facial_hair"],
                c.avatar_id,
            ),
            reverse=True,
        )

        return candidates[:top_k]

    def best_match(self, detected_traits):
        return self.rank(detected_traits, 1)[0]
