import marshal, sys, os, traceback

print(f"CWD: {os.getcwd()}")
print(f"Python: {sys.version}")

# Interceptar sys.exit para ver si lo llama
_real_exit = sys.exit
def fake_exit(code=0):
    print(f">>> sys.exit({code}) llamado desde:")
    traceback.print_stack()
    _real_exit(code)
sys.exit = fake_exit

f = open("head football patched.pyc", "rb")
f.read(16)
code = marshal.load(f)
f.close()

print("Ejecutando codigo...")
try:
    exec(code)
except BaseException as e:
    print(f"Excepcion: {type(e).__name__}: {e}")
    traceback.print_exc()

print("Fin")