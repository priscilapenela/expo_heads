"""Pruebas del CHECK AVATAR 6. Ejecutar: python -m unittest -v."""

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageChops

from avatar_builder import (
    AvatarConfig,
    CATALOG,
    LOGICAL_SIZE,
    random_config,
    render_avatar,
    save_avatar,
    save_uuid_avatar,
)


class AvatarBuilderTests(unittest.TestCase):
    def test_default_is_valid_transparent_rgba(self):
        image = render_avatar(AvatarConfig(), scale=1)
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.size, LOGICAL_SIZE)
        self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.assertIsNotNone(image.getchannel("A").getbbox())

    def test_scale_is_integer_nearest_neighbor(self):
        base = render_avatar(AvatarConfig(), scale=1)
        scaled = render_avatar(AvatarConfig(), scale=3)
        self.assertEqual(scaled.size, (288, 336))
        self.assertEqual(
            scaled,
            base.resize(scaled.size, Image.Resampling.NEAREST),
        )

    def test_left_is_exact_mirror_of_right(self):
        right_config = AvatarConfig(
            hair_style="hair_32",
            glasses_style="glasses_08",
            accessory_style="accessory_09",
            facing="right",
        )
        left_config = replace(right_config, facing="left")
        right = render_avatar(right_config, scale=1)
        left = render_avatar(left_config, scale=1)
        expected = right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        self.assertIsNone(ImageChops.difference(left, expected).getbbox())

    def test_unknown_value_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no existe"):
            AvatarConfig.from_dict({"hair_style": "hair_99"})

    def test_unknown_field_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "desconocidos"):
            AvatarConfig.from_dict({"modo_secreto": "x"})

    def test_all_catalog_endpoints_render(self):
        base = AvatarConfig()
        for field, values in CATALOG.items():
            for value in (values[0], values[-1]):
                image = render_avatar(replace(base, **{field: value}), scale=1)
                self.assertEqual(image.size, LOGICAL_SIZE)

    def test_200_random_combinations_are_deterministic(self):
        import random

        rng_a = random.Random(731)
        rng_b = random.Random(731)
        hashes_a = []
        hashes_b = []
        for _ in range(200):
            hashes_a.append(hashlib.sha256(render_avatar(random_config(rng_a), 1).tobytes()).digest())
            hashes_b.append(hashlib.sha256(render_avatar(random_config(rng_b), 1).tobytes()).digest())
        self.assertEqual(hashes_a, hashes_b)
        self.assertGreater(len(set(hashes_a)), 190)

    def test_atomic_save_and_uuid_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = save_avatar(AvatarConfig(), root / "direct.png")
            self.assertTrue(target.is_file())
            with Image.open(target) as image:
                self.assertEqual(image.size, (192, 224))

            avatar_a, path_a = save_uuid_avatar(AvatarConfig(), root)
            avatar_b, path_b = save_uuid_avatar(AvatarConfig(), root)
            self.assertNotEqual(avatar_a, avatar_b)
            self.assertNotEqual(path_a, path_b)
            self.assertTrue(path_a.is_file())
            self.assertTrue(path_b.is_file())


if __name__ == "__main__":
    unittest.main()
