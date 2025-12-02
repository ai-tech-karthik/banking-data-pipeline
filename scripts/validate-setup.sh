#!/bin/bash
# Validation script for Docker Compose setup

set -e

echo "🔍 Validating LendingClub Pipeline Setup..."
echo ""

# Check Docker
echo "✓ Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop."
    exit 1
fi
echo "  Docker version: $(docker --version)"

# Check Docker Compose
echo "✓ Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed."
    exit 1
fi
echo "  Docker Compose version: $(docker-compose --version)"

# Check if Docker daemon is running
echo "✓ Checking Docker daemon..."
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running. Please start Docker Desktop."
    exit 1
fi
echo "  Docker daemon is running"

# Check for required files
echo "✓ Checking required files..."
required_files=(
    "docker-compose.yml"
    "Dockerfile"
    "workspace.yaml"
    "dagster.yaml"
    ".env.example"
    "pyproject.toml"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done
echo "  All required files present"

# Check for .env file
echo "✓ Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "  Created .env file. Please review and update if needed."
else
    echo "  .env file exists"
fi

# Check for input data files
echo "✓ Checking input data files..."
if [ ! -f "data/inputs/Customer.csv" ]; then
    echo "⚠️  data/inputs/Customer.csv not found"
fi
if [ ! -f "data/inputs/accounts.csv" ]; then
    echo "⚠️  data/inputs/accounts.csv not found"
fi

# Check directory permissions
echo "✓ Checking directory permissions..."
if [ ! -w "data" ]; then
    echo "⚠️  data/ directory is not writable. Fixing permissions..."
    chmod -R 777 data/
fi
echo "  Directory permissions OK"

# Check available disk space
echo "✓ Checking disk space..."
available_space=$(df -h . | awk 'NR==2 {print $4}')
echo "  Available disk space: $available_space"

echo ""
echo "✅ Setup validation complete!"
echo ""
echo "Next steps:"
echo "  1. Review .env file and update if needed"
echo "  2. Ensure input CSV files are in data/inputs/"
echo "  3. Run: docker-compose up -d"
echo "  4. Access Dagster UI at http://localhost:3000"
echo ""
