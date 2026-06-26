$ErrorActionPreference = "Stop"
Write-Host "[INFO] Stage seletivo do Hotfix 15F.10.34" -ForegroundColor Cyan

git status --short

git add app\dashboard_streamlit.py
git add scripts\147_validate_analise_individual_vm_sem_erros.py
git add scripts\147_validate_analise_individual_vm_sem_erros.ps1
git add scripts\148_git_push_hotfix_15f_10_34.ps1
git add README_HOTFIX_15F_10_34.md
git add MARCO_15F_10_34_ANALISE_INDIVIDUAL_VM_SEM_ERROS.md
git add docs\tecnicos\rmc_analise_individual_vm_sem_erros_15f10_34.md

git status --short

git commit -m "Hotfix 15F.10.34 - corrige relatorio da analise individual de VM"
git push origin main
