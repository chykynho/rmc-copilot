# Etapa 15-C.1 — Hotfix import Streamlit

## Problema corrigido

Ao rodar a página diretamente:

```powershell
streamlit run .\app\pages\resource_analysis.py
```

o Streamlit não encontrava o pacote `rmc_copilot`, gerando:

```text
ModuleNotFoundError: No module named 'rmc_copilot'
```

## Correção

A página `app/pages/resource_analysis.py` agora adiciona a raiz do projeto ao `sys.path` antes dos imports:

```python
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

## Aplicação

Extraia este patch na raiz do projeto principal:

```text
C:\Projetos\rmc_copilot
```

Depois rode:

```powershell
streamlit run .\app\pages\resource_analysis.py
```

## Observação

Este hotfix não altera lógica de relatório. Apenas corrige a descoberta do pacote Python quando a página é aberta isoladamente pelo Streamlit.
