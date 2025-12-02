#!/usr/bin/env python3
"""Test the complete pipeline using Dagster"""
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("TEST 2: Running Complete Pipeline via Dagster")
print("=" * 70)

print("\nMaterializing all assets...")
result = subprocess.run(
    [
        "dagster", "asset", "materialize",
        "--select", "*",
        "-m", "src.lending_club_pipeline.definitions"
    ],
    capture_output=True,
    text=True,
    env={**subprocess.os.environ, "DAGSTER_HOME": subprocess.os.environ.get("DAGSTER_HOME", "dagster_home")}
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n" + "=" * 70)
if result.returncode == 0:
    print("✅ DAGSTER PIPELINE COMPLETED SUCCESSFULLY!")
else:
    print(f"❌ DAGSTER PIPELINE FAILED with return code {result.returncode}")
print("=" * 70)

sys.exit(result.returncode)
