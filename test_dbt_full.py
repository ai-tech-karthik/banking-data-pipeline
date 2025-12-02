#!/usr/bin/env python3
"""Test the complete DBT pipeline"""
import subprocess
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir('dbt_project')

print("=" * 70)
print("TEST 1: Running Complete DBT Pipeline")
print("=" * 70)

steps = [
    ("Cleaning previous run", "dbt clean"),
    ("Installing dependencies", "dbt deps"),
    ("Compiling models", "dbt compile --target prod"),
    ("Running all models", "dbt run --target prod"),
    ("Running snapshots", "dbt snapshot --target prod"),
    ("Running tests", "dbt test --target prod"),
]

results = []

for step_name, command in steps:
    print(f"\n{'='*70}")
    print(f"Step: {step_name}")
    print(f"Command: {command}")
    print('='*70)
    
    result = subprocess.run(
        command.split(),
        capture_output=True,
        text=True
    )
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Track results
    success = result.returncode == 0
    results.append((step_name, success))
    
    if not success:
        print(f"❌ {step_name} FAILED with return code {result.returncode}")
        break
    else:
        print(f"✅ {step_name} PASSED")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
for step_name, success in results:
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"{step_name}: {status}")

all_passed = all(success for _, success in results)
print("\n" + "=" * 70)
if all_passed:
    print("🎉 ALL DBT TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 70)

sys.exit(0 if all_passed else 1)
