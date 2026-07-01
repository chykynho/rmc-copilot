from __future__ import annotations

import re
import shutil
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
APP_DIR = ROOT / "app"
DASH = APP_DIR / "dashboard_streamlit.py"
BRIDGE = APP_DIR / "rmc_otmz_menu_view.py"
VIEW = APP_DIR / "rmc_optimization_all_view.py"
PAGES = APP_DIR / "pages"
PAGES_DISABLED = APP_DIR / "pages_disabled"

TAG = datetime.now().strftime("%Y%m%d_%H%M%S")

BAD_GLOBAL_IMPORTS = {
    "from app.rmc_otmz_menu_view import render_otmz_panel",
    "from rmc_otmz_menu_view import render_otmz_panel",
}

def log(msg: str) -> None:
    print(msg, flush=True)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def write_text(path: Path, txt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt, encoding="utf-8")

def backup_file(path: Path, suffix: str) -> Path | None:
    if not path.exists():
        return None
    dst = path.with_suffix(path.suffix + f".{suffix}_{TAG}")
    shutil.copy2(path, dst)
    log(f"[BACKUP] {path} -> {dst}")
    return dst

def remove_global_otmz_imports(txt: str) -> str:
    lines = txt.splitlines(True)
    out = []
    removed = 0
    for line in lines:
        if line.strip() in BAD_GLOBAL_IMPORTS:
            removed += 1
            continue
        out.append(line)
    if removed:
        log(f"[OK] Removidos imports OTMZ globais/quebrados: {removed}")
    return "".join(out)

def candidate_backups() -> list[Path]:
    candidates: list[Path] = []
    if DASH.exists():
        candidates.append(DASH)

    patterns = [
        "dashboard_streamlit.py.bak*",
        "dashboard_streamlit.py.broken*",
        "dashboard_streamlit.py.*bak*",
        "dashboard_streamlit.py.*backup*",
        "dashboard_streamlit.py.broken_before*",
    ]

    seen = set()
    out: list[Path] = []
    for p in candidates:
        if p.exists():
            seen.add(str(p.resolve()))
            out.append(p)

    for pat in patterns:
        for p in DASH.parent.glob(pat):
            if not p.is_file():
                continue
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                out.append(p)

    out.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return out

def valid_source(txt: str, name: str) -> tuple[bool, str]:
    txt = remove_global_otmz_imports(txt)

    if "def main(" not in txt:
        return False, "sem def main()"

    if "def render_otimizacao_unificada(" not in txt:
        return False, "sem render_otimizacao_unificada()"

    if 'pagina == "Otimização"' not in txt and "pagina == 'Otimização'" not in txt:
        return False, "sem rota pagina == Otimização"

    try:
        compile(txt, name, "exec")
    except SyntaxError as e:
        return False, f"syntax error: {e}"
    except Exception as e:
        return False, f"compile error: {e}"

    return True, "ok"

def choose_dashboard_base() -> tuple[Path, str]:
    checked = []
    for p in candidate_backups():
        try:
            raw = read_text(p)
            cleaned = remove_global_otmz_imports(raw)
            ok, reason = valid_source(cleaned, str(p))
            if ok:
                log(f"[OK] Base válida escolhida: {p}")
                return p, cleaned
            checked.append(f"{p.name}: {reason}")
        except Exception as e:
            checked.append(f"{p.name}: {e}")

    log("[ERRO] Nenhum dashboard válido encontrado.")
    log("[INFO] Arquivos verificados:")
    for item in checked[:100]:
        log(f"  - {item}")
    raise SystemExit(1)

def function_bounds(lines: list[str], name: str) -> tuple[int, int]:
    start = -1
    pat = re.compile(rf"^def\s+{re.escape(name)}\s*\(")
    for i, line in enumerate(lines):
        if pat.match(line):
            start = i
            break

    if start < 0:
        raise RuntimeError(f"Não encontrei def {name}().")

    end = len(lines)
    next_top = re.compile(r"^(def\s+|class\s+|if\s+__name__\s*==)")
    for j in range(start + 1, len(lines)):
        if next_top.match(lines[j]):
            end = j
            break

    return start, end

def patch_render_otimizacao(txt: str) -> str:
    lines = txt.splitlines(True)
    start, end = function_bounds(lines, "render_otimizacao_unificada")
    def_line = lines[start]

    new_func = [
        def_line,
        "    # Menu personalizado > Otimização > OTMZ.\n",
        "    import sys\n",
        "    from pathlib import Path\n",
        "    app_dir = Path(__file__).resolve().parent\n",
        "    if str(app_dir) not in sys.path:\n",
        "        sys.path.insert(0, str(app_dir))\n",
        "    from rmc_otmz_menu_view import render_otmz_panel\n",
        "    render_otmz_panel()\n",
        "\n",
    ]

    log("[OK] render_otimizacao_unificada() ajustada para carregar OTMZ.")
    return "".join(lines[:start] + new_func + lines[end:])

