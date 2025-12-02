#!/bin/bash
# Script to set up local Python virtual environment and run the pipeline

set -e  # Exit on error

echo "=========================================="
echo "Setting up Local Python Environment"
echo "=========================================="

# Check Python version
echo ""
echo "Checking Python version..."
python3 --version

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf venv
fi
python3 -m venv venv

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install the package in editable mode with dev dependencies
echo ""
echo "Installing package and dependencies..."
pip install -e ".[dev]"

# Install DBT dependencies
echo ""
echo "Installing DBT packages..."
cd dbt_project
dbt deps
cd ..

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the e2e tests, run:"
echo "  pytest tests/e2e/test_full_pipeline.py -v"
echo ""
echo "To deactivate the virtual environment, run:"
echo "  deactivate"
