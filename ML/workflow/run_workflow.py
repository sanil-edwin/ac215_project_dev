import subprocess, sys, click

def sh(cmd):
    print("$ " + " ".join(cmd))
    res = subprocess.run(cmd, check=True)
    return res.returncode

@click.command()
@click.option("--start-year", type=int, default=2020)
@click.option("--end-year", type=int, default=2024)
@click.option("--sample", is_flag=True)
def main(start_year, end_year, sample):
    ingest_cmd = ["docker","compose","run","--rm","data-ingestion","python","src/download_yield_data.py","--start-year",str(start_year),"--end-year",str(end_year)]
    if sample: ingest_cmd.append("--sample")

    preprocess_cmd = ["docker","compose","run","--rm","data-prepocessing","python","src/preprocess.py"]

    stress_cmd = ["docker","compose","run","--rm","model-stress-detection","python","src/train_stress.py","--save","/app/data/models/stress","--write-summaries","/app/data/summaries","--write-drivers","/app/data/drivers"]

    yield_cmd = ["docker","compose","run","--rm","model-yield-forcasting","python","src/train_yield.py","--save","/app/data/models/yield"]

    for name, cmd in [("Ingestion", ingest_cmd), ("Preprocess", preprocess_cmd), ("Stress model", stress_cmd), ("Yield model", yield_cmd)]:
        print(f"\n=== {name} ===")
        try: sh(cmd)
        except subprocess.CalledProcessError as e:
            print(f"❌ {name} failed ({e.returncode})", file=sys.stderr); sys.exit(e.returncode)

    print("\n✅ Workflow complete.")

if __name__ == "__main__":
    main()
