param(
    [string]$Data = ".\outputs\capacity_normalized.csv"
)

python .\src\rmc_rag\evaluate_data_rag_v3.py --data $Data --index .\rag_index --model gemma3:1b --questions .\eval\rmc_data_questions_v3.jsonl --prompt .\prompts\rmc_system_prompt_v4.md --out .\outputs\data_rag_eval_results_v3.jsonl --mode safe --show-failures
