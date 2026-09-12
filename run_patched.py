"""
Ejecuta el juego Head Football con power-ups desactivados.
Requiere haber ejecutado setup_patched.py primero.
"""
import marshal, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Agregar los módulos extraídos del exe al path
extracted = os.path.join(os.path.dirname(__file__), "head football.exe_extracted")
pyz = os.path.join(extracted, "PYZ.pyz_extracted")

for p in [extracted, pyz]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Cargar y ejecutar el juego parcheado
with open("head football patched.pyc", "rb") as f:
    f.read(16)
    code = marshal.load(f)

exec(code)