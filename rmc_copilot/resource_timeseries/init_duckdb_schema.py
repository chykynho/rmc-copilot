from __future__ import annotations

import argparse
from pathlib import Path

from .duckdb_repository import create_resource_timeseries_schema, inspect_resource_timeseries_schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicializa as tabelas granulares de recursos no DuckDB oficial do RMC Copilot.")
    parser.add_argument("--db", default=None, help="Caminho do DuckDB. Default: rmc_copilot.config.DATABASE_PATH")
    args = parser.parse_args()

    create_resource_timeseries_schema(args.db)
    print("Schema granular de recursos inicializado com sucesso.")
    if args.db:
        print(f"Banco: {Path(args.db)}")

    info = inspect_resource_timeseries_schema(args.db)
    for key, df in info.items():
        if key.endswith("__count"):
            print(f"{key}: {df.iloc[0, 0]}")


if __name__ == "__main__":
    main()
