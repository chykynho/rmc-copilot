import sys

try:
    import pyVim
    import pyVmomi
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim, vmodl
except Exception as exc:
    print("[ERRO] Falha no import pyVim/pyVmomi")
    print(f"[ERRO] {type(exc).__name__}: {exc}")
    print("[INFO] Instale com: python -m pip install pyvmomi")
    print("[INFO] No código, use: from pyVim.connect import SmartConnect, Disconnect")
    print("[INFO] No código, use: from pyVmomi import vim, vmodl")
    sys.exit(1)

print("[OK] Import correto: pyVim")
print("[OK] Import correto: pyVmomi")
print("[OK] from pyVim.connect import SmartConnect, Disconnect")
print("[OK] from pyVmomi import vim, vmodl")
