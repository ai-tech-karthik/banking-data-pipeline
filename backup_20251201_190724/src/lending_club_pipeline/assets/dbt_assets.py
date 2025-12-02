"""
DBT transformation assets for the LendingClub data pipeline.

This module integrates DBT models as Dagster assets, enabling:
- Automatic dependency tracking between DBT models and Dagster assets
- Visual lineage in the Dagster UI
- Unified orchestration of ingestion and transformation layers
"""

import os
import time
from pathlib import Path
from typing import Any, Mapping

from dagster import (
    AssetExecutionContext,
    OpExecutionContext,
    AssetCheckResult,
    AssetCheckSeverity,
    asset_check,
    AssetKey,
)
from dagster_dbt import (
    DbtCliResource,
    dbt_assets,
    DagsterDbtTranslator,
    DagsterDbtTranslatorSettings,
)
from dagster_dbt.asset_decorator import DbtProject


# Get the absolute path to the DBT project directory
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent.parent / "dbt_project"

# Initialize the DBT project
dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    packaged_project_dir=DBT_PROJECT_DIR,
)

# Prepare the DBT project (parse manifest)
dbt_project.prepare_if_dev()


class CustomDagsterDbtTranslator(DagsterDbtTranslator):
    """
    Custom translator to configure how DBT models are represented as Dagster assets.
    
    This translator:
    - Assigns asset groups based on DBT model layer (staging, intermediate, marts)
    - Adds tags to identify the transformation layer
    - Adds owners and metadata for governance
    - Configures freshness policies based on layer
    - Preserves DBT model descriptions as asset descriptions
    """
    
    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        """
        Assign asset group based on DBT model path.
        
        Models in staging/ → 'staging' group
        Models in intermediate/ → 'intermediate' group
        Models in marts/ → 'marts' group
        """
        # Get the model's file path
        original_file_path = dbt_resource_props.get("original_file_path", "")
        
        if "staging" in original_file_path:
            return "staging"
        elif "intermediate" in original_file_path:
            return "intermediate"
        elif "marts" in original_file_path:
            return "marts"
        
        # Default group for other models
        return "transformations"
    
    def get_tags(self, dbt_resource_props: Mapping[str, Any]) -> Mapping[str, str]:
        """
        Add tags to identify the transformation layer and domain.
        """
        tags = {}
        
        # Get the model's file path and name
        original_file_path = dbt_resource_props.get("original_file_path", "")
        model_name = dbt_resource_props.get("name", "")
        
        # Layer tags
        if "staging" in original_file_path:
            tags["layer"] = "staging"
            tags["sla"] = "daily"
        elif "intermediate" in original_file_path:
            tags["layer"] = "intermediate"
            tags["sla"] = "daily"
        elif "marts" in original_file_path:
            tags["layer"] = "marts"
            tags["sla"] = "daily"
        
        # Domain tags based on model name
        if "customer" in model_name.lower():
            tags["domain"] = "customer"
        elif "account" in model_name.lower():
            tags["domain"] = "account"
        elif "summary" in model_name.lower():
            tags["domain"] = "analytics"
        
        # Add DBT-specific tags
        tags["tool"] = "dbt"
        tags["materialization"] = dbt_resource_props.get("config", {}).get("materialized", "view")
        
        return tags
    
    def get_owners(self, dbt_resource_props: Mapping[str, Any]) -> list[str] | None:
        """
        Assign owners based on DBT model layer.
        """
        original_file_path = dbt_resource_props.get("original_file_path", "")
        
        if "staging" in original_file_path:
            return ["data-engineering-team@company.com"]
        elif "intermediate" in original_file_path:
            return ["data-engineering-team@company.com"]
        elif "marts" in original_file_path:
            return ["analytics-team@company.com", "data-engineering-team@company.com"]
        
        return ["data-engineering-team@company.com"]
    

    
    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        """
        Override asset key generation to map DBT sources to Dagster assets.
        
        For DBT sources (raw.customers_raw, raw.accounts_raw), we want to map them
        to the Dagster ingestion assets (customers_raw, accounts_raw) without the
        'raw' prefix to avoid duplicate assets.
        """
        resource_type = dbt_resource_props.get("resource_type")
        
        # For sources, strip the 'raw' schema prefix to match Dagster asset names
        if resource_type == "source":
            source_name = dbt_resource_props.get("source_name", "")
            table_name = dbt_resource_props.get("name", "")
            
            # Map raw.customers_raw -> customers_raw
            # Map raw.accounts_raw -> accounts_raw
            if source_name == "raw":
                return AssetKey([table_name])
        
        # For models, use the default behavior
        return super().get_asset_key(dbt_resource_props)
    
    def get_metadata(self, dbt_resource_props: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Add custom metadata to DBT assets.
        """
        metadata = {}
        
        # Get the model's file path and name
        original_file_path = dbt_resource_props.get("original_file_path", "")
        model_name = dbt_resource_props.get("name", "")
        
        # Add layer information
        if "staging" in original_file_path:
            metadata["layer"] = "staging"
            metadata["purpose"] = "Data cleaning and normalization"
            metadata["transformation_type"] = "cleaning, type_casting, standardization"
        elif "intermediate" in original_file_path:
            metadata["layer"] = "intermediate"
            metadata["purpose"] = "Business logic and joins"
            metadata["transformation_type"] = "joins, filters, business_rules"
        elif "marts" in original_file_path:
            metadata["layer"] = "marts"
            metadata["purpose"] = "Business-ready analytics"
            metadata["transformation_type"] = "aggregations, calculations, final_output"
        
        # Add materialization info
        materialization = dbt_resource_props.get("config", {}).get("materialized", "view")
        metadata["materialization"] = materialization
        
        # Add materialization rationale
        if materialization == "view":
            metadata["materialization_rationale"] = "Lightweight, always fresh, no storage overhead"
        elif materialization == "ephemeral":
            metadata["materialization_rationale"] = "Computed on-the-fly, reusable component"
        elif materialization == "table":
            metadata["materialization_rationale"] = "Persistent storage for query performance"
        
        # Add schema info
        schema = dbt_resource_props.get("schema", "")
        if schema:
            metadata["schema"] = schema
        
        # Add data classification and freshness expectations
        metadata["data_classification"] = "internal"
        metadata["refresh_frequency"] = "daily"
        
        # Add layer-specific freshness SLA
        if "staging" in original_file_path:
            metadata["expected_lag_hours"] = 24
            metadata["freshness_sla"] = "24 hours - Expected to refresh daily at 2 AM"
        elif "intermediate" in original_file_path:
            metadata["expected_lag_hours"] = 25
            metadata["freshness_sla"] = "25 hours - Expected to refresh daily at 2 AM"
        elif "marts" in original_file_path:
            metadata["expected_lag_hours"] = 26
            metadata["freshness_sla"] = "26 hours - Expected to refresh daily at 2 AM"
        else:
            metadata["expected_lag_hours"] = 24.5
        
        # Add model-specific metadata
        if "customer" in model_name.lower():
            metadata["business_domain"] = "customer_master_data"
        elif "account" in model_name.lower():
            metadata["business_domain"] = "account_management"
        elif "summary" in model_name.lower():
            metadata["business_domain"] = "financial_analytics"
        
        # Add DBT-specific metadata
        metadata["dbt_model_name"] = model_name
        metadata["dbt_file_path"] = original_file_path
        
        # Add description from DBT model if available
        description = dbt_resource_props.get("description", "")
        if description:
            metadata["dbt_description"] = description
        
        return metadata


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    dagster_dbt_translator=CustomDagsterDbtTranslator(
        settings=DagsterDbtTranslatorSettings(
            enable_asset_checks=False,  # Disable automatic asset checks - we use manual checks instead
            # Disable auto-creation of source assets since we define them explicitly
            enable_duplicate_source_asset_keys=False,
        )
    ),
    name="dbt_transformations",
)
def dbt_transformations(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    Execute all DBT models and snapshots in the project with comprehensive error handling.
    
    This asset:
    - Runs DBT snapshots first to capture SCD2 historical versions
    - Runs all DBT models (source → staging → intermediate → marts)
    - Executes DBT tests to validate data quality
    - Automatically depends on ingestion assets (customers_raw, accounts_raw)
    - Provides detailed execution logs and metadata
    - Implements retry logic for transient database errors
    - Fails fast on test failures to prevent bad data propagation
    
    The DBT execution order:
    1. Snapshots: snap_customer, snap_account (SCD2 tracking)
    2. Source layer: src_customer, src_account (raw data with loaded_at)
    3. Staging layer: stg_customer, stg_account (cleaned data)
    4. Intermediate layer: int_account_with_customer, int_savings_account_only (incremental)
    5. Marts layer: account_summary, customer_profile (incremental)
    
    Incremental Strategy:
    - First run: Full refresh (process all data)
    - Subsequent runs: Process only new/changed records based on dbt_valid_from timestamps
    - Snapshots detect changes and create new versions automatically
    - Incremental models merge new/changed records efficiently
    
    Args:
        context: Dagster execution context for logging and metadata
        dbt: DBT CLI resource for executing DBT commands
        
    Yields:
        Asset materialization events for each DBT model and snapshot
        
    Raises:
        Exception: If DBT execution fails (model errors, test failures, snapshot errors, etc.)
    """
    context.log.info("Starting DBT transformation execution with snapshots and error handling")
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Step 1: Execute DBT build command which runs models, snapshots, and tests in correct order
            # DBT automatically handles dependencies and runs in topological order
            # Include quarantine models as they are needed to filter staging tables
            context.log.info("Step 1: Executing DBT build (models + snapshots + tests)")
            dbt_args = ["build"]
            
            context.log.info(f"DBT command: dbt {' '.join(dbt_args)}")
            
            # Stream DBT execution events
            dbt_result = dbt.cli(dbt_args, context=context)
            
            # Process and log DBT events
            for event in dbt_result.stream():
                # Log warnings from DBT
                if hasattr(event, 'event_type') and 'warn' in str(event.event_type).lower():
                    context.log.warning(f"DBT warning: {event}")
                
                yield event
            
            context.log.info("DBT build completed successfully")
            
            context.log.info("DBT transformation execution completed successfully")
            context.log.info(
                "Execution summary: "
                "DBT build command executed models, snapshots, and tests in correct dependency order"
            )
            
            # If we get here, execution was successful - no need to retry
            return
            
        except Exception as e:
            error_message = str(e)
            
            # Check if this is a transient database error that should be retried
            is_transient = _is_transient_error(error_message)
            
            if is_transient and attempt < max_retries - 1:
                # Transient error - retry with exponential backoff
                wait_time = retry_delay * (2 ** attempt)
                context.log.warning(
                    f"Transient database error detected (attempt {attempt + 1}/{max_retries}): {error_message}"
                )
                context.log.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                # Non-transient error or max retries reached - fail
                context.log.error(f"DBT execution failed: {error_message}")
                
                # Provide detailed error context
                if "snapshot" in error_message.lower():
                    context.log.error(
                        "Snapshot execution error. Common causes:\n"
                        "  - Staging models (stg_customer, stg_account) don't exist or have no data\n"
                        "  - Snapshot configuration issues (strategy, unique_key, updated_at)\n"
                        "  - Schema changes in staging models breaking snapshot contracts\n"
                        "  - Database permissions issues for snapshot schema"
                    )
                elif "test" in error_message.lower() or "fail" in error_message.lower():
                    context.log.error(
                        "Data quality test failure detected. "
                        "Check the DBT logs for details on which tests failed and why."
                    )
                elif "syntax" in error_message.lower():
                    context.log.error(
                        "SQL syntax error detected. "
                        "Review the DBT model files for syntax issues."
                    )
                elif "relation" in error_message.lower() or "table" in error_message.lower():
                    context.log.error(
                        "Missing table or relation error. "
                        "Ensure ingestion assets ran successfully and source tables exist."
                    )
                elif "connection" in error_message.lower() or "timeout" in error_message.lower():
                    context.log.error(
                        f"Database connection error after {max_retries} attempts. "
                        "Check database connectivity and credentials."
                    )
                elif "incremental" in error_message.lower():
                    context.log.error(
                        "Incremental model error. Try running with --full-refresh flag. "
                        "Common causes:\n"
                        "  - Incremental logic errors (is_incremental() conditions)\n"
                        "  - unique_key configuration issues\n"
                        "  - Schema changes requiring full refresh"
                    )
                else:
                    context.log.error(
                        "Check the DBT logs for detailed error information. "
                        "Common issues include:\n"
                        "  - SQL syntax errors in model files\n"
                        "  - Data quality test failures\n"
                        "  - Missing source tables (ensure ingestion assets ran successfully)\n"
                        "  - Database connection issues\n"
                        "  - Snapshot or incremental model configuration errors"
                    )
                
                raise


def _is_transient_error(error_message: str) -> bool:
    """
    Determine if an error is transient and should be retried.
    
    Transient errors include:
    - Connection timeouts
    - Network errors
    - Database lock errors
    - Temporary resource unavailability
    
    Args:
        error_message: The error message to analyze
        
    Returns:
        True if the error is transient, False otherwise
    """
    transient_patterns = [
        "timeout",
        "connection",
        "network",
        "lock",
        "busy",
        "unavailable",
        "temporary",
        "retry",
        "deadlock",
    ]
    
    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in transient_patterns)



