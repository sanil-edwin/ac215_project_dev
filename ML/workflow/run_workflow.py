import subprocess, sys, click
from pathlib import Path

COMPOSE_FILE = "/repo/compose.yaml"  # robust even if working_dir isn't the repo root

def sh(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

@click.command()
@click.option("--start-year", type=int, default=2015, show_default=True)
@click.option("--end-year", type=int, default=2024, show_default=True)
@click.option("--sample/--no-sample", default=True, help="Use sample data for ingestion")
@click.option("--verbose", is_flag=True, help="Pass --verbose to trainers")
def main(start_year: int, end_year: int, sample: bool, verbose: bool):
    print("\n=== Ingestion ===")
    ingest_cmd = [
        "docker","compose","-f",COMPOSE_FILE,"run","--rm","data-ingestion",
        "python","src/download_yield_data.py",
        "--start-year",str(start_year),"--end-year",str(end_year)
    ]
    if sample:
        ingest_cmd.append("--sample")
    sh(ingest_cmd)
    print("\n=== Preprocessing ===")
    sh([
        "docker","compose","-f",COMPOSE_FILE,"run","--rm","data-preprocessing",
        "python","src/preprocess_data.py"
    ])
    print("\n=== Stress model ===")
    stress_cmd = [
        "docker","compose","-f",COMPOSE_FILE,"run","--rm","model-stress-detection",
        "python","src/train_model.py"
    ]
    if verbose:
        stress_cmd.append("--verbose")
    sh(stress_cmd)
    print("\n=== Yield model ===")
    yield_cmd = [
        "docker","compose","-f",COMPOSE_FILE,"run","--rm","model-yield-forecasting",
        "python","src/train_model.py"
    ]
    if verbose:
        yield_cmd.append("--verbose")
    sh(yield_cmd)
    print("\n✅ Workflow complete.")

if __name__ == "__main__":
    main()
