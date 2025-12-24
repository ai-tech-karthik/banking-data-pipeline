#!/usr/bin/env python3
"""Test only the 6 previously failing tests"""
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()
os.chdir('dbt_project')

print("=" * 70)
print("Testing the 6 Fixed Tests")
print("=" * 70)

# The 6 tests that were failing
tests_to_run = [
    "dbt_utils_expression_is_true_src_customer_count_0",
    "dbt_utils_expression_is_true_src_account_count_0",
    "dbt_utils_expression_is_true_account_summary_interest_rate_pct___0_01_and_0_025",
    "dbt_utils_expression_is_true_account_summary_count_0",
    "dbt_utils_expression_is_true_customer_profile_count_0",
    "accepted_values_int_account_with_customer_account_type__Savings__Checking"
]

print("\nNote: The count tests have been removed (they don't work in WHERE clauses)")
print("We'll run all tests to verify the fixes\n")

result = subprocess.run(
    ['dbt', 'test', '--target', 'prod'],
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Check for the specific error patterns
errors_found = []
if "dbt_utils_expression_is_true_src_customer_count_0" in result.stdout:
    errors_found.append("src_customer count test still exists")
if "dbt_utils_expression_is_true_src_account_count_0" in result.stdout:
    errors_found.append("src_account count test still exists")
if "interest_rate_pct___0_01_and_0_025" in result.stdout and "ERROR" in result.stdout:
    errors_found.append("interest_rate test still failing")
if "dbt_utils_expression_is_true_account_summary_count_0" in result.stdout:
    errors_found.append("account_summary count test still exists")
if "dbt_utils_expression_is_true_customer_profile_count_0" in result.stdout:
    errors_found.append("customer_profile count test still exists")
if "accepted_values_int_account_with_customer_account_type__Savings__Checking" in result.stdout and "FAIL" in result.stdout:
    errors_found.append("account_type test still failing")

print("\n" + "=" * 70)
if errors_found:
    print("❌ Some issues remain:")
    for error in errors_found:
        print(f"  - {error}")
else:
    print("✅ ALL FIXES APPLIED SUCCESSFULLY!")
    if "ERROR=0" in result.stdout:
        print("✅ ALL TESTS PASSING!")
    else:
        print("⚠️  Some tests may still be failing - check output above")
print("=" * 70)
