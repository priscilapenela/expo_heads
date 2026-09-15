from pathlib import Path
import os
import py_compile
import shutil

BASE_DIR = Path(__file__).resolve().parent
LAUNCHER = BASE_DIR / "launcher.py"
BACKUP = BASE_DIR / "launcher.py.before_check5_resultados"

NEW_BLOCK = 'def _result_info_paths():\n    """\n    Lista todas las fuentes válidas de resultado del juego.\n\n    El EXE actual deja data/info_files/cijeli_game_łnfo.txt vacío al finalizar,\n    pero sí escribe el marcador real en data/replays/recent/*nfo.txt.\n    Por eso se monitorean ambas ubicaciones.\n    """\n    paths = [RESULT_INFO_FILE]\n\n    if INFO_DIR.is_dir():\n        for candidate in INFO_DIR.glob("cijeli_game_*nfo.txt"):\n            if candidate.is_file() and candidate not in paths:\n                paths.append(candidate)\n\n    replay_dir = BASE_DIR / "data" / "replays" / "recent"\n    if replay_dir.is_dir():\n        for candidate in replay_dir.glob("*nfo.txt"):\n            if candidate.is_file() and candidate not in paths:\n                paths.append(candidate)\n\n    return paths\n'

def main():
    print("=" * 72)
    print("EXPO HEADS - CHECK 5")
    print("Parche: leer el marcador real desde data/replays/recent")
    print("=" * 72)

    if not LAUNCHER.is_file():
        print(f"ERROR: No se encontro {LAUNCHER}")
        return 1

    original = LAUNCHER.read_text(encoding="utf-8")

    if "El EXE actual deja data/info_files/cijeli_game_łnfo.txt vacío" in original:
        print("OK: launcher.py ya tiene aplicado este parche.")
        return 0

    start = original.find("def _result_info_paths():")
    end = original.find("\ndef snapshot_match_results()", start)

    if start == -1 or end == -1:
        print("ERROR: No pude localizar el bloque _result_info_paths() esperado.")
        print("No se modifico launcher.py.")
        return 2

    if not BACKUP.exists():
        shutil.copy2(LAUNCHER, BACKUP)
        print(f"Backup: {BACKUP.name}")
    else:
        print(f"Backup existente conservado: {BACKUP.name}")

    patched = original[:start] + NEW_BLOCK + original[end + 1:]

    temp = LAUNCHER.with_name("launcher.py.check5_tmp")
    temp.write_text(patched, encoding="utf-8")

    try:
        py_compile.compile(str(temp), doraise=True)
    except Exception as exc:
        temp.unlink(missing_ok=True)
        print(f"ERROR DE SINTAXIS: {exc}")
        print("No se modifico launcher.py.")
        return 3

    os.replace(temp, LAUNCHER)

    print()
    print("OK: launcher.py actualizado.")
    print("Ahora snapshot_match_results() controla tambien los replays.")
    print("El filtro de nombres sigue activo para no tomar partidos viejos.")
    print()
    print("CHECK 5A aplicado correctamente.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
