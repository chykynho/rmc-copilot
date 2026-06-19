param(
    [Parameter(Mandatory=$true)][string]$Solicitacao,
    [Parameter(Mandatory=$true)][string]$VM,
    [string]$Resources = "CPU,MEM,DISK",
    [string]$Partitions = "C:",
    [int]$Periodo = 90,
    [string]$Solicitante = "",
    [string]$Analista = "Francisco Alves",
    [string]$Classificacao = "PÚBLICO",
    [string]$RunId = "",
    [string]$VmResourceId = ""
)

$ErrorActionPreference = "Stop"

$argsList = @(
    "-m", "rmc_copilot.resource_analysis.generate_resource_analysis_consolidated_v1",
    "--source", "duckdb",
    "--solicitacao", $Solicitacao,
    "--vm", $VM,
    "--resources", $Resources,
    "--partitions", $Partitions,
    "--periodo", $Periodo,
    "--solicitante", $Solicitante,
    "--analista", $Analista,
    "--classificacao", $Classificacao,
    "--formats", "md,docx,pdf",
    "--zip"
)

if ($RunId -ne "") { $argsList += @("--run-id", $RunId) }
if ($VmResourceId -ne "") { $argsList += @("--vm-resource-id", $VmResourceId) }

python @argsList
