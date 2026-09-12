"""
Extrae los módulos internos del exe y prepara todo para correr el juego parcheado.
Ejecutar UNA sola vez: python setup_patched.py
"""
import subprocess, sys, os

exe_path = "head football.exe"
if not os.path.exists(exe_path):
    print(f"ERROR: No se encuentra {exe_path}")
    sys.exit(1)

print("Extrayendo módulos del exe...")
subprocess.run([sys.executable, "-m", "pyinstxtractor_ng", exe_path], check=True)

print("\n✅ Extracción completa.")
print("Ahora ejecutá: python run_patched.py")