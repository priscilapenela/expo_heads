from pathlib import Path
from datetime import datetime
import sqlite3
import os

BASE = Path(__file__).resolve().parent
# Si este script se ejecuta desde Descargas pero el .bat está dentro del proyecto,
# el cwd será la carpeta del proyecto y esa es la que nos interesa.
PROJECT = Path.cwd()

print("=" * 72)
print("EXPO HEADS - DIAGNOSTICO CHECK 5 (SOLO LECTURA)")
print("Carpeta analizada:", PROJECT)
print("=" * 72)

info = PROJECT / "data" / "info_files"
settings = info / "tren_igra_postavke.txt"

print("\n[1] NOMBRES CONFIGURADOS")
if settings.is_file():
    try:
        lines = settings.read_text(encoding="utf-8", errors="replace").splitlines()
        print("Archivo:", settings)
        print("Linea 4:", repr(lines[3] if len(lines) > 3 else "<NO EXISTE>"))
        print("Linea 5:", repr(lines[4] if len(lines) > 4 else "<NO EXISTE>"))
    except Exception as exc:
        print("ERROR leyendo settings:", exc)
else:
    print("NO EXISTE:", settings)

print("\n[2] ARCHIVOS DE RESULTADO EN data/info_files")
result_files = []
if info.is_dir():
    for p in info.iterdir():
        if p.is_file() and p.name.startswith("cijeli_game_") and p.name.lower().endswith("nfo.txt"):
            result_files.append(p)
else:
    print("NO EXISTE carpeta:", info)

if not result_files:
    print("No se encontraron archivos cijeli_game_*nfo.txt")
else:
    for p in sorted(result_files, key=lambda x: x.stat().st_mtime_ns, reverse=True):
        st = p.stat()
        print("\nArchivo:", repr(p.name))
        print("Modificado:", datetime.fromtimestamp(st.st_mtime).isoformat(sep=" ", timespec="seconds"))
        print("Tamaño:", st.st_size)
        try:
            raw = p.read_text(encoding="utf-8", errors="replace").strip()
            print("Contenido:", repr(raw[:500]))
            parts = [x.strip() for x in raw.splitlines()[-1].split("|")] if raw else []
            if len(parts) >= 4:
                print("Interpretado: P1=%r P2=%r G1=%r G2=%r" % tuple(parts[:4]))
        except Exception as exc:
            print("ERROR leyendo:", exc)

print("\n[3] REPLAYS RECIENTES CON POSIBLE RESULTADO")
recent = PROJECT / "data" / "replays" / "recent"
found = 0
if recent.is_dir():
    candidates = sorted((p for p in recent.iterdir() if p.is_file()), key=lambda x: x.stat().st_mtime_ns, reverse=True)
    for p in candidates[:8]:
        if "nfo" not in p.name.lower() and "info" not in p.name.lower():
            continue
        found += 1
        print("\nReplay:", repr(p.name))
        print("Modificado:", datetime.fromtimestamp(p.stat().st_mtime).isoformat(sep=" ", timespec="seconds"))
        try:
            print("Contenido:", repr(p.read_text(encoding="utf-8", errors="replace").strip()[:500]))
        except Exception as exc:
            print("ERROR leyendo:", exc)
if not found:
    print("No se encontraron *_nfo recientes.")

print("\n[4] BASE expo_heads.db")
db = PROJECT / "data" / "expo_heads.db"
if not db.is_file():
    print("NO EXISTE:", db)
else:
    try:
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        for table in ("partidas", "ranking", "jugadores", "avatares"):
            try:
                count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                print(f"{table}: {count} filas")
            except Exception as exc:
                print(f"{table}: ERROR {exc}")
        try:
            rows = con.execute("SELECT jugador, goles, goles_recibidos, modo, fecha FROM partidas ORDER BY id DESC LIMIT 6").fetchall()
            print("Ultimas partidas:")
            for r in rows:
                print("  ", r)
        except Exception as exc:
            print("No pude listar partidas:", exc)
        con.close()
    except Exception as exc:
        print("ERROR abriendo DB:", exc)

print("\n" + "=" * 72)
print("FIN DEL DIAGNOSTICO. No se modificó ningún archivo.")
print("Copiame esta salida completa en el chat.")
print("=" * 72)
