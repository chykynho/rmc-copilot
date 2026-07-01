from __future__ import annotations

import os
import re

SERVICE = "RMC_COPILOT_ARIA_UI"
USER_TOKEN = "secureToken"
USER_COOKIE = "cookie"

def sanitize_cookie(raw: str) -> str:
    s = str(raw or "").strip().replace("\ufeff", "").strip()

    # Copy as cURL / header completo.
    m = re.search(r'(?is)(?:-H\s+)?[\'"]?Cookie\s*:\s*([^\'"\r\n]+)', s)
    if m:
        s = m.group(1).strip()

    # Linha simples "Cookie: ..."
    s = re.sub(r'(?is)^\s*Cookie\s*:\s*', '', s).strip()

    # Aspas e espaços.
    s = s.strip().strip('"').strip("'").strip()

    # Remove quebras de linha e normaliza separadores.
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s*;\s*', '; ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # Se vier junto com outros headers, corta antes deles.
    for marker in [" Authorization:", " X-CSRF", " Bearer ", " Sec-Fetch", " User-Agent:", " Accept:"]:
        idx = s.lower().find(marker.lower())
        if idx > 0:
            s = s[:idx].strip().rstrip(";").strip()

    return s

def sanitize_token(raw: str) -> str:
    s = str(raw or "").strip().replace("\ufeff", "").strip()

    # Payload inteiro: ...&secureToken=uuid
    m = re.search(r'(?i)(?:^|[&\s])secureToken=([a-f0-9-]{20,})', s)
    if m:
        return m.group(1).strip()

    # JSON/HTML.
    m = re.search(r'(?i)secureToken["\']?\s*[:=]\s*["\']?([a-f0-9-]{20,})', s)
    if m:
        return m.group(1).strip()

    return s.strip().strip('"').strip("'")

def main() -> int:
    try:
        import keyring
    except Exception as e:
        raise SystemExit(f"[ERRO] keyring não instalado: {e}")

    token = sanitize_token(os.environ.get("RMC_ARIA_SECURE_TOKEN_IN", ""))
    cookie = sanitize_cookie(os.environ.get("RMC_ARIA_COOKIE_IN", ""))

    if not token:
        raise SystemExit("[ERRO] secureToken vazio. Copie o secureToken para a área de transferência e rode novamente.")
    if len(token) < 20:
        raise SystemExit("[ERRO] secureToken parece curto/inválido.")

    if not cookie:
        raise SystemExit("[ERRO] Cookie vazio. Copie o Cookie de Headers > Request Headers para a área de transferência e rode novamente.")
    if len(cookie) < 20 or "=" not in cookie:
        raise SystemExit("[ERRO] Cookie parece inválido/curto. Copie o Cookie completo de Headers > Request Headers.")
    if "cookie:" in cookie.lower() or "\n" in cookie or "\r" in cookie:
        raise SystemExit("[ERRO] Cookie ainda contém prefixo ou quebra de linha.")

    keyring.set_password(SERVICE, USER_TOKEN, token)
    keyring.set_password(SERVICE, USER_COOKIE, cookie)

    print("[OK] Segredos salvos no Windows Credential Manager.")
    print(f"[INFO] Cookie: {len(cookie)} caracteres, pares_aprox={cookie.count(';') + 1}")
    print(f"[INFO] secureToken: {len(token)} caracteres")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
