"""Constructor modular y determinista de cabezones para Expo Heads.

Dibuja en una grilla lógica de 96x112 píxeles y escala únicamente con
vecino más cercano. No toca los EXE ni ningún archivo interno del juego.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from PIL import Image, ImageDraw


LOGICAL_SIZE = (96, 112)
DEFAULT_SCALE = 2

SKIN_TONES = {
    "skin_01_porcelain": (255, 211, 174),
    "skin_02_fair": (250, 190, 145),
    "skin_03_light": (235, 164, 116),
    "skin_04_warm": (216, 142, 92),
    "skin_05_olive": (190, 126, 82),
    "skin_06_tan": (165, 101, 63),
    "skin_07_brown": (133, 76, 48),
    "skin_08_deep": (104, 57, 39),
    "skin_09_dark": (78, 43, 32),
    "skin_10_ebony": (57, 32, 27),
}

HAIR_COLORS = {
    "hair_color_01_black": (30, 23, 24),
    "hair_color_02_soft_black": (49, 38, 37),
    "hair_color_03_dark_brown": (68, 42, 31),
    "hair_color_04_brown": (101, 59, 38),
    "hair_color_05_chestnut": (126, 69, 38),
    "hair_color_06_light_brown": (154, 103, 62),
    "hair_color_07_dark_blond": (170, 128, 70),
    "hair_color_08_blond": (218, 175, 94),
    "hair_color_09_light_blond": (244, 214, 143),
    "hair_color_10_auburn": (154, 61, 32),
    "hair_color_11_copper": (199, 78, 34),
    "hair_color_12_gray": (132, 131, 137),
    "hair_color_13_silver": (193, 190, 193),
    "hair_color_14_blue": (42, 75, 139),
    "hair_color_15_violet": (102, 55, 128),
    "hair_color_16_rose": (163, 77, 104),
}

IRIS_COLORS = {
    "iris_01_near_black": (32, 23, 20),
    "iris_02_dark_brown": (59, 37, 26),
    "iris_03_medium_brown": (106, 62, 40),
    "iris_04_honey": (154, 106, 47),
    "iris_05_hazel": (123, 113, 55),
    "iris_06_amber": (180, 122, 40),
    "iris_07_green": (79, 123, 69),
    "iris_08_gray_green": (102, 122, 101),
    "iris_09_blue": (62, 120, 168),
    "iris_10_gray_blue": (111, 135, 150),
}

FRAME_COLORS = {
    "frame_black": (24, 24, 27),
    "frame_graphite": (66, 69, 76),
    "frame_brown": (90, 53, 35),
    "frame_tortoise": (129, 72, 31),
    "frame_blue": (34, 77, 145),
    "frame_cyan": (29, 150, 180),
    "frame_red": (160, 42, 45),
    "frame_burgundy": (104, 31, 48),
    "frame_violet": (105, 52, 137),
    "frame_pink": (190, 73, 116),
    "frame_green": (52, 117, 72),
    "frame_gold": (198, 148, 41),
    "frame_silver": (176, 184, 194),
}

FACE_SHAPES = [f"face_{i:02d}" for i in range(1, 11)]
EYE_STYLES = [f"eyes_{i:02d}" for i in range(1, 11)]
EYEBROW_STYLES = [f"brows_{i:02d}" for i in range(1, 13)]
NOSE_STYLES = [f"nose_{i:02d}" for i in range(1, 13)]
MOUTH_STYLES = [f"mouth_{i:02d}" for i in range(1, 13)]
EAR_STYLES = [f"ear_{i:02d}" for i in range(1, 11)]
DETAIL_STYLES = ["detail_00_none"] + [f"detail_{i:02d}" for i in range(1, 10)]
HAIR_STYLES = [f"hair_{i:02d}" for i in range(1, 41)]
GLASSES_STYLES = ["glasses_00_none"] + [f"glasses_{i:02d}" for i in range(1, 20)]
FACIAL_HAIR_STYLES = ["facial_hair_00_none"] + [f"facial_hair_{i:02d}" for i in range(1, 21)]
ACCESSORY_STYLES = ["accessory_00_none"] + [f"accessory_{i:02d}" for i in range(1, 16)]

CATALOG = {
    "face_shape": FACE_SHAPES,
    "skin_tone": list(SKIN_TONES),
    "eye_style": EYE_STYLES,
    "iris_color": list(IRIS_COLORS),
    "eyebrow_style": EYEBROW_STYLES,
    "nose_style": NOSE_STYLES,
    "mouth_style": MOUTH_STYLES,
    "ear_style": EAR_STYLES,
    "detail_style": DETAIL_STYLES,
    "hair_style": HAIR_STYLES,
    "hair_color": list(HAIR_COLORS),
    "glasses_style": GLASSES_STYLES,
    "frame_color": list(FRAME_COLORS),
    "facial_hair_style": FACIAL_HAIR_STYLES,
    "accessory_style": ACCESSORY_STYLES,
    "facing": ["right", "left"],
}


@dataclass(frozen=True)
class AvatarConfig:
    face_shape: str = "face_01"
    skin_tone: str = "skin_03_light"
    eye_style: str = "eyes_01"
    iris_color: str = "iris_03_medium_brown"
    eyebrow_style: str = "brows_03"
    nose_style: str = "nose_01"
    mouth_style: str = "mouth_02"
    ear_style: str = "ear_01"
    detail_style: str = "detail_00_none"
    hair_style: str = "hair_03"
    hair_color: str = "hair_color_03_dark_brown"
    glasses_style: str = "glasses_00_none"
    frame_color: str = "frame_black"
    facial_hair_style: str = "facial_hair_00_none"
    accessory_style: str = "accessory_00_none"
    facing: str = "right"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AvatarConfig":
        unknown = sorted(set(data) - set(cls.__dataclass_fields__))
        if unknown:
            raise ValueError(f"Campos de avatar desconocidos: {', '.join(unknown)}")
        config = cls(**data)
        validate_config(config)
        return config

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def validate_config(config: AvatarConfig) -> None:
    for field, allowed in CATALOG.items():
        value = getattr(config, field)
        if value not in allowed:
            raise ValueError(f"{field}={value!r} no existe en el catálogo")


def _mix(color: tuple[int, int, int], target: tuple[int, int, int], amount: float):
    return tuple(round(a + (b - a) * amount) for a, b in zip(color, target))


def _outline(draw: ImageDraw.ImageDraw, xy, fill, width=2):
    draw.polygon(xy, fill=fill, outline=(18, 15, 18), width=width)


def _face_polygon(style: int):
    variants = [
        [(28, 15), (68, 13), (82, 27), (84, 66), (76, 91), (58, 101), (36, 98), (22, 82), (18, 43)],
        [(31, 13), (67, 14), (80, 28), (83, 66), (73, 94), (52, 102), (31, 95), (20, 74), (20, 38)],
        [(25, 18), (69, 13), (84, 31), (82, 75), (68, 98), (39, 101), (20, 78), (18, 39)],
        [(34, 12), (66, 14), (80, 25), (84, 67), (73, 91), (59, 102), (38, 98), (23, 82), (19, 41)],
        [(24, 17), (69, 15), (84, 30), (85, 69), (74, 95), (49, 102), (27, 91), (17, 69), (18, 38)],
        [(29, 12), (64, 13), (79, 23), (84, 60), (79, 83), (62, 99), (40, 101), (23, 87), (17, 51), (20, 28)],
        [(26, 13), (71, 14), (84, 28), (84, 71), (71, 96), (49, 102), (29, 94), (18, 72), (18, 36)],
        [(30, 15), (67, 12), (82, 26), (85, 62), (78, 84), (64, 98), (42, 101), (25, 88), (18, 58), (20, 31)],
        [(23, 19), (70, 14), (85, 31), (83, 72), (67, 98), (40, 100), (20, 80), (17, 39)],
        [(32, 12), (64, 12), (79, 20), (85, 57), (80, 81), (61, 100), (38, 100), (21, 84), (17, 48), (21, 25)],
    ]
    points = variants[(style - 1) % len(variants)]
    # Las plantillas aprobadas son cabezonas, redondeadas y algo más anchas
    # que un rostro humano real. La transformación conserva las variantes.
    return [
        (round(50 + (x - 50) * 1.13), round(56 + (y - 56) * 0.94))
        for x, y in points
    ]


def _draw_back_hair(draw, style, color, shadow):
    long_styles = set(range(21, 41)) | {10, 18, 20}
    if style not in long_styles:
        return
    if style in {25, 26, 34, 40}:
        draw.ellipse((2, 42, 25, 83), fill=shadow, outline=(18, 15, 18), width=2)
        draw.polygon([(10, 62), (20, 58), (22, 103), (8, 107)], fill=color, outline=(18, 15, 18))
    elif style in {27, 28, 29, 37}:
        y = 7 if style in {27, 29} else 42
        draw.ellipse((6, y, 31, y + 25), fill=shadow, outline=(18, 15, 18), width=2)
        if style == 29:
            draw.ellipse((64, 9, 88, 33), fill=color, outline=(18, 15, 18), width=2)
    elif style in {30, 31, 32, 33, 39}:
        count = 2 if style in {31, 33} else 1
        for i in range(count):
            x = 8 + i * 58
            for y in range(50, 105, 8):
                draw.ellipse((x, y, x + 10, y + 12), fill=color, outline=shadow)
    else:
        draw.polygon(
            [(16, 20), (70, 15), (83, 37), (82, 108), (64, 109), (60, 76),
             (31, 76), (28, 110), (12, 109), (12, 39)],
            fill=shadow, outline=(18, 15, 18),
        )


def _draw_neck(draw, skin, shadow):
    draw.polygon([(37, 86), (63, 86), (65, 111), (33, 111)], fill=(18, 15, 18))
    draw.polygon([(40, 87), (60, 87), (61, 110), (37, 110)], fill=skin)
    draw.polygon([(40, 96), (60, 91), (60, 99), (40, 103)], fill=shadow)


def _draw_ear(draw, style, skin, shadow, highlight):
    heights = [20, 23, 25, 27, 21, 24, 26, 20, 24, 22]
    h = heights[(style - 1) % 10]
    box = (5, 51 - h // 2, 27, 51 + h // 2)
    draw.ellipse(box, fill=(18, 15, 18))
    draw.ellipse((box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2), fill=skin)
    draw.line([(16, 47), (21, 51), (16, 56), (16, 51), (20, 51)], fill=shadow, width=2)
    if style in {3, 6, 9}:
        draw.point((13, 44), fill=highlight)


def _draw_face(draw, style, skin, shadow, highlight):
    poly = _face_polygon(style)
    _outline(draw, poly, skin)
    draw.polygon([(67, 16), (79, 28), (82, 66), (75, 87), (64, 96),
                  (64, 88), (74, 77), (77, 30)], fill=shadow)
    draw.polygon([(31, 19), (47, 16), (41, 20), (31, 25), (25, 37), (23, 30)], fill=highlight)


def _draw_hair(draw, style, color, shadow, highlight):
    # Base superior. Las variaciones se construyen con píxeles/polígonos simples.
    if style == 1:  # crop
        draw.polygon([(20, 35), (24, 18), (37, 10), (68, 11), (80, 24), (79, 37), (65, 29), (43, 27)], fill=color, outline=(18, 15, 18))
    elif style == 2:  # buzz
        draw.polygon([(20, 34), (25, 18), (42, 12), (69, 15), (79, 28), (78, 35)], fill=shadow, outline=(18, 15, 18))
        for x in range(28, 73, 5):
            draw.point((x, 20 + (x % 3)), fill=highlight)
    elif style in {4, 13, 14, 15}:  # spiky/quiff/faux hawk/messy
        pts = [(19, 36), (22, 22), (28, 24), (31, 8), (38, 17), (44, 5), (50, 16),
               (58, 4), (62, 18), (73, 9), (71, 22), (82, 20), (77, 39), (59, 28), (38, 31)]
        draw.polygon(pts, fill=color, outline=(18, 15, 18))
    elif style in {5, 6, 7}:  # curls/coils/afro
        radius = 8 if style == 7 else 6
        for x, y in [(22,29),(25,20),(34,14),(45,11),(57,12),(68,16),(76,24),(72,33),(61,29),(49,27),(37,29)]:
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color, outline=(18,15,18))
            draw.point((x-2, y-2), fill=highlight)
    elif style == 8:  # undercut
        draw.polygon([(20, 38), (24, 22), (38, 12), (74, 10), (82, 24), (77, 35), (52, 25), (35, 33)], fill=color, outline=(18,15,18))
        draw.rectangle((19, 31, 38, 38), fill=shadow)
        for y in range(32, 38, 3):
            draw.line((22, y, 36, y), fill=highlight)
    elif style in {9, 19, 20, 38}:  # bowl/fringes
        draw.polygon([(18, 39), (22, 20), (37, 10), (69, 12), (82, 28), (79, 43),
                      (70, 35), (65, 47), (57, 36), (49, 48), (41, 36), (32, 45), (26, 35)],
                     fill=color, outline=(18,15,18))
    elif style in {10, 18, 21, 22, 23, 24, 35, 36}:  # bobs/long
        draw.polygon([(16, 44), (20, 22), (34, 11), (68, 12), (82, 30), (82, 75),
                      (72, 91), (68, 50), (62, 33), (42, 30), (28, 42), (27, 91), (14, 89)],
                     fill=color, outline=(18,15,18))
        if style in {22, 23, 24}:
            for x in (19, 29, 70, 78):
                for y in range(45, 91, 10):
                    draw.ellipse((x-4, y-4, x+5, y+6), fill=color, outline=shadow)
    elif style in {25, 26, 27, 28, 29, 37, 40}:  # tied/buns
        draw.polygon([(19, 39), (22, 21), (38, 11), (67, 13), (80, 28), (76, 39),
                      (62, 27), (43, 29), (28, 39)], fill=color, outline=(18,15,18))
        draw.line((27, 25, 67, 20), fill=highlight, width=2)
        if style in {40}:
            draw.polygon([(39, 21), (48, 48), (57, 22), (65, 45), (72, 25)], fill=color)
    elif style in {30, 31, 32, 33, 34, 39}:  # braided/cornrow
        draw.polygon([(19, 39), (22, 23), (36, 12), (68, 13), (80, 30), (75, 39), (61, 27), (39, 28), (27, 39)], fill=shadow, outline=(18,15,18))
        for x in range(27, 72, 8):
            draw.line((x, 18, x+9, 31), fill=highlight, width=2)
        if style == 39:
            for x in range(35, 70, 8):
                draw.ellipse((x, 30, x+7, 41), fill=color, outline=shadow)
    else:  # side part, waves, slick, pixie
        draw.polygon([(19, 39), (22, 22), (36, 11), (70, 12), (82, 28), (77, 39),
                      (66, 31), (53, 25), (42, 31), (29, 37)], fill=color, outline=(18,15,18))
        draw.line((43, 14, 35, 31), fill=highlight, width=2)

    # Textura visual, sin suavizado.
    if style not in {2, 5, 6, 7, 23, 24, 30, 31, 32, 33, 34, 39}:
        draw.line((34, 18, 29, 31), fill=highlight, width=2)
        draw.line((48, 14, 43, 27), fill=shadow, width=2)


def _draw_eyes(draw, style, iris):
    y = 52
    if style == 9:
        draw.line((45, y+3, 54, y+3), fill=(18,15,18), width=2)
        draw.line((66, y+2, 75, y+2), fill=(18,15,18), width=2)
        return
    if style == 10:
        draw.arc((44, y, 55, y+7), 10, 170, fill=(18,15,18), width=2)
        draw.arc((65, y-1, 76, y+6), 10, 170, fill=(18,15,18), width=2)
        return
    h = 7 if style in {2, 5} else 6
    w = 9 if style not in {4, 6} else 8
    for x, offset in ((45, 1), (66, 0)):
        box = (x, y + offset, x + w, y + offset + h)
        draw.rectangle(box, fill=(18, 15, 18))
        draw.rectangle((box[0]+2, box[1]+2, box[2]-1, box[3]-1), fill=(248, 241, 222))
        pupil_x = box[0] + (5 if x == 45 else 4)
        draw.rectangle((pupil_x, box[1]+2, pupil_x+2, box[3]-1), fill=iris)
        draw.point((pupil_x+1, box[1]+3), fill=(12, 12, 14))
    if style in {3, 7}:
        draw.line((44, y+1, 54, y-1), fill=(18,15,18), width=1)
        draw.line((65, y, 75, y-2), fill=(18,15,18), width=1)
    elif style == 8:
        draw.line((44, y, 54, y+2), fill=(18,15,18), width=1)
        draw.line((65, y-1, 75, y+1), fill=(18,15,18), width=1)


def _draw_brows(draw, style, hair):
    c = _mix(hair, (0, 0, 0), 0.3)
    width = 1 if style in {1, 3, 8} else 2
    left = [(44, 47), (54, 46)]
    right = [(65, 46), (76, 45)]
    if style in {3, 4, 7}:
        left = [(44, 47), (49, 44), (55, 46)]
        right = [(65, 46), (70, 43), (76, 45)]
    elif style in {5, 9}:
        left = [(44, 45), (55, 48)]
        right = [(65, 44), (76, 47)]
    elif style in {6, 10}:
        left = [(44, 48), (49, 44), (56, 43)]
        right = [(65, 47), (70, 43), (77, 42)]
    if style == 8:
        left[-1] = (52, left[-1][1])
        right[-1] = (73, right[-1][1])
    if style == 12:
        draw.line((44, 47, 49, 46), fill=c, width=2)
        draw.line((52, 46, 56, 45), fill=c, width=2)
        draw.line(right, fill=c, width=2)
        return
    draw.line(left, fill=c, width=width)
    draw.line(right, fill=c, width=width)


def _draw_nose(draw, style, shadow, highlight):
    x = 63 + ((style - 1) % 3)
    y = 59
    length = 7 + ((style - 1) % 4)
    if style in {4, 8}:
        draw.line((x, y, x-2, y+length, x+4, y+length+1), fill=shadow, width=2)
    elif style in {6, 9, 10}:
        draw.line((x, y, x+1, y+length, x+7, y+length), fill=shadow, width=2)
        draw.point((x+4, y+length-1), fill=highlight)
    else:
        draw.line((x, y, x, y+length, x+5, y+length+1), fill=shadow, width=2)
    if style in {3, 6, 11}:
        draw.point((x+6, y+length), fill=(18,15,18))


def _draw_mouth(draw, style, skin_shadow, lip):
    x, y = 55, 76
    dark = (45, 25, 25)
    if style == 1:
        draw.line((x, y, x+12, y), fill=dark, width=2)
    elif style in {2, 3, 6, 12}:
        draw.line((x, y, x+4, y+2, x+10, y+2, x+14, y-1), fill=dark, width=2)
        if style == 12:
            draw.point((x-2, y), fill=skin_shadow)
            draw.point((x+16, y-1), fill=skin_shadow)
    elif style in {4, 5}:
        draw.rectangle((x, y-1, x+14, y+5), fill=dark)
        draw.rectangle((x+2, y, x+12, y+1), fill=(248, 241, 222))
        if style == 5:
            draw.rectangle((x+3, y+3, x+11, y+4), fill=lip)
    elif style in {7, 8, 9}:
        draw.line((x, y, x+13, y), fill=lip, width=2 if style != 7 else 1)
        if style == 9:
            draw.line((x+2, y+2, x+11, y+2), fill=lip, width=2)
    elif style == 10:
        draw.line((x, y+2, x+13, y), fill=dark, width=2)
    elif style == 11:
        draw.ellipse((x+4, y-2, x+10, y+5), fill=dark)


def _draw_details(draw, style, skin, shadow):
    freckle = _mix(shadow, (80, 35, 25), 0.35)
    if style in {1, 2, 4}:
        points = [(52,65),(56,64),(60,65),(67,64),(71,63)]
        if style == 2:
            points += [(49,67),(54,68),(64,67),(74,66)]
        for p in points:
            draw.point(p, fill=freckle)
    if style in {3, 4}:
        for p in [(43,67),(47,66),(74,65),(77,64)]:
            draw.point(p, fill=freckle)
    if style == 5:
        draw.rectangle((44, 70, 45, 71), fill=freckle)
    elif style == 6:
        draw.rectangle((76, 69, 77, 70), fill=freckle)
    elif style == 7:
        blush = _mix(skin, (236, 82, 89), 0.35)
        draw.rectangle((40, 66, 47, 69), fill=blush)
        draw.rectangle((72, 64, 78, 67), fill=blush)
    elif style == 8:
        draw.point((51, 76), fill=shadow)
        draw.point((73, 74), fill=shadow)
    elif style == 9:
        draw.line((43, 72, 46, 69), fill=shadow, width=1)


def _draw_facial_hair(draw, style, color, skin):
    if style == 0:
        return
    c = _mix(color, (0, 0, 0), 0.15)
    if style <= 10:
        y = 70
        if style == 1:
            for x in range(55, 71, 3):
                draw.point((x, y), fill=_mix(c, (255,255,255), 0.45))
        elif style in {2, 3, 9}:
            draw.line((55, y, 69, y), fill=c, width=1 if style in {2,9} else 2)
        elif style in {4, 5, 6, 8}:
            draw.polygon([(54,y),(61,y-2),(63,y+1),(65,y-2),(72,y),(68,y+4),(63,y+2),(59,y+4)], fill=c)
        elif style == 7:
            draw.line((54,y,61,y+2), fill=c, width=2)
            draw.line((66,y+2,72,y), fill=c, width=2)
        else:
            draw.arc((53, y-4, 64, y+5), 0, 180, fill=c, width=2)
            draw.arc((63, y-4, 74, y+5), 0, 180, fill=c, width=2)
        return
    # Barbas: mandíbula y/o mentón.
    if style == 11:
        for x, y in [(28,78),(31,84),(37,90),(44,94),(53,96),(63,92),(70,86)]:
            draw.point((x,y), fill=_mix(c,(255,255,255),0.35))
    elif style in {12, 13, 14}:
        draw.rectangle((56, 80, 67, 89 + (style-12)*3), fill=c)
        if style == 13:
            draw.ellipse((53, 78, 70, 94), fill=c)
            draw.ellipse((57, 80, 67, 88), fill=skin)
    elif style in {15, 19}:
        draw.line([(27,76),(31,87),(43,95),(58,97),(72,87)], fill=c, width=3 if style == 15 else 2)
    else:
        draw.polygon([(26,74),(31,86),(43,96),(61,97),(74,85),(75,76),(69,86),(59,91),(43,90),(33,82)], fill=c)
        draw.polygon([(52,75),(72,74),(68,82),(57,82)], fill=skin)
        if style in {17, 20}:
            draw.line((54,70,71,70), fill=c, width=2)


def _draw_glasses(draw, style, color):
    if style == 0:
        return
    dark = _mix(color, (0,0,0), 0.2)
    lens = (180, 222, 232, 55)
    sun = style in {17, 18, 19}
    lens_fill = (34, 48, 66, 210) if sun else lens
    left = (41, 49, 57, 62)
    right = (63, 48, 80, 61)
    width = 2 if style not in {1, 14} else 1
    if style in {5, 6, 17}:
        draw.ellipse(left, fill=lens_fill, outline=dark, width=width)
        draw.ellipse(right, fill=lens_fill, outline=dark, width=width)
    elif style in {7, 10}:
        draw.rounded_rectangle(left, radius=4, fill=lens_fill, outline=dark, width=width)
        draw.rounded_rectangle(right, radius=4, fill=lens_fill, outline=dark, width=width)
    elif style == 11:
        draw.polygon([(41,50),(56,49),(54,62),(43,61)], fill=lens_fill, outline=dark)
        draw.polygon([(64,49),(80,49),(77,61),(65,61)], fill=lens_fill, outline=dark)
    else:
        draw.rectangle(left, fill=lens_fill, outline=dark, width=width)
        draw.rectangle(right, fill=lens_fill, outline=dark, width=width)
    draw.line((57, 54, 63, 53), fill=dark, width=width)
    draw.line((41, 53, 24, 49), fill=dark, width=width)
    if style in {8, 13}:
        draw.line((60, 49, 61, 45, 64, 49), fill=dark, width=1)
    if style in {9, 15}:
        draw.line((41,49,57,49), fill=dark, width=3)
        draw.line((63,48,80,48), fill=dark, width=3)


def _draw_accessory(draw, style, skin_shadow):
    if style == 0:
        return
    gold, silver = (236, 182, 38), (207, 217, 226)
    if style == 1:
        draw.ellipse((13, 57, 17, 61), fill=silver, outline=(18,15,18))
    elif style == 2:
        draw.rectangle((13, 57, 17, 61), fill=silver, outline=(18,15,18))
    elif style == 3:
        draw.polygon([(15,54),(17,58),(21,58),(18,61),(19,65),(15,62),(11,65),(12,61),(9,58),(13,58)], fill=gold, outline=(18,15,18))
    elif style in {4, 5, 6}:
        radius = 5 if style == 4 else 7
        draw.ellipse((10,55,10+radius*2,55+radius*2), outline=gold if style != 5 else silver, width=2)
        if style == 6:
            draw.ellipse((14,60,22,70), outline=silver, width=2)
    elif style == 7:
        draw.arc((8,43,22,61), 240, 80, fill=silver, width=2)
    elif style == 8:
        draw.line((15,61,15,72), fill=gold, width=2)
        draw.ellipse((11,70,19,79), fill=(54,148,214), outline=(18,15,18))
    elif style == 9:  # hearing aid
        draw.arc((6,39,23,62), 260, 80, fill=silver, width=4)
        draw.rectangle((10,42,15,54), fill=(80,90,99), outline=(18,15,18))
    elif style == 10:  # cochlear processor
        draw.ellipse((7,31,18,42), fill=(65,68,73), outline=(18,15,18))
        draw.line((12,41,18,57), fill=(65,68,73), width=3)
    elif style == 11:
        draw.ellipse((77,64,80,67), fill=silver, outline=(18,15,18))
    elif style == 12:
        draw.arc((73,62,81,72), 80, 285, fill=gold, width=2)
    elif style == 13:
        draw.ellipse((72,43,76,47), fill=silver, outline=(18,15,18))
    elif style == 14:
        draw.arc((69,39,78,49), 80, 285, fill=gold, width=2)
    elif style == 15:
        draw.rounded_rectangle((38,69,49,76), radius=2, fill=(224,170,132), outline=skin_shadow)
        draw.line((40,71,47,74), fill=(245,211,180), width=1)


def render_avatar(config: AvatarConfig, scale: int = DEFAULT_SCALE) -> Image.Image:
    """Devuelve un avatar RGBA. Renderiza a 96x112 y escala sin suavizado."""
    validate_config(config)
    if not isinstance(scale, int) or scale < 1 or scale > 8:
        raise ValueError("scale debe ser un entero entre 1 y 8")

    skin = SKIN_TONES[config.skin_tone]
    skin_shadow = _mix(skin, (102, 44, 31), 0.21)
    skin_highlight = _mix(skin, (255, 245, 218), 0.27)
    lip = _mix(skin, (152, 45, 56), 0.42)
    hair = HAIR_COLORS[config.hair_color]
    hair_shadow = _mix(hair, (8, 7, 10), 0.35)
    hair_highlight = _mix(hair, (255, 214, 150), 0.24)

    def style_index(field: str) -> int:
        value = getattr(config, field)
        numeric_parts = [part for part in value.split("_") if part.isdigit()]
        if len(numeric_parts) != 1:
            raise ValueError(f"No se pudo obtener el índice de {field}={value!r}")
        return int(numeric_parts[0])

    ids = {
        name: style_index(name)
        for name in ("face_shape", "eye_style", "eyebrow_style", "nose_style",
                     "mouth_style", "ear_style", "detail_style", "hair_style",
                     "glasses_style", "facial_hair_style", "accessory_style")
    }

    image = Image.new("RGBA", LOGICAL_SIZE, (0, 0, 0, 0))

    def widened_hair_layer(draw_function) -> Image.Image:
        layer = Image.new("RGBA", LOGICAL_SIZE, (0, 0, 0, 0))
        layer_draw = ImageDraw.Draw(layer, "RGBA")
        draw_function(layer_draw)
        widened = layer.resize((104, LOGICAL_SIZE[1]), Image.Resampling.NEAREST)
        return widened.crop((4, 0, 100, LOGICAL_SIZE[1]))

    back_hair = widened_hair_layer(
        lambda layer_draw: _draw_back_hair(
            layer_draw, ids["hair_style"], hair, hair_shadow
        )
    )
    image.alpha_composite(back_hair)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_neck(draw, skin, skin_shadow)
    _draw_ear(draw, ids["ear_style"], skin, skin_shadow, skin_highlight)
    _draw_face(draw, ids["face_shape"], skin, skin_shadow, skin_highlight)
    front_hair = widened_hair_layer(
        lambda layer_draw: _draw_hair(
            layer_draw, ids["hair_style"], hair, hair_shadow, hair_highlight
        )
    )
    image.alpha_composite(front_hair)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_details(draw, ids["detail_style"], skin, skin_shadow)
    _draw_eyes(draw, ids["eye_style"], IRIS_COLORS[config.iris_color])
    _draw_brows(draw, ids["eyebrow_style"], hair)
    _draw_nose(draw, ids["nose_style"], skin_shadow, skin_highlight)
    _draw_mouth(draw, ids["mouth_style"], skin_shadow, lip)
    _draw_facial_hair(draw, ids["facial_hair_style"], hair, skin)
    _draw_glasses(draw, ids["glasses_style"], FRAME_COLORS[config.frame_color])
    _draw_accessory(draw, ids["accessory_style"], skin_shadow)

    if config.facing == "left":
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if scale != 1:
        image = image.resize(
            (LOGICAL_SIZE[0] * scale, LOGICAL_SIZE[1] * scale),
            Image.Resampling.NEAREST,
        )
    return image


def save_avatar(config: AvatarConfig, output_path: str | Path, scale: int = DEFAULT_SCALE) -> Path:
    """Guarda atómicamente un PNG transparente sin modificar otros archivos."""
    path = Path(output_path)
    if path.suffix.casefold() != ".png":
        raise ValueError("El avatar debe guardarse como .png")
    path.parent.mkdir(parents=True, exist_ok=True)
    image = render_avatar(config, scale=scale)
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        image.save(temp, format="PNG", optimize=False)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return path


def save_uuid_avatar(
    config: AvatarConfig,
    avatar_dir: str | Path,
    scale: int = DEFAULT_SCALE,
) -> tuple[str, Path]:
    """Crea un PNG UUID nuevo; jamás sobreescribe un avatar anterior."""
    folder = Path(avatar_dir)
    folder.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        avatar_id = str(uuid4())
        path = folder / f"{avatar_id}.png"
        if path.exists():
            continue
        save_avatar(config, path, scale=scale)
        return avatar_id, path
    raise OSError("No se pudo reservar un UUID único para el avatar")


def random_config(rng: random.Random, facing: str | None = None) -> AvatarConfig:
    """Genera una combinación válida; útil para QA y previews."""
    data = {field: rng.choice(values) for field, values in CATALOG.items()}
    if facing:
        data["facing"] = facing
    # La mayoría de las combinaciones se mantienen juveniles y sin vello.
    if rng.random() < 0.78:
        data["facial_hair_style"] = "facial_hair_00_none"
    if rng.random() < 0.58:
        data["accessory_style"] = "accessory_00_none"
    if rng.random() < 0.45:
        data["glasses_style"] = "glasses_00_none"
    return AvatarConfig.from_dict(data)


def _demo_configs() -> list[AvatarConfig]:
    """Selección curada: variedad alta sin combinaciones visualmente ruidosas."""
    hair_styles = [1, 3, 4, 5, 7, 8, 9, 10, 11, 14, 17, 18,
                   19, 20, 21, 22, 23, 25, 27, 30, 32, 33, 37, 40]
    skin_keys = list(SKIN_TONES)
    hair_keys = [
        "hair_color_03_dark_brown", "hair_color_10_auburn",
        "hair_color_01_black", "hair_color_08_blond",
        "hair_color_04_brown", "hair_color_02_soft_black",
        "hair_color_11_copper", "hair_color_06_light_brown",
        "hair_color_12_gray", "hair_color_05_chestnut",
    ]
    iris_keys = list(IRIS_COLORS)
    eye_sequence = [1, 3, 2, 5, 1, 4, 2, 3, 1, 5, 2, 4,
                    1, 3, 2, 5, 1, 4, 2, 3, 1, 5, 2, 4]
    mouth_sequence = [2, 3, 4, 2, 5, 6, 2, 3, 7, 2, 3, 4,
                      2, 6, 8, 2, 3, 5, 2, 12, 3, 2, 4, 2]
    glasses = {2: 2, 5: 5, 9: 10, 13: 6, 17: 14, 21: 3}
    accessories = {3: 1, 7: 3, 11: 9, 15: 11, 19: 8, 23: 10}
    facial_hair = {4: 3, 10: 8, 16: 13, 22: 16}
    configs = []
    for i, hair_style in enumerate(hair_styles):
        config = AvatarConfig(
            face_shape=f"face_{i % 10 + 1:02d}",
            skin_tone=skin_keys[(i * 3) % len(skin_keys)],
            eye_style=f"eyes_{eye_sequence[i]:02d}",
            iris_color=iris_keys[(i * 2) % len(iris_keys)],
            eyebrow_style=f"brows_{i % 12 + 1:02d}",
            nose_style=f"nose_{(i * 5) % 12 + 1:02d}",
            mouth_style=f"mouth_{mouth_sequence[i]:02d}",
            ear_style=f"ear_{i % 10 + 1:02d}",
            detail_style=("detail_00_none" if i % 4 else f"detail_{i % 9 + 1:02d}"),
            hair_style=f"hair_{hair_style:02d}",
            hair_color=hair_keys[(i * 7) % len(hair_keys)],
            glasses_style=(f"glasses_{glasses[i]:02d}" if i in glasses else "glasses_00_none"),
            frame_color=list(FRAME_COLORS)[(i * 2) % len(FRAME_COLORS)],
            facial_hair_style=(f"facial_hair_{facial_hair[i]:02d}" if i in facial_hair else "facial_hair_00_none"),
            accessory_style=(f"accessory_{accessories[i]:02d}" if i in accessories else "accessory_00_none"),
            facing="right" if i % 2 == 0 else "left",
        )
        validate_config(config)
        configs.append(config)
    return configs


def create_demo(output_dir: str | Path, seed: int = 20260913) -> list[Path]:
    """Genera dos PNG de juego, sus opuestos y una grilla de 24 ejemplos."""
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    # La semilla queda en la API para conservar compatibilidad del comando.
    # La muestra visible es curada; random_config sigue cubierto por las pruebas.
    _ = seed
    configs = _demo_configs()

    outputs = []
    for index, config in enumerate(configs[:2], start=1):
        outputs.append(save_avatar(config, folder / f"avatar_demo_j{index}.png"))
        opposite = replace(config, facing="left" if config.facing == "right" else "right")
        outputs.append(save_avatar(opposite, folder / f"avatar_demo_j{index}_opuesto.png"))
        (folder / f"avatar_demo_j{index}.json").write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    tile_w, tile_h = 212, 236
    sheet = Image.new("RGBA", (6 * tile_w, 4 * tile_h), (8, 25, 48, 255))
    for i, config in enumerate(configs):
        avatar = render_avatar(config, scale=2)
        x = (i % 6) * tile_w + (tile_w - avatar.width) // 2
        y = (i // 6) * tile_h + (tile_h - avatar.height) // 2
        sheet.alpha_composite(avatar, (x, y))
    sheet_path = folder / "avatar_demo_24.png"
    sheet.save(sheet_path, format="PNG")
    outputs.append(sheet_path)

    catalog_path = folder / "avatar_catalog.json"
    catalog_path.write_text(
        json.dumps(CATALOG, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    outputs.append(catalog_path)
    return outputs


def _read_config(path: str | Path) -> AvatarConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("La configuración JSON debe ser un objeto")
    return AvatarConfig.from_dict(data)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Constructor modular de Expo Heads")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", metavar="CARPETA", help="genera una demostración reproducible")
    group.add_argument("--config", metavar="JSON", help="configuración de un avatar")
    parser.add_argument("--output", metavar="PNG", help="salida para --config")
    parser.add_argument("--facing", choices=("right", "left"), help="sobrescribe la orientación")
    parser.add_argument("--scale", type=int, default=DEFAULT_SCALE, help="escala entera 1..8")
    parser.add_argument("--seed", type=int, default=20260913, help="semilla de --demo")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.demo:
        for path in create_demo(args.demo, seed=args.seed):
            print(path)
        return 0
    if not args.output:
        parser.error("--output es obligatorio cuando se usa --config")
    config = _read_config(args.config)
    if args.facing:
        config = replace(config, facing=args.facing)
    print(save_avatar(config, args.output, scale=args.scale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
