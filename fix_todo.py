"""
fix_todo.py — Repara TODOS los archivos de data/info_files/ que causan crashes.
Ejecutar desde la raíz del repo: python fix_todo.py
"""
import os, glob

info_dir = os.path.join("data", "info_files")

# 1. Sentinel para cijeli_game_*nfo.txt (TODOS los que matcheen)
sentinel = "__EXPO_PENDING__|pending|-1|-1|0|0"
count = 0
for pattern in ["cijeli_game_*nfo.txt", "cijeli_game_*nfo*.txt"]:
    for path in glob.glob(os.path.join(info_dir, pattern)):
        with open(path, "w", encoding="utf-8") as f:
            f.write(sentinel)
        print(f"  OK sentinel: {path}")
        count += 1

# Si no encontró ninguno, crearlos
if count == 0:
    for name in ["cijeli_game_\u0142nfo.txt", "cijeli_game_#U0142nfo.txt"]:
        path = os.path.join(info_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(sentinel)
        print(f"  OK creado: {path}")

# 2. cijeli_game.txt — copiar contenido de tren_igra_dat.txt
src = os.path.join(info_dir, "tren_igra_dat.txt")
dst = os.path.join(info_dir, "cijeli_game.txt")
if os.path.exists(src):
    with open(src, "rb") as f:
        data = f.read()
    with open(dst, "wb") as f:
        f.write(data)
    print(f"  OK cijeli_game.txt: {len(data)} bytes (copiado de tren_igra_dat.txt)")
else:
    print(f"  ERROR: no se encontró {src}")

# 3. jezik.txt — convertir LF a CRLF si hace falta
jezik = os.path.join(info_dir, "jezik.txt")
if os.path.exists(jezik):
    with open(jezik, "rb") as f:
        data = f.read()
    if b"\r\n" not in data and b"\n" in data:
        data = data.replace(b"\n", b"\r\n")
        with open(jezik, "wb") as f:
            f.write(data)
        print(f"  OK jezik.txt: LF → CRLF ({len(data)} bytes)")
    else:
        print(f"  OK jezik.txt: ya tiene CRLF")

# 4. kontrole.txt — quitar trailing pipe si existe
kontrol = os.path.join(info_dir, "kontrole.txt")
if os.path.exists(kontrol):
    with open(kontrol, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if text.endswith("|"):
        text = text[:-1]
        with open(kontrol, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  OK kontrole.txt: trailing pipe removido")
    else:
        print(f"  OK kontrole.txt: sin cambios")

# 5. Verificar tren_igra_postavke.txt tiene CRLF
trp = os.path.join(info_dir, "tren_igra_postavke.txt")
if os.path.exists(trp):
    with open(trp, "rb") as f:
        data = f.read()
    if b"\r\n" not in data and b"\n" in data:
        data = data.replace(b"\n", b"\r\n")
        with open(trp, "wb") as f:
            f.write(data)
        print(f"  OK tren_igra_postavke.txt: LF → CRLF")
    else:
        print(f"  OK tren_igra_postavke.txt: ya tiene CRLF")

print("\n✅ Todos los archivos reparados. Probá el exe.")
