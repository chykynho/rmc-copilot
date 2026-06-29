param(
    [string]$VropsHost = "mor-vropsprd01.bvnet.bv",
    [string]$AuthSource = "bvnet.bv",
    [string]$Cluster = "ALL",
    [string]$Username = "",
    [string]$DbPath = "data\database\rmc_copilot.duckdb",
    [int]$MaxVms = 0,
    [string]$OrphanCsv = "",
    [switch]$SaveCredential,
    [switch]$UseSavedCredential,
    [string]$SecretPath = "data\secrets\vrops_credential.xml"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$LogDir = "data\logs\coletas"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("coleta_otimizacao_16a_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8
}

$Python = ".\.rmcllm\Scripts\python.exe"
if (!(Test-Path $Python)) { $Python = "python" }

$SecretDir = Split-Path $SecretPath -Parent
if (![string]::IsNullOrWhiteSpace($SecretDir)) { New-Item -ItemType Directory -Force -Path $SecretDir | Out-Null }

if ($UseSavedCredential) {
    if (!(Test-Path $SecretPath)) { throw "Credencial salva não encontrada: $SecretPath" }
    $cred = Import-Clixml -Path $SecretPath
    $Username = $cred.UserName
    $SecurePassword = $cred.Password
} else {
    if ([string]::IsNullOrWhiteSpace($Username)) { $Username = Read-Host "Usuário vROps" }
    $SecurePassword = Read-Host "Senha vROps" -AsSecureString
}

if ($SaveCredential) {
    $cred = New-Object System.Management.Automation.PSCredential($Username, $SecurePassword)
    $cred | Export-Clixml -Path $SecretPath
    Write-Log "[OK] Credencial vROps salva com DPAPI em $SecretPath"
}

$BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
try { $PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($BSTR) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR) }

$env:RMC_VROPS_PASSWORD = $PlainPassword
$env:PYTHONIOENCODING = "utf-8"

$argsPy = @(
    ".\scripts\161_collect_optimization_vrops.py",
    "--host", $VropsHost,
    "--auth-source", $AuthSource,
    "--username", $Username,
    "--cluster", $Cluster,
    "--db", $DbPath,
    "--max-vms", $MaxVms
)
if (![string]::IsNullOrWhiteSpace($OrphanCsv)) { $argsPy += @("--orphan-csv", $OrphanCsv) }

Write-Log "[INICIO] Coleta de Otimização 16A | host=$VropsHost | cluster=$Cluster | max_vms=$MaxVms"
Write-Log "[REGRA] A IA/coleta não executa ação operacional; apenas registra dados para relatório e recomendação."
$Output = & $Python @argsPy 2>&1
$ExitCode = $LASTEXITCODE
$Output | Tee-Object -FilePath $Log -Append
Remove-Item Env:\RMC_VROPS_PASSWORD -ErrorAction SilentlyContinue

if ($ExitCode -ne 0) {
    Write-Log "[ERRO] Coleta falhou com codigo $ExitCode"
    exit $ExitCode
}
Write-Log "[FIM] Log: $Log"
