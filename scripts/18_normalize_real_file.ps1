param(
    [Parameter(Mandatory=$true)][string]$InputFile,
    [string]$Out = ".\outputs\capacity_normalized.csv"
)

python .\src\rmc_data\normalize_capacity_file_v1.py --input $InputFile --out $Out --profile-out ".\outputs\capacity_normalization_profile.json"
