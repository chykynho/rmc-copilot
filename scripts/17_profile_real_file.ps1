param(
    [Parameter(Mandatory=$true)][string]$InputFile,
    [string]$Out = ".\outputs\profile_real.json"
)

python .\src\rmc_data\profile_capacity_file.py --input $InputFile --out $Out
