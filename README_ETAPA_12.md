# RMC Copilot LLM - Etapa 12

## Objetivo

A Etapa 12 prepara o assistente Data+RAG para trabalhar com arquivos reais do RMC Copilot, mesmo quando os nomes das colunas não forem iguais aos nomes usados no CSV de exemplo.

Ela adiciona:

- profiler de arquivos reais;
- normalizador de schema;
- validação de colunas mínimas;
- geração de CSV normalizado;
- suporte a CSV, Parquet, DuckDB e XLSX;
- chat Data+RAG v3 usando arquivo normalizado;
- avaliação Data+RAG v3.

## Arquivos adicionados

```text
src/rmc_data/schema_aliases.py
src/rmc_data/profile_capacity_file.py
src/rmc_data/normalize_capacity_file_v1.py
src/rmc_data/validate_real_data_v1.py
src/rmc_rag/chat_data_rag_v3.py
src/rmc_rag/evaluate_data_rag_v3.py
docs/tecnicos/rmc_schema_real_data_etapa12.md
eval/rmc_data_questions_v3.jsonl
scripts/17_profile_real_file.ps1
scripts/18_normalize_real_file.ps1
scripts/19_validate_real_data.ps1
scripts/20_chat_data_rag_v3.ps1
scripts/21_eval_data_rag_v3.ps1
requirements-data-etapa12.txt
```

## Fluxo recomendado

### 1. Instalar dependências

```powershell
pip install -r requirements-data-etapa12.txt
```

### 2. Criar perfil do arquivo real

Exemplo com o CSV de amostra:

```powershell
python .\src\rmc_data\profile_capacity_file.py --input .\data\sample\rmc_capacity_realistic.csv --out .\outputs\profile_capacity_sample.json
```

Exemplo com arquivo real:

```powershell
python .\src\rmc_data\profile_capacity_file.py --input "C:\CAMINHO\SEU_ARQUIVO_REAL.csv" --out .\outputs\profile_real.json
```

### 3. Normalizar o arquivo

```powershell
python .\src\rmc_data\normalize_capacity_file_v1.py --input .\data\sample\rmc_capacity_realistic.csv --out .\outputs\capacity_normalized.csv
```

### 4. Validar dados normalizados

```powershell
python .\src\rmc_data\validate_real_data_v1.py --input .\outputs\capacity_normalized.csv --out .\outputs\capacity_validation.json
```

### 5. Usar no chat Data+RAG v3

```powershell
python .\src\rmc_rag\chat_data_rag_v3.py --data .\outputs\capacity_normalized.csv --index .\rag_index --model gemma3:1b --question "Quais objetos têm forecast de disco em 30 dias?" --mode safe
```

### 6. Avaliar

```powershell
python .\src\rmc_rag\evaluate_data_rag_v3.py --data .\outputs\capacity_normalized.csv --index .\rag_index --model gemma3:1b --questions .\eval\rmc_data_questions_v3.jsonl --prompt .\prompts\rmc_system_prompt_v4.md --out .\outputs\data_rag_eval_results_v3.jsonl --mode safe --show-failures
```

## Observação

A Etapa 12 não altera a lógica que passou em 100% na Etapa 11.1. Ela apenas adiciona uma camada antes:

```text
arquivo real
↓
profile
↓
normalização de schema
↓
validação
↓
Data+RAG
```
