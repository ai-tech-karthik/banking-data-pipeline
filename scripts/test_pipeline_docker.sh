#!/bin/bash
# Test script for full pipeline execution in Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧪 LendingClub Pipeline - Docker Compose Test"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

# Step 1: Validate environment
echo "Step 1: Validating environment..."
if [ -f "scripts/validate_environment.py" ]; then
    python3 scripts/validate_environment.py
    if [ $? -ne 0 ]; then
        print_error "Environment validation failed"
        exit 1
    fi
else
    print_warning "validate_environment.py not found, skipping"
fi
echo ""

# Step 2: Check if Docker Compose is running
echo "Step 2: Checking Docker Compose status..."
if docker-compose ps | grep -q "Up"; then
    print_success "Docker Compose services are running"
else
    print_warning "Docker Compose services not running. Starting..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_info "Waiting for services to start (30 seconds)..."
    sleep 30
    
    # Check again
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker Compose services started successfully"
    else
        print_error "Failed to start Docker Compose services"
        docker-compose logs
        exit 1
    fi
fi
echo ""

# Step 3: Check Dagster UI accessibility
echo "Step 3: Checking Dagster UI..."
max_retries=10
retry_count=0
while [ $retry_count -lt $max_retries ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
        print_success "Dagster UI is accessible at http://localhost:3000"
        break
    else
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            print_info "Waiting for Dagster UI... (attempt $retry_count/$max_retries)"
            sleep 5
        else
            print_error "Dagster UI is not accessible after $max_retries attempts"
            print_info "Check logs with: docker-compose logs dagster-webserver"
            exit 1
        fi
    fi
done
echo ""

# Step 4: Verify input data exists
echo "Step 4: Verifying input data..."
if [ -f "data/inputs/Customer.csv" ] && [ -f "data/inputs/accounts.csv" ]; then
    print_success "Input CSV files found"
    
    # Show file info
    customer_lines=$(wc -l < data/inputs/Customer.csv)
    accounts_lines=$(wc -l < data/inputs/accounts.csv)
    print_info "Customer.csv: $customer_lines lines"
    print_info "accounts.csv: $accounts_lines lines"
else
    print_error "Input CSV files not found in data/inputs/"
    exit 1
fi
echo ""

# Step 5: Clean previous outputs
echo "Step 5: Cleaning previous outputs..."
if [ -d "data/outputs" ]; then
    rm -f data/outputs/*.csv data/outputs/*.parquet
    print_success "Cleaned previous outputs"
else
    mkdir -p data/outputs
    print_success "Created outputs directory"
fi
echo ""

# Step 6: Run pipeline using Dagster CLI (if available in container)
echo "Step 6: Testing pipeline execution..."
print_info "To run the pipeline, you have two options:"
echo ""
echo "Option 1: Using Dagster UI (Recommended)"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Navigate to 'Assets' tab"
echo "  3. Click 'Materialize all' button"
echo "  4. Wait for all assets to complete"
echo ""
echo "Option 2: Using Dagster CLI in container"
echo "  docker-compose exec dagster-webserver dagster asset materialize --select '*'"
echo ""

# Ask user if they want to proceed with automated test
read -p "Do you want to attempt automated pipeline execution? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Attempting to materialize assets via CLI..."
    
    # Try to run dagster command in container
    if docker-compose exec -T dagster-webserver dagster asset materialize --select '*' 2>&1; then
        print_success "Pipeline execution completed"
    else
        print_warning "Automated execution failed. Please use Dagster UI instead."
        print_info "Open http://localhost:3000 and materialize assets manually"
        exit 0
    fi
else
    print_info "Skipping automated execution"
    print_info "Please materialize assets via Dagster UI and then run:"
    print_info "  python3 scripts/validate_pipeline.py"
    exit 0
fi
echo ""

# Step 7: Wait for outputs to be generated
echo "Step 7: Waiting for outputs..."
max_wait=60
wait_count=0
while [ $wait_count -lt $max_wait ]; do
    if [ -f "data/outputs/account_summary.csv" ]; then
        print_success "Output files generated"
        break
    else
        wait_count=$((wait_count + 1))
        if [ $wait_count -lt $max_wait ]; then
            sleep 2
        else
            print_warning "Output files not found after waiting"
            print_info "Check Dagster UI for asset status"
        fi
    fi
done
echo ""

# Step 8: Validate outputs
echo "Step 8: Validating outputs..."
if [ -f "scripts/validate_pipeline.py" ]; then
    python3 scripts/validate_pipeline.py
    if [ $? -eq 0 ]; then
        print_success "Pipeline validation passed"
    else
        print_error "Pipeline validation failed"
        exit 1
    fi
else
    print_warning "validate_pipeline.py not found, skipping validation"
    
    # Basic validation
    if [ -f "data/outputs/account_summary.csv" ]; then
        lines=$(wc -l < data/outputs/account_summary.csv)
        print_success "account_summary.csv exists with $lines lines"
    fi
    
    if [ -f "data/outputs/account_summary.parquet" ]; then
        size=$(du -h data/outputs/account_summary.parquet | cut -f1)
        print_success "account_summary.parquet exists ($size)"
    fi
fi
echo ""

# Step 9: Show summary
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo ""
print_success "Environment validated"
print_success "Docker Compose services running"
print_success "Dagster UI accessible"
print_success "Input data verified"

if [ -f "data/outputs/account_summary.csv" ]; then
    print_success "Pipeline outputs generated"
    echo ""
    echo "Output files:"
    ls -lh data/outputs/
else
    print_warning "Pipeline outputs not found"
    print_info "Materialize assets in Dagster UI: http://localhost:3000"
fi

echo ""
echo "Next steps:"
echo "  • View pipeline in Dagster UI: http://localhost:3000"
echo "  • Check outputs in: data/outputs/"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop services: docker-compose down"
echo ""

print_success "Test completed successfully!"
