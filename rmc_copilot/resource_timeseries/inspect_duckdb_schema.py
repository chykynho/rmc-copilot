from __future__ import annotations

import argparse

import duckdb

try:
    from rmc_copilot.config import DATABASE_PATH
except Exception:  # pragma: no cover
    DATABASE_PATH = "data/database/rmc_copilot.duckdb"

from .duckdb_repository import create_resource_timeseries_schema, RESOURCE_TABLES


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspeciona tabelas granulares de recursos no DuckDB.")
    parser.add_argument("--db", default=str(DATABASE_PATH), help="Caminho do DuckDB")
    args = parser.parse_args()

    create_resource_timeseries_schema(args.db)
    con = duckdb.connect(args.db)
    print("BANCO:", args.db)
    print("\nTABELAS:")
    print(con.execute("SHOW TABLES").df().to_string(index=False))

    for table in RESOURCE_TABLES:
        print("\n" + "=" * 80)
        print(table)
        print("\nCOLUNAS:")
        print(con.execute(f"DESCRIBE {table}").df().to_string(index=False))
        print("\nTOTAL:")
        print(con.execute(f"SELECT COUNT(*) AS linhas FROM {table}").df().to_string(index=False))
        try:
            print("\nAMOSTRA:")
            print(con.execute(f"SELECT * FROM {table} LIMIT 5").df().to_string(index=False))
        except Exception as exc:
            print("Sem amostra:", exc)
    con.close()


if __name__ == "__main__":
    main()
