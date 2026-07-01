from __future__ import annotations

import getpass
import sys
import re

SERVICE = "RMC_COPILOT_ARIA_UI"
USER_TOKEN = "secureToken"
USER_COOKIE = "cookie"


def sanitize_cookie(raw: str) -> str:
    s = str(raw or "").strip().replace("\ufeff", "").strip()
    m = re.search(r'(?is)(?:-H\s+)?[\'"]?Cookie\s*:\s*([^\'"\r\n]+)', s)
    if m:
        s = m.group(1).strip()
    s = re.sub(r'(?is)^\s*Cookie\s*:\s*', '', s).strip()
    s = s.strip().strip('"').strip("'").strip()
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s*;\s*', '; ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def sanitize_token(raw: str) -> str:
    s = str(raw or "").strip().replace("\ufeff", "").strip()
    m = re.search(r'(?i)(?:^|[&\s])secureToken=([a-f0-9-]{20,})', s)
    if m:
        return m.group(1).strip()
    m = re.search(r'(?i)secureToken["\']?\s*[:=]\s*["\']?([a-f0-9-]{20,})', s)
    if m:
        return m.group(1).strip()
    return s.strip().strip('"').strip("'")


def main():
    try:
        import keyring
    except Exception as e:
        raise SystemExit(f"[ERRO] keyring não instalado: {e}\nRode scripts\\199_install_secure_optimization_deps.ps1")

    print("[INFO] Salvando segredos no Windows Credential Manager via keyring.")
    print("[SEGURANCA] Nada será salvo em arquivo texto.")
    print("[SEGURANCA] O valor digitado não aparecerá no console.")

    token = sanitize_token(getpass.getpass("Cole o secureToken: "))
    cookie = sanitize_cookie(getpass.getpass("Cole o Cookie: "))

    if not token:
        raise SystemExit("[ERRO] secureToken vazio.")
    if not cookie:
        raise SystemExit("[ERRO] Cookie vazio.")

    if any(x in cookie.lower() for x in ['cookie:', '\\r', '\\n', '-h ']):
        raise SystemExit('[ERRO] Cookie contém prefixo/header/cURL. Cole somente o valor depois de Cookie:.')
    if len(cookie) < 20 or '=' not in cookie:
        raise SystemExit('[ERRO] Cookie parece inválido/curto. Copie o Cookie completo de Headers > Request Headers.')

    keyring.set_password(SERVICE, USER_TOKEN, token)
    keyring.set_password(SERVICE, USER_COOKIE, cookie)

    print(f"[OK] secureToken e Cookie salvos no cofre do Windows. Cookie={len(cookie)} caracteres, pares_aprox={cookie.count(';') + 1}")
    print("[INFO] Serviço:", SERVICE)
    print("[INFO] Itens:", USER_TOKEN, USER_COOKIE)

if __name__ == "__main__":
    main()
