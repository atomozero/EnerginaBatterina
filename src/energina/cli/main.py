"""Entry point CLI: energina run config.yaml"""

import argparse
import sys
from pathlib import Path

from energina.core.logging_config import setup_logging


def main():
    """Entry point principale."""
    parser = argparse.ArgumentParser(
        prog="energina",
        description="EnerginaBatterina - Piattaforma trading energia rinnovabile",
    )
    subparsers = parser.add_subparsers(dest="comando", help="Comandi disponibili")

    # Comando: run
    run_parser = subparsers.add_parser("run", help="Esegui pipeline completa")
    run_parser.add_argument(
        "config",
        type=Path,
        help="Percorso file configurazione YAML",
    )
    run_parser.add_argument(
        "--resume", action="store_true",
        help="Riprendi da checkpoint precedente",
    )
    run_parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Livello di logging (default: INFO)",
    )

    # Comando: valida
    valida_parser = subparsers.add_parser("valida", help="Valida file di configurazione")
    valida_parser.add_argument("config", type=Path, help="Percorso file configurazione YAML")

    args = parser.parse_args()

    if args.comando is None:
        parser.print_help()
        sys.exit(0)

    if args.comando == "run":
        cmd_run(args)
    elif args.comando == "valida":
        cmd_valida(args)


def cmd_run(args):
    """Esegui pipeline completa."""
    setup_logging(args.log_level)

    if not args.config.exists():
        print(f"Errore: file non trovato: {args.config}")
        sys.exit(1)

    from energina.core.direttore import Direttore

    try:
        direttore = Direttore(args.config)
        risultati = direttore.esegui(resume=args.resume)

        # Stampa riepilogo
        print("\n" + "=" * 60)
        print("  RIEPILOGO RISULTATI")
        print("=" * 60)

        if "contatore" in risultati:
            riep = risultati["contatore"].get("riepilogo", {})
            print(f"\n  Produzione annua:    {riep.get('produzione_annua_kwh', 'N/D'):>10} kWh")
            print(f"  Consumo annuo:       {riep.get('consumo_annuo_kwh', 'N/D'):>10} kWh")
            print(f"  Autoconsumo:         {riep.get('autoconsumo_pct', 'N/D'):>10}%")
            print(f"  Autosufficienza:     {riep.get('autosufficienza_pct', 'N/D'):>10}%")

        if "economico" in risultati:
            ind = risultati["economico"].get("indicatori", {})
            print(f"\n  NPV:                 {ind.get('npv_eur', 'N/D'):>10} EUR")
            irr = ind.get('irr_pct')
            irr_str = f"{irr}%" if irr is not None else "N/C"
            print(f"  IRR:                 {irr_str:>10}")
            print(f"  Payback:             {ind.get('payback_semplice_anni', 'N/D'):>10} anni")
            print(f"  ROI:                 {ind.get('roi_pct', 'N/D'):>10}%")
            print(f"  LCOE:                {ind.get('lcoe_eur_kwh', 'N/D'):>10} EUR/kWh")

        if "report" in risultati:
            path = risultati["report"].get("riepilogo", {}).get("percorso_report", "")
            if path:
                print(f"\n  Report: {path}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\nErrore: {e}")
        sys.exit(1)


def cmd_valida(args):
    """Valida file di configurazione."""
    import yaml

    if not args.config.exists():
        print(f"Errore: file non trovato: {args.config}")
        sys.exit(1)

    try:
        with open(args.config, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        campi_richiesti = ["meteo", "fotovoltaico", "edificio"]
        mancanti = [c for c in campi_richiesti if c not in config]
        if mancanti:
            print(f"Attenzione: sezioni mancanti: {', '.join(mancanti)}")

        print(f"Configurazione valida: {args.config}")
        print(f"  Progetto: {config.get('progetto', {}).get('nome', 'N/D')}")
        print(f"  Sezioni: {', '.join(config.keys())}")

    except yaml.YAMLError as e:
        print(f"Errore YAML: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
