param(
    [string]$InputFile = ".\outputs\capacity_normalized.csv",
    [string]$Out = ".\outputs\capacity_validation.json"
)

python .\src\rmc_data\validate_real_data_v1.py --input $InputFile --out $Out
