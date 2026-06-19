from __future__ import annotations

import argparse
import getpass
from dataclasses import dataclass
from typing import Optional

try:
    import keyring
except Exception:  # pragma: no cover
    keyring = None

SERVICE_PREFIX = "rmc_copilot"


@dataclass
class CredentialRef:
    system: str
    username: str

    @property
    def service_name(self) -> str:
        return f"{SERVICE_PREFIX}_{self.system}"


def require_keyring() -> None:
    if keyring is None:
        raise RuntimeError("Biblioteca keyring não instalada. Instale com: pip install keyring")


def set_password(system: str, username: str, password: str) -> None:
    require_keyring()
    ref = CredentialRef(system=system, username=username)
    keyring.set_password(ref.service_name, username, password)


def get_password(system: str, username: str) -> Optional[str]:
    require_keyring()
    ref = CredentialRef(system=system, username=username)
    return keyring.get_password(ref.service_name, username)


def delete_password(system: str, username: str) -> None:
    require_keyring()
    ref = CredentialRef(system=system, username=username)
    keyring.delete_password(ref.service_name, username)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gerencia credenciais do RMC Copilot no Windows Credential Manager/keyring.")
    p.add_argument("action", choices=["set", "get", "delete"], help="Ação")
    p.add_argument("--system", required=True, choices=["vrops", "vcenter"], help="Sistema alvo")
    p.add_argument("--username", required=True, help="Usuário")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "set":
        password = getpass.getpass("Senha/token: ")
        set_password(args.system, args.username, password)
        print(f"Credencial salva no keyring: sistema={args.system}, usuário={args.username}")
    elif args.action == "get":
        password = get_password(args.system, args.username)
        print("Credencial encontrada." if password else "Credencial não encontrada.")
    elif args.action == "delete":
        delete_password(args.system, args.username)
        print(f"Credencial removida: sistema={args.system}, usuário={args.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
