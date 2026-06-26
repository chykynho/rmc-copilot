param(
    [Parameter(Mandatory=$true)][string]$Question,
    [string]$Data = ".\outputs\capacity_normalized.csv",
    [string]$Mode = "safe"
)

python .\src\rmc_rag\chat_data_rag_v3.py --data $Data --index .\rag_index --model gemma3:1b --question $Question --mode $Mode --limit 15
