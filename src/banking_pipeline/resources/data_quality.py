"""
Data quality monitoring resource for tracking and reporting test results.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

from dagster import ConfigurableResource, InitResourceContext


class TestResult:
    """Represents a single data quality test result."""
    
    def __init__(
        self,
        test_name: str,
        model_name: str,
        status: str,
        severity: str = "error",
        message: Optional[str] = None,
        layer: Optional[str] = None,
    ):
        """
        Initialize a test result.
        
        Args:
            test_name: Name of the test that was executed
            model_name: Name of the model being tested
            status: Test status (pass, fail, warn, error, skip)
            severity: Severity level (error, warn)
            message: Optional error or warning message
            layer: Data layer (source, staging, snapshot, intermediate, marts)
        """
        self.test_name = test_name
        self.model_name = model_name
        self.status = status
        self.severity = severity
        self.message = message
        self.layer = layer or self._infer_layer_from_model(model_name)
    
    def _infer_layer_from_model(self, model_name: str) -> str:
        """Infer the data layer from the model name prefix."""
        if model_name.startswith("src_"):
            return "source"
        elif model_name.startswith("stg_"):
            return "staging"
        elif model_name.startswith("snap_"):
            return "snapshot"
        elif model_name.startswith("int_"):
            return "intermediate"
        else:
            return "marts"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary."""
        return {
            "test_name": self.test_name,
            "model_name": self.model_name,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "layer": self.layer,
        }


class DataQualityMonitor(ConfigurableResource):
    """
    Resource for monitoring and reporting data quality test results.
    
    This resource provides methods to parse DBT test results, group them by
    layer and severity, and generate comprehensive quality reports.
    """
    
    def generate_report(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """
        Generate a comprehensive data quality report from test results.
        
        Args:
            test_results: List of TestResult objects
            
        Returns:
            Dictionary containing the quality report with summary statistics,
            results grouped by layer and severity, and detailed failure information
        """
        total_tests = len(test_results)
        passed = sum(1 for t in test_results if t.status == "pass")
        failed = sum(1 for t in test_results if t.status == "fail")
        warned = sum(1 for t in test_results if t.status == "warn")
        skipped = sum(1 for t in test_results if t.status == "skip")
        errored = sum(1 for t in test_results if t.status == "error")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "warned": warned,
                "skipped": skipped,
                "errored": errored,
                "pass_rate": round(passed / total_tests * 100, 2) if total_tests > 0 else 0.0,
            },
            "by_layer": self._group_by_layer(test_results),
            "by_severity": self._group_by_severity(test_results),
            "failures": [t.to_dict() for t in test_results if t.status == "fail"],
            "warnings": [t.to_dict() for t in test_results if t.status == "warn"],
            "errors": [t.to_dict() for t in test_results if t.status == "error"],
        }
        
        return report
    
    def _group_by_layer(self, test_results: List[TestResult]) -> Dict[str, Dict[str, int]]:
        """
        Group test results by data layer.
        
        Args:
            test_results: List of TestResult objects
            
        Returns:
            Dictionary mapping layer names to summary statistics
        """
        layers = {}
        
        for test in test_results:
            layer = test.layer
            
            if layer not in layers:
                layers[layer] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "warned": 0,
                    "skipped": 0,
                    "errored": 0,
                }
            
            layers[layer]["total"] += 1
            
            if test.status == "pass":
                layers[layer]["passed"] += 1
            elif test.status == "fail":
                layers[layer]["failed"] += 1
            elif test.status == "warn":
                layers[layer]["warned"] += 1
            elif test.status == "skip":
                layers[layer]["skipped"] += 1
            elif test.status == "error":
                layers[layer]["errored"] += 1
        
        # Calculate pass rates
        for layer_stats in layers.values():
            total = layer_stats["total"]
            passed = layer_stats["passed"]
            layer_stats["pass_rate"] = round(passed / total * 100, 2) if total > 0 else 0.0
        
        return layers
    
    def _group_by_severity(self, test_results: List[TestResult]) -> Dict[str, Dict[str, int]]:
        """
        Group test results by severity level.
        
        Args:
            test_results: List of TestResult objects
            
        Returns:
            Dictionary mapping severity levels to summary statistics
        """
        severities = {}
        
        for test in test_results:
            severity = test.severity
            
            if severity not in severities:
                severities[severity] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "warned": 0,
                    "skipped": 0,
                    "errored": 0,
                }
            
            severities[severity]["total"] += 1
            
            if test.status == "pass":
                severities[severity]["passed"] += 1
            elif test.status == "fail":
                severities[severity]["failed"] += 1
            elif test.status == "warn":
                severities[severity]["warned"] += 1
            elif test.status == "skip":
                severities[severity]["skipped"] += 1
            elif test.status == "error":
                severities[severity]["errored"] += 1
        
        # Calculate pass rates
        for severity_stats in severities.values():
            total = severity_stats["total"]
            passed = severity_stats["passed"]
            severity_stats["pass_rate"] = round(passed / total * 100, 2) if total > 0 else 0.0
        
        return severities
    
    def parse_dbt_test_results(self, dbt_results_path: str) -> List[TestResult]:
        """
        Parse DBT test results from run_results.json file.
        
        Args:
            dbt_results_path: Path to DBT run_results.json file
            
        Returns:
            List of TestResult objects parsed from the DBT results
            
        Raises:
            FileNotFoundError: If the results file doesn't exist
            json.JSONDecodeError: If the results file is not valid JSON
        """
        results_file = Path(dbt_results_path)
        
        if not results_file.exists():
            raise FileNotFoundError(f"DBT results file not found: {dbt_results_path}")
        
        with open(results_file, "r") as f:
            dbt_results = json.load(f)
        
        test_results = []
        
        for result in dbt_results.get("results", []):
            # Only process test nodes
            if result.get("unique_id", "").startswith("test."):
                test_name = result.get("unique_id", "").split(".")[-1]
                
                # Extract model name from test metadata
                model_name = "unknown"
                if "test_metadata" in result:
                    model_name = result["test_metadata"].get("name", "unknown")
                
                # Determine status
                status = result.get("status", "unknown")
                if status == "success":
                    status = "pass"
                elif status in ["fail", "error", "warn", "skipped"]:
                    status = status if status != "skipped" else "skip"
                
                # Extract severity from config
                severity = "error"
                if "config" in result:
                    severity = result["config"].get("severity", "error")
                
                # Extract error message if available
                message = None
                if status in ["fail", "error", "warn"]:
                    message = result.get("message", None)
                
                test_result = TestResult(
                    test_name=test_name,
                    model_name=model_name,
                    status=status,
                    severity=severity,
                    message=message,
                )
                
                test_results.append(test_result)
        
        return test_results
    
    def save_report(self, report: Dict[str, Any], output_path: str) -> None:
        """
        Save quality report to a JSON file.
        
        Args:
            report: Quality report dictionary
            output_path: Path where the report should be saved
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