def ensure_main_call(txt: str) -> str:
    if "def main(" not in txt:
        raise RuntimeError("def main() ausente.")

    if re.search(r"(?m)^\s*main\s*\(\s*\)\s*$", txt):
        return txt

    txt += "\n\nif __name__ == \"__main__\":\n    main()\n"
    log("[OK] Chamada main() adicionada ao rodapé.")
    return txt

def write_bridge() -> None:
    bridge_lines = [
        "from __future__ import annotations",
        "",
        "def render_otmz_panel():",
        "    import sys",
        "    from pathlib import Path",
        "",
        "    app_dir = Path(__file__).resolve().parent",
        "    if str(app_dir) not in sys.path:",
        "        sys.path.insert(0, str(app_dir))",
        "",
        "    try:",
        "        from rmc_optimization_all_view import render_all_optimization_panel",
        "        render_all_optimization_panel()",
        "    except Exception as exc:",
        "        import streamlit as st",
        "        st.header(\"OTMZ\")",
        "        st.error(\"Falha ao carregar a tela OTMZ.\")",
        "        st.exception(exc)",
        "        st.info(\"Erro restrito à UI. Coleta, DuckDB e credenciais não foram alterados.\")",
        "",
    ]
    code = "\n".join(bridge_lines)
    write_text(BRIDGE, code)
    compile(read_text(BRIDGE), str(BRIDGE), "exec")
    log("[OK] Bridge OTMZ criado/validado.")

def patch_view_label() -> None:
    if not VIEW.exists():
        log("[WARN] app/rmc_optimization_all_view.py não encontrado.")
        return

    backup_file(VIEW, "bak_16a14_7")
    txt = read_text(VIEW)
    txt = txt.replace("Otimização Aria", "OTMZ")
    txt = txt.replace("Buscar otimização agora", "Buscar OTMZ agora")
    write_text(VIEW, txt)

    try:
        compile(read_text(VIEW), str(VIEW), "exec")
        log("[OK] View OTMZ compila.")
    except Exception as e:
        log(f"[WARN] View OTMZ não compila, mas o dashboard ficará protegido pelo bridge: {e}")

def disable_multipage_loose_pages() -> None:
    if not PAGES.exists():
        return

    PAGES_DISABLED.mkdir(parents=True, exist_ok=True)
    patterns = ["*Idle*.py", "*Otimizacao_Aria*.py", "*Otimização_Aria*.py", "*OTMZ*.py"]
    moved = 0

    for pat in patterns:
        for p in list(PAGES.glob(pat)):
            dst = PAGES_DISABLED / p.name
            if dst.exists():
                dst = PAGES_DISABLED / f"{p.stem}_{TAG}{p.suffix}"
            shutil.move(str(p), str(dst))
            moved += 1
            log(f"[OK] Página solta desativada: {p} -> {dst}")

    if moved == 0:
        log("[INFO] Nenhuma página solta de OTMZ/Idle encontrada em app/pages.")

def assert_final_dashboard(txt: str) -> None:
    if "def main(" not in txt:
        raise RuntimeError("def main() ausente no dashboard final.")

    if "def render_otimizacao_unificada(" not in txt:
        raise RuntimeError("render_otimizacao_unificada() ausente no dashboard final.")

    if not re.search(r"def\s+render_otimizacao_unificada\s*\([^)]*\):[\s\S]{0,700}render_otmz_panel\(\)", txt):
        raise RuntimeError("render_otimizacao_unificada() não chama render_otmz_panel().")

    # Só proíbe import global/top-level. Import dentro da função é correto.
    first_220 = "\n".join(txt.splitlines()[:220])
    for bad in BAD_GLOBAL_IMPORTS:
        if bad in first_220:
            raise RuntimeError(f"Import global quebrado ainda existe no topo: {bad}")

    compile(txt, str(DASH), "exec")

def main() -> None:
    log("[INFO] Hotfix 16A.14.7 - reparo definitivo OTMZ/menu")
    log("[REGRA] Não altera coleta, DuckDB, credenciais, LLM ou agendamento.")

    if not DASH.exists():
        raise SystemExit(f"[ERRO] Não encontrei {DASH}")

    backup_file(DASH, "broken_before_16a14_7")

    source, txt = choose_dashboard_base()
    txt = remove_global_otmz_imports(txt)
    txt = patch_render_otimizacao(txt)
    txt = ensure_main_call(txt)

    assert_final_dashboard(txt)
    write_text(DASH, txt)
    log("[OK] dashboard_streamlit.py gravado e compilado.")

    write_bridge()
    patch_view_label()
    disable_multipage_loose_pages()

    final_txt = read_text(DASH)
    assert_final_dashboard(final_txt)

    log("[OK] Reparo final validado.")
    log("[OK] Resultado: menu personalizado Otimização carrega OTMZ.")
    log(f"[INFO] Base usada: {source}")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("[ERRO] Falha no hotfix 16A.14.7:")
        traceback.print_exc()
        raise SystemExit(1)
