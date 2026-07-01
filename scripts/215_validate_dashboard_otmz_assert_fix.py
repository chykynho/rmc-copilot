from __future__ import annotations

import re
from pathlib import Path

dash = Path("app/dashboard_streamlit.py")
bridge = Path("app/rmc_otmz_menu_view.py")
view = Path("app/rmc_optimization_all_view.py")

print("[INFO] Validação 16A.14.7")

if not dash.exists():
    raise SystemExit("[ERRO] app/dashboard_streamlit.py não existe")

txt = dash.read_text(encoding="utf-8", errors="replace")
top = "\n".join(txt.splitlines()[:220])

checks = {}

try:
    compile(txt, str(dash), "exec")
    checks["dashboard_compila"] = True
except Exception as e:
    checks["dashboard_compila"] = False
    print("[ERRO] dashboard não compila:", e)

checks["tem_def_main"] = "def main(" in txt
checks["tem_rota_otimizacao"] = ('pagina == "Otimização"' in txt) or ("pagina == 'Otimização'" in txt)
checks["tem_render_otimizacao_unificada"] = "def render_otimizacao_unificada(" in txt
checks["otimizacao_chama_otmz"] = bool(re.search(r"def\s+render_otimizacao_unificada\s*\([^)]*\):[\s\S]{0,700}render_otmz_panel\(\)", txt))
checks["sem_import_app_topo"] = "from app.rmc_otmz_menu_view import render_otmz_panel" not in top
checks["sem_import_local_topo"] = "from rmc_otmz_menu_view import render_otmz_panel" not in top
checks["bridge_existe"] = bridge.exists()
checks["view_existe"] = view.exists()

if bridge.exists():
    try:
        compile(bridge.read_text(encoding="utf-8", errors="replace"), str(bridge), "exec")
        checks["bridge_compila"] = True
    except Exception as e:
        checks["bridge_compila"] = False
        print("[ERRO] bridge não compila:", e)

for k, v in checks.items():
    print(f"{k}: {v}")

print("\n[INFO] Linhas relevantes:")
for i, line in enumerate(txt.splitlines(), start=1):
    if "render_otimizacao_unificada" in line or "render_otmz_panel" in line or 'pagina == "Otimização"' in line:
        print(f"{i}: {line.strip()}")

failed = [k for k, v in checks.items() if not v]
if failed:
    raise SystemExit("[ERRO] Falhas: " + ", ".join(failed))

print("[OK] Validação final passou.")
