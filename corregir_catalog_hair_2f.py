from pathlib import Path
import json
import shutil

BASE_DIR = Path(__file__).resolve().parent
CATALOG = BASE_DIR / "avatars_catalog.json"
BACKUP = BASE_DIR / "avatars_catalog.json.before_hair_2f"

def main():
    if not CATALOG.is_file():
        raise SystemExit(f"ERROR: no existe {CATALOG}")

    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("ERROR: avatars_catalog.json debe tener raíz lista []")

    if not BACKUP.exists():
        shutil.copy2(CATALOG, BACKUP)
        print(f"Backup creado: {BACKUP.name}")
    else:
        print(f"Backup existente conservado: {BACKUP.name}")

    found = False
    for avatar in data:
        if avatar.get("id") != "avatar_0032":
            continue

        traits = avatar.setdefault("traits", {})
        old_family = traits.get("hair_shape_family")

        # El PNG de avatar_0032 es una media melena compacta/capas medias,
        # no una melena larga. Mantenerlo como long_layered hacía que ganara
        # demasiados matches de pelo largo.
        traits["hair_shape_family"] = "layered_medium"
        traits["hair_style_variant"] = "layered_medium"

        annotation = avatar.setdefault("hair_v2_annotation", {})
        annotation["status"] = "reviewed"
        annotation["source"] = ["visual_review", "visual_metadata.hair_style"]
        annotation["notes"] = [
            f"hair_shape_family corregido de {old_family!r} a 'layered_medium'."
        ]

        found = True
        break

    if not found:
        raise SystemExit("ERROR: no se encontró avatar_0032 en el catálogo")

    tmp = CATALOG.with_name(CATALOG.name + ".hair_2f_tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(CATALOG)

    print("OK: avatar_0032 actualizado a hair_shape_family='layered_medium'.")

if __name__ == "__main__":
    main()
