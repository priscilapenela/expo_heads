from pathlib import Path
import json
import copy
import shutil

BASE_DIR = Path(__file__).resolve().parent
CATALOG = BASE_DIR / "avatars_catalog.json"
BACKUP = BASE_DIR / "avatars_catalog.json.before_hair_v2"

STYLE_MAP = {
    "spiky_short": {
        "hair_shape_family": "messy_short",
        "hair_style_variant": "spiky_short",
        "hair_tied": "none",
        "hair_texture": "spiky",
    },
    "dreadlocks": {
        "hair_shape_family": "locs",
        "hair_style_variant": "dreadlocks",
        "hair_texture": "locs",
    },
    "layered_medium": {
        "hair_shape_family": "long_layered",
        "hair_style_variant": "layered_medium",
        "hair_tied": "none",
    },
    "high_ponytail": {
        "hair_shape_family": "ponytail",
        "hair_style_variant": "high_ponytail",
        "hair_tied": "ponytail",
    },
    "afro": {
        "hair_shape_family": "afro",
        "hair_style_variant": "afro",
        "hair_volume": "high",
        "hair_tied": "none",
        "parting": "none",
    },
    "bald": {
        "hair_shape_family": "none",
        "hair_style_variant": "bald",
        "hair_volume": "low",
        "bangs": "none",
        "hair_tied": "none",
        "parting": "none",
        "face_framing": "none",
    },
    "braids_cornrows": {
        "hair_shape_family": "braids",
        "hair_style_variant": "braids_cornrows",
        "hair_texture": "braided",
    },
    "shoulder_length_straight": {
        "hair_shape_family": "long_loose",
        "hair_style_variant": "shoulder_length_straight",
        "hair_tied": "none",
    },
    "messy_medium": {
        "hair_shape_family": "messy_medium",
        "hair_style_variant": "messy_medium",
        "hair_tied": "none",
    },
    "high_bun_ponytail": {
        "hair_shape_family": "bun",
        "hair_style_variant": "high_bun_ponytail",
        "hair_tied": "bun",
    },
}

def enrich(item):
    item = copy.deepcopy(item)
    traits = item.setdefault("traits", {})
    vm = item.get("visual_metadata") or {}
    accessories = set(item.get("accessories") or [])
    accessories.update(vm.get("accessories") or [])
    source = []
    notes = []

    if traits.get("bald") is True or traits.get("hair_length") == "bald":
        traits.update({
            "hair_shape_family": "none",
            "hair_style_variant": "bald",
            "hair_volume": "low",
            "bangs": "none",
            "hair_tied": "none",
            "parting": "none",
            "face_framing": "none",
        })
        source.append("bald")

    style = vm.get("hair_style")
    if style in STYLE_MAP:
        traits.update(STYLE_MAP[style])
        source.append("visual_metadata.hair_style")
        notes.append(f"Mapeado desde {style!r}")

    if "ponytail" in accessories and "hair_shape_family" not in traits:
        traits.update({
            "hair_shape_family": "ponytail",
            "hair_style_variant": "ponytail",
            "hair_tied": "ponytail",
        })
        source.append("accessories.ponytail")

    if "braids" in accessories and "hair_shape_family" not in traits:
        traits.update({
            "hair_shape_family": "braids",
            "hair_style_variant": "braids",
        })
        source.append("accessories.braids")

    if "undercut" in accessories and "hair_shape_family" not in traits:
        traits.update({
            "hair_shape_family": "undercut",
            "hair_style_variant": "undercut",
            "hair_tied": "none",
        })
        source.append("accessories.undercut")

    if "hair_shape_family" not in traits and traits.get("hair_texture") == "braided":
        traits.update({
            "hair_shape_family": "braids",
            "hair_style_variant": "braids_unspecified",
        })
        source.append("traits.hair_texture=braided")

    if (
        "hair_shape_family" not in traits
        and traits.get("hair_texture") == "spiky"
        and traits.get("hair_length") in {"very_short", "short"}
    ):
        traits.update({
            "hair_shape_family": "messy_short",
            "hair_style_variant": "spiky_short_unspecified",
            "hair_tied": "none",
        })
        source.append("traits.short+spiky")

    item["hair_v2_annotation"] = {
        "status": "partial" if "hair_shape_family" in traits else "pending_visual_review",
        "source": source,
        "notes": notes,
    }
    return item

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

    enriched = [enrich(item) for item in data]

    ids = [x.get("id") for x in enriched]
    if len(ids) != len(set(ids)):
        raise SystemExit("ERROR: IDs duplicados en catálogo")

    tmp = CATALOG.with_name(CATALOG.name + ".hair_v2_tmp")
    tmp.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CATALOG)

    annotated = sum(
        1 for x in enriched
        if x.get("hair_v2_annotation", {}).get("status") == "partial"
    )
    print(f"OK: {annotated}/{len(enriched)} avatares enriquecidos con metadata Hair V2.")
    print("Los restantes quedan pendientes de revisión visual; no se inventaron datos.")

if __name__ == "__main__":
    main()
