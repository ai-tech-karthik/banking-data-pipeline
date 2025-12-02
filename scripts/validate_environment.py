#!/usr/bin/env python3
"""
Environment validation script for LendingClub Pipeline.
Validates Python version, dependencies, and configuration.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET}  {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def check_python_version() -> bool:
    """Check if Python version meets requirements."""
    print_header("Checking Python Version")
    
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    
    version_str = f"{current_version[0]}.{current_version[1]}"
    
    if current_version >= required_version:
        print_success(f"Python {version_str} (>= 3.8 required)")
        return True
    else:
        print_error(f"Python {version_str} is too old. Python >= 3.8 required.")
        return False


def check_docker() -> bool:
    """Check if Docker is installed and running."""
    print_header("Checking Docker")
    
    # Check Docker installation
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print_success(f"Docker installed: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Docker is not installed or not in PATH")
        return False
    
    # Check Docker daemon
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True
        )
        print_success("Docker daemon is running")
        return True
    except subprocess.CalledProcessError:
        print_error("Docker daemon is not running. Please start Docker Desktop.")
        return False


def check_docker_compose() -> bool:
    """Check if Docker Compose is installed."""
    print_header("Checking Docker Compose")
    
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print_success(f"Docker Compose installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Docker Compose is not installed or not in PATH")
        return False


def check_required_files() -> bool:
    """Check if all required project files exist."""
    print_header("Checking Required Files")
    
    required_files = [
        "docker-compose.yml",
        "Dockerfile",
        "workspace.yaml",
        "dagster.yaml",
        ".env.example",
        "pyproject.toml",
        "dbt_project/dbt_project.yml",
        "dbt_project/profiles.yml",
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print_success(f"Found: {file_path}")
        else:
            print_error(f"Missing: {file_path}")
            all_exist = False
    
    return all_exist


def check_env_file() -> Tuple[bool, List[str]]:
    """Check if .env file exists and contains required variables."""
    print_header("Checking Environment Configuration")
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print_warning(".env file not found")
        if Path(".env.example").exists():
            print_warning("Creating .env from .env.example...")
            import shutil
            shutil.copy(".env.example", ".env")
            print_success("Created .env file")
        else:
            print_error(".env.example not found. Cannot create .env file.")
            return False, []
    else:
        print_success(".env file exists")
    
    # Read and validate .env contents
    required_vars = [
        "ENVIRONMENT",
        "DATABASE_TYPE",
        "DUCKDB_PATH",
        "DBT_TARGET",
        "OUTPUT_PATH",
    ]
    
    env_vars = {}
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    missing_vars = []
    for var in required_vars:
        if var in env_vars and env_vars[var]:
            print_success(f"{var}={env_vars[var]}")
        else:
            print_warning(f"{var} is not set or empty")
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def check_data_directories() -> bool:
    """Check if data directories exist and are writable."""
    print_header("Checking Data Directories")
    
    directories = [
        "data/inputs",
        "data/outputs",
        "data/duckdb",
    ]
    
    all_ok = True
    for dir_path in directories:
        path = Path(dir_path)
        if path.exists():
            if os.access(path, os.W_OK):
                print_success(f"{dir_path} exists and is writable")
            else:
                print_warning(f"{dir_path} exists but is not writable")
                all_ok = False
        else:
            print_warning(f"{dir_path} does not exist. Creating...")
            path.mkdir(parents=True, exist_ok=True)
            print_success(f"Created {dir_path}")
    
    return all_ok


def check_input_data() -> bool:
    """Check if input CSV files exist."""
    print_header("Checking Input Data Files")
    
    input_files = [
        "data/inputs/Customer.csv",
        "data/inputs/accounts.csv",
    ]
    
    all_exist = True
    for file_path in input_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print_success(f"{file_path} exists ({size} bytes)")
        else:
            print_warning(f"{file_path} not found")
            all_exist = False
    
    if not all_exist:
        print_warning("Some input files are missing. Sample data will be needed for testing.")
    
    return all_exist


def check_python_dependencies(docker_running: bool = False) -> bool:
    """Check if required Python packages are installed."""
    print_header("Checking Python Dependencies")
    
    # All packages (only required for local execution without Docker)
    all_packages = [
        "dagster",
        "dagster-dbt",
        "dbt-core",
        "dbt-duckdb",
        "pandas",
        "pyarrow",
    ]
    
    installed_count = 0
    for package in all_packages:
        try:
            __import__(package.replace("-", "_"))
            print_success(f"{package} is installed")
            installed_count += 1
        except ImportError:
            if docker_running:
                print_warning(f"{package} is not installed (OK for Docker setup)")
            else:
                print_warning(f"{package} is not installed")
    
    if installed_count == 0 and not docker_running:
        print_warning("No Python packages installed locally.")
        print_warning("For local development without Docker, run: pip install -e .")
        print_warning("For Docker-based development, this is acceptable.")
        return True  # Still return True as Docker can handle this
    elif installed_count == 0 and docker_running:
        print_success("Using Docker for pipeline execution (local packages not required)")
        return True
    elif installed_count < len(all_packages):
        print_warning(f"{installed_count}/{len(all_packages)} packages installed.")
        if docker_running:
            print_success("Docker is running - local packages are optional")
        else:
            print_warning("For full local development, run: pip install -e .")
        return True
    
    return True


def check_disk_space() -> bool:
    """Check available disk space."""
    print_header("Checking Disk Space")
    
    import shutil
    
    total, used, free = shutil.disk_usage(".")
    
    free_gb = free // (2**30)
    total_gb = total // (2**30)
    
    print_success(f"Available: {free_gb} GB / {total_gb} GB")
    
    if free_gb < 1:
        print_warning("Less than 1 GB free. Consider freeing up disk space.")
        return False
    
    return True


def main():
    """Run all validation checks."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}LendingClub Pipeline - Environment Validation{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    checks = [
        ("Python Version", check_python_version),
        ("Docker", check_docker),
        ("Docker Compose", check_docker_compose),
        ("Required Files", check_required_files),
        ("Data Directories", check_data_directories),
        ("Input Data", check_input_data),
        ("Disk Space", check_disk_space),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Error during {name} check: {str(e)}")
            results[name] = False
    
    # Environment configuration check (returns tuple)
    env_ok, missing_vars = check_env_file()
    results["Environment Configuration"] = env_ok
    
    # Python dependencies check (optional for Docker setup)
    try:
        # Check if Docker is running to determine if local packages are required
        docker_running = results.get("Docker", False)
        dep_ok = check_python_dependencies(docker_running=docker_running)
        results["Python Dependencies"] = dep_ok
    except Exception:
        print_warning("Skipping Python dependencies check (optional for Docker setup)")
        results["Python Dependencies"] = None
    
    # Summary
    print_header("Validation Summary")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"\n{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    if failed > 0:
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    if skipped > 0:
        print(f"{Colors.YELLOW}Skipped: {skipped}{Colors.RESET}")
    
    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Environment validation successful!{Colors.RESET}\n")
        print("Next steps:")
        print("  1. Review .env file and update if needed")
        print("  2. Run: docker-compose up -d")
        print("  3. Access Dagster UI at http://localhost:3000")
        print("  4. Run validation script: python scripts/validate_pipeline.py")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Environment validation failed!{Colors.RESET}\n")
        print("Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
