from __future__ import annotations

import argparse

from .duckdb_repository import migrate_legacy_historico_vm_metricas


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra historico_vm_metricas para vm_resource_timeseries.")
    parser.add_argument("--db", default=None, help="Caminho do DuckDB. Default: rmc_copilot.config.DATABASE_PATH")
    parser.add_argument("--execution-id", default=None, help="Execution_id específico. Se omitido, migra todos.")
    parser.add_argument("--no-replace", action="store_true", help="Não apaga registros migrados anteriormente do mesmo run_id.")
    args = parser.parse_args()

    summary = migrate_legacy_historico_vm_metricas(
        db_path=args.db,
        execution_id=args.execution_id,
        replace=not args.no_replace,
    )

    if summary.empty:
        print("Nenhum dado encontrado em historico_vm_metricas para migrar.")
    else:
        print("Migração concluída.")
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