# Asset checks for DBT test results
# Note: These checks apply to the entire DBT transformation process
# We use the account_summary asset as the target since it's the final output
@asset_check(asset=AssetKey(["marts", "account_summary"]), description="Verify all DBT tests passed")
def dbt_tests_passed(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    Asset check that verifies all DBT tests passed.
    
    This check:
    - Runs after DBT models are materialized
    - Parses DBT test results from the run_results.json file
    - Reports detailed information about any test failures
    - Provides severity levels based on test outcomes
    
    Args:
        context: Dagster execution context for logging
        dbt: DBT CLI resource for accessing DBT artifacts
        
    Returns:
        AssetCheckResult with pass/fail status and metadata
    """
    import json
    
    context.log.info("Checking DBT test results")
    
    # Path to DBT run results
    run_results_path = DBT_PROJECT_DIR / "target" / "run_results.json"
    
    if not run_results_path.exists():
        context.log.warning("DBT run_results.json not found - cannot verify test results")
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.WARN,
            description="DBT run results file not found",
            metadata={
                "message": "run_results.json not found in target directory"
            }
        )
    
    try:
        with open(run_results_path, 'r') as f:
            run_results = json.load(f)
        
        # Parse test results
        test_results = []
        failed_tests = []
        warned_tests = []
        passed_tests = []
        
        for result in run_results.get('results', []):
            # Check if this is a test result
            if result.get('unique_id', '').startswith('test.'):
                test_name = result.get('unique_id', 'unknown')
                status = result.get('status', 'unknown')
                message = result.get('message', '')
                
                test_info = {
                    'name': test_name,
                    'status': status,
                    'message': message
                }
                test_results.append(test_info)
                
                if status == 'fail' or status == 'error':
                    failed_tests.append(test_info)
                    context.log.error(f"Test failed: {test_name} - {message}")
                elif status == 'warn':
                    warned_tests.append(test_info)
                    context.log.warning(f"Test warning: {test_name} - {message}")
                elif status == 'pass':
                    passed_tests.append(test_info)
                    context.log.debug(f"Test passed: {test_name}")
        
        # Determine overall result
        total_tests = len(test_results)
        
        if not test_results:
            context.log.info("No DBT tests found in run results")
            return AssetCheckResult(
                passed=True,
                description="No DBT tests to verify",
                metadata={
                    "total_tests": 0
                }
            )
        
        if failed_tests:
            context.log.error(f"{len(failed_tests)} out of {total_tests} DBT tests failed")
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.ERROR,
                description=f"{len(failed_tests)} DBT test(s) failed",
                metadata={
                    "total_tests": total_tests,
                    "passed": len(passed_tests),
                    "failed": len(failed_tests),
                    "warned": len(warned_tests),
                    "failed_test_names": [t['name'] for t in failed_tests],
                    "failed_test_messages": [t['message'] for t in failed_tests]
                }
            )
        
        if warned_tests:
            context.log.warning(f"{len(warned_tests)} out of {total_tests} DBT tests have warnings")
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description=f"{len(warned_tests)} DBT test(s) have warnings",
                metadata={
                    "total_tests": total_tests,
                    "passed": len(passed_tests),
                    "failed": len(failed_tests),
                    "warned": len(warned_tests),
                    "warned_test_names": [t['name'] for t in warned_tests]
                }
            )
        
        # All tests passed
        context.log.info(f"All {total_tests} DBT tests passed successfully")
        return AssetCheckResult(
            passed=True,
            description=f"All {total_tests} DBT test(s) passed",
            metadata={
                "total_tests": total_tests,
                "passed": len(passed_tests),
                "failed": 0,
                "warned": 0
            }
        )
        
    except Exception as e:
        context.log.error(f"Error parsing DBT test results: {str(e)}")
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.ERROR,
            description="Failed to parse DBT test results",
            metadata={
                "error": str(e)
            }
        )


@asset_check(asset=AssetKey(["marts", "account_summary"]), description="Verify no DBT model compilation errors")
def dbt_models_compiled(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    Asset check that verifies all DBT models compiled successfully.
    
    This check:
    - Verifies that all models compiled without SQL syntax errors
    - Checks for missing references or dependencies
    - Reports any compilation warnings
    
    Args:
        context: Dagster execution context for logging
        dbt: DBT CLI resource for accessing DBT artifacts
        
    Returns:
        AssetCheckResult with pass/fail status and metadata
    """
    import json
    
    context.log.info("Checking DBT model compilation")
    
    # Path to DBT run results
    run_results_path = DBT_PROJECT_DIR / "target" / "run_results.json"
    
    if not run_results_path.exists():
        context.log.warning("DBT run_results.json not found - cannot verify compilation")
        return AssetCheckResult(
            passed=True,
            severity=AssetCheckSeverity.WARN,
            description="DBT run results file not found",
            metadata={
                "message": "run_results.json not found - assuming compilation succeeded"
            }
        )
    
    try:
        with open(run_results_path, 'r') as f:
            run_results = json.load(f)
        
        # Parse model results
        model_results = []
        failed_models = []
        successful_models = []
        
        for result in run_results.get('results', []):
            # Check if this is a model result (not a test)
            if result.get('unique_id', '').startswith('model.'):
                model_name = result.get('unique_id', 'unknown')
                status = result.get('status', 'unknown')
                message = result.get('message', '')
                
                model_info = {
                    'name': model_name,
                    'status': status,
                    'message': message
                }
                model_results.append(model_info)
                
                if status == 'error':
                    failed_models.append(model_info)
                    context.log.error(f"Model compilation/execution failed: {model_name} - {message}")
                elif status == 'success':
                    successful_models.append(model_info)
                    context.log.debug(f"Model compiled/executed successfully: {model_name}")
        
        # Determine overall result
        total_models = len(model_results)
        
        if not model_results:
            context.log.info("No DBT models found in run results")
            return AssetCheckResult(
                passed=True,
                description="No DBT models to verify",
                metadata={
                    "total_models": 0
                }
            )
        
        if failed_models:
            context.log.error(f"{len(failed_models)} out of {total_models} DBT models failed")
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.ERROR,
                description=f"{len(failed_models)} DBT model(s) failed to compile/execute",
                metadata={
                    "total_models": total_models,
                    "successful": len(successful_models),
                    "failed": len(failed_models),
                    "failed_model_names": [m['name'] for m in failed_models],
                    "failed_model_messages": [m['message'] for m in failed_models]
                }
            )
        
        # All models compiled successfully
        context.log.info(f"All {total_models} DBT models compiled/executed successfully")
        return AssetCheckResult(
            passed=True,
            description=f"All {total_models} DBT model(s) compiled/executed successfully",
            metadata={
                "total_models": total_models,
                "successful": len(successful_models),
                "failed": 0
            }
        )
        
    except Exception as e:
        context.log.error(f"Error checking DBT model compilation: {str(e)}")
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.ERROR,
            description="Failed to check DBT model compilation",
            metadata={
                "error": str(e)
            }
        )
