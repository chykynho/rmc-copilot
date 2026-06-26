from pathlib import Path
import py_compile, sys, re
root = Path(__file__).resolve().parents[1]
t = root / "app" / "dashboard_streamlit.py"
print(f"[INFO] Validando {t}")
py_compile.compile(str(t), doraise=True)
print("[OK] dashboard_streamlit.py compila")
text = t.read_text(encoding="utf-8", errors="ignore")
checks = {
    "marker": "HOTFIX_15F_10_34_ANALISE_INDIVIDUAL_VM_SEM_ERROS",
    "titulo_correto": "Análise Individual de VM",
    "json_ia_recurso": "def _ia_json_extract",
    "guard_recurso": "def _texto_tem_contradicao_recurso",
    "guard_total": "def _texto_tem_contradicao_total",
    "html_png": "data:image/png;base64",
    "nao_fup_titulo": "Isto NÃO é FUP",
    "ia_so_recomenda": "A IA só analisa, explica e recomenda",
}
ok=True
for name, needle in checks.items():
    found = needle in text
    print(f"[{'OK' if found else 'ERRO'}] {name}")
    ok = ok and found
# Garante que a recomendação total não usa FUP.
if "manter FUP próximo" in text:
    print("[ERRO] termo FUP indevido no relatório total")
    ok=False
sys.exit(0 if ok else 1)
