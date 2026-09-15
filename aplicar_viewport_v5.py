from __future__ import annotations

from pathlib import Path
import hashlib
import os
import shutil
import sys

TARGETS = (
    "head_football_patched_v5_1v1.exe",
    "head_football_patched_v5_top1_ai.exe",
)

OLD = b'<longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>'
NEW = b'<dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>'
NEW_PADDED = NEW + (b" " * (len(OLD) - len(NEW)))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def patch_exe(path: Path) -> str:
    data = path.read_bytes()

    if data.count(OLD) == 1:
        before_size = len(data)
        before_hash = sha256(path)

        backup = path.with_suffix(path.suffix + ".before_viewport")
        if not backup.exists():
            shutil.copy2(path, backup)

        pos = data.find(OLD)
        patched = bytearray(data)
        patched[pos : pos + len(OLD)] = NEW_PADDED

        if len(patched) != before_size:
            raise RuntimeError(f"El tamaño cambió inesperadamente en {path.name}.")

        temp = path.with_suffix(path.suffix + ".expo_tmp")
        temp.write_bytes(patched)
        os.replace(temp, path)

        after_hash = sha256(path)
        return (
            f"OK  {path.name}\n"
            f"    backup: {backup.name}\n"
            f"    SHA256 antes : {before_hash}\n"
            f"    SHA256 después: {after_hash}"
        )

    # La versión ya parcheada conserva el XML nuevo y rellena el resto con espacios.
    if data.count(NEW) == 1:
        return f"YA  {path.name} ya tiene DPI-aware / viewport automático."

    raise RuntimeError(
        f"No encontré el manifiesto esperado en {path.name}. "
        "No se modificó el archivo."
    )


def main() -> int:
    base = Path(__file__).resolve().parent
    missing = [name for name in TARGETS if not (base / name).is_file()]
    if missing:
        print("ERROR: faltan estos archivos en la misma carpeta que este script:")
        for name in missing:
            print(f"  - {name}")
        print("\nNo se modificó ningún ejecutable.")
        return 2

    print("Expo Heads - CHECK 2: viewport automático en 1v1 y Top #1 IA\n")
    for name in TARGETS:
        try:
            print(patch_exe(base / name))
            print()
        except Exception as exc:
            print(f"ERROR en {name}: {exc}")
            return 1

    print("LISTO. El launcher puede seguir usando exactamente los mismos nombres de EXE.")
    print("Probá primero 1 VS 1 y después 1 VS TOP #1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
