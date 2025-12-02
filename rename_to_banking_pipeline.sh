#!/bin/bash

# ============================================================================
# Banking Data Pipeline Renaming Script
# ============================================================================
# This script renames all Lending Club / LC references to generic banking terms
# 
# Usage: ./rename_to_banking_pipeline.sh
# 
# What it does:
# 1. Renames directories (lending_club_pipeline → banking_pipeline)
# 2. Replaces text in all source files
# 3. Updates configuration files
# 4. Updates documentation
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running on macOS or Linux
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SED_INPLACE="sed -i ''"
        OS_TYPE="macOS"
    else
        SED_INPLACE="sed -i"
        OS_TYPE="Linux"
    fi
    print_status "Detected OS: $OS_TYPE"
}

# Function to create backup
create_backup() {
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    print_status "Creating backup in $BACKUP_DIR..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup critical files
    cp -r src "$BACKUP_DIR/" 2>/dev/null || true
    cp pyproject.toml "$BACKUP_DIR/" 2>/dev/null || true
    cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true
    cp README.md "$BACKUP_DIR/" 2>/dev/null || true
    cp -r dbt_project "$BACKUP_DIR/" 2>/dev/null || true
    
    print_success "Backup created in $BACKUP_DIR"
}

# Function to rename directories
rename_directories() {
    print_status "Renaming directories..."
    
    # Rename main source directory
    if [ -d "src/lending_club_pipeline" ]; then
        mv src/lending_club_pipeline src/banking_pipeline
        print_success "Renamed: src/lending_club_pipeline → src/banking_pipeline"
    else
        print_warning "Directory src/lending_club_pipeline not found"
    fi
    
    # Rename egg-info directory if it exists
    if [ -d "src/lending_club_pipeline.egg-info" ]; then
        mv src/lending_club_pipeline.egg-info src/banking_pipeline.egg-info
        print_success "Renamed: egg-info directory"
    fi
    
    # Rename any other LC directories
    find . -depth -type d -name "*lending_club*" -not -path "*/\.*" -not -path "*/backup_*" 2>/dev/null | while read dir; do
        new_dir=$(echo "$dir" | sed 's/lending_club/banking/g')
        if [ "$dir" != "$new_dir" ]; then
            mv "$dir" "$new_dir"
            print_success "Renamed: $dir → $new_dir"
        fi
    done
}

# Function to replace text in files
replace_in_files() {
    print_status "Replacing text in files..."
    
    local file_count=0
    
    # Find all relevant files
    find . -type f \( \
        -name "*.py" -o \
        -name "*.md" -o \
        -name "*.yml" -o \
        -name "*.yaml" -o \
        -name "*.sql" -o \
        -name "*.txt" -o \
        -name "*.toml" -o \
        -name "*.json" -o \
        -name "*.sh" -o \
        -name "Dockerfile" -o \
        -name ".env*" \
    \) -not -path "*/\.*" \
       -not -path "*/node_modules/*" \
       -not -path "*/venv/*" \
       -not -path "*/backup_*/*" \
       -not -path "*/__pycache__/*" \
       -not -path "*/target/*" \
       -not -path "*/dbt_packages/*" | while read file; do
        
        # Skip this script itself
        if [[ "$file" == *"rename_to_banking_pipeline.sh"* ]]; then
            continue
        fi
        
        # Create temp file
        temp_file="${file}.tmp"
        
        # Perform replacements
        sed 's/lending_club_pipeline/banking_pipeline/g' "$file" | \
        sed 's/lending-club-pipeline/banking-data-pipeline/g' | \
        sed 's/LendingClub/Banking/g' | \
        sed 's/Lending Club/Banking/g' | \
        sed 's/lending club/banking/g' | \
        sed 's/lc-pipeline-v1/banking-data-pipeline/g' | \
        sed 's/lc-pipeline/banking-pipeline/g' | \
        sed 's/lc_pipeline/banking_pipeline/g' | \
        sed 's/LC Data Pipeline/Banking Data Pipeline/g' | \
        sed 's/LC customer/banking customer/g' | \
        sed 's/LC account/banking account/g' | \
        sed 's/ai-tech-karthik\/lc-pipeline-v1/ai-tech-karthik\/banking-data-pipeline/g' > "$temp_file"
        
        # Check if file changed
        if ! cmp -s "$file" "$temp_file"; then
            mv "$temp_file" "$file"
            ((file_count++))
            echo "  ✓ Updated: $file"
        else
            rm "$temp_file"
        fi
    done
    
    print_success "Updated $file_count files"
}

# Function to update specific configuration files
update_configs() {
    print_status "Updating configuration files..."
    
    # Update pyproject.toml
    if [ -f "pyproject.toml" ]; then
        sed -i.bak 's/name = "lending-club-pipeline"/name = "banking-data-pipeline"/' pyproject.toml
        sed -i.bak 's/description = "Production-grade data pipeline for LendingClub customer and account data processing"/description = "Production-grade data pipeline for banking customer and account data processing"/' pyproject.toml
        sed -i.bak 's/description = "Production-grade data pipeline for Lending Club customer and account data processing"/description = "Production-grade data pipeline for banking customer and account data processing"/' pyproject.toml
        rm -f pyproject.toml.bak
        print_success "Updated: pyproject.toml"
    fi
    
    # Update docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        sed -i.bak 's/lending_club_/banking_/g' docker-compose.yml
        sed -i.bak 's/lending-club-pipeline/banking-data-pipeline/g' docker-compose.yml
        sed -i.bak 's/container_name: lending_club/container_name: banking/g' docker-compose.yml
        rm -f docker-compose.yml.bak
        print_success "Updated: docker-compose.yml"
    fi
    
    # Update dbt_project.yml
    if [ -f "dbt_project/dbt_project.yml" ]; then
        sed -i.bak "s/name: 'lending_club_pipeline'/name: 'banking_pipeline'/" dbt_project/dbt_project.yml
        sed -i.bak "s/profile: 'lending_club_pipeline'/profile: 'banking_pipeline'/" dbt_project/dbt_project.yml
        sed -i.bak 's/lending_club_pipeline:/banking_pipeline:/' dbt_project/dbt_project.yml
        rm -f dbt_project/dbt_project.yml.bak
        print_success "Updated: dbt_project/dbt_project.yml"
    fi
    
    # Update profiles.yml
    if [ -f "dbt_project/profiles.yml" ]; then
        sed -i.bak "s/lending_club_pipeline:/banking_pipeline:/" dbt_project/profiles.yml
        rm -f dbt_project/profiles.yml.bak
        print_success "Updated: dbt_project/profiles.yml"
    fi
    
    # Update .env files
    for env_file in .env .env.example; do
        if [ -f "$env_file" ]; then
            sed -i.bak 's/lending_club\.duckdb/banking.duckdb/g' "$env_file"
            rm -f "${env_file}.bak"
            print_success "Updated: $env_file"
        fi
    done
}

# Function to update documentation
update_docs() {
    print_status "Updating documentation..."
    
    # Update main README
    if [ -f "README.md" ]; then
        sed -i.bak 's/# LC Data Pipeline/# Banking Data Pipeline/' README.md
        sed -i.bak 's/LC customer/banking customer/g' README.md
        sed -i.bak 's/LC account/banking account/g' README.md
        sed -i.bak 's/LC /banking /g' README.md
        rm -f README.md.bak
        print_success "Updated: README.md"
    fi
    
    # Update all markdown files in docs/
    if [ -d "docs" ]; then
        find docs -name "*.md" -type f | while read doc_file; do
            sed -i.bak 's/LC /banking /g' "$doc_file"
            sed -i.bak 's/LC\./banking./g' "$doc_file"
            rm -f "${doc_file}.bak"
        done
        print_success "Updated: docs/*.md files"
    fi
}

# Function to clean up Python cache
clean_cache() {
    print_status "Cleaning Python cache..."
    
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    
    print_success "Cleaned Python cache"
}

# Function to verify changes
verify_changes() {
    print_status "Verifying changes..."
    
    echo ""
    echo "Checking for remaining 'lending_club' references..."
    
    remaining=$(grep -r "lending_club" . \
        --exclude-dir=.git \
        --exclude-dir=venv \
        --exclude-dir=node_modules \
        --exclude-dir=backup_* \
        --exclude-dir=target \
        --exclude-dir=dbt_packages \
        --exclude="*.pyc" \
        --exclude="rename_to_banking_pipeline.sh" \
        2>/dev/null | wc -l)
    
    if [ "$remaining" -gt 0 ]; then
        print_warning "Found $remaining remaining 'lending_club' references"
        echo "Run this to see them: grep -r 'lending_club' . --exclude-dir=.git --exclude-dir=venv --exclude-dir=backup_*"
    else
        print_success "No 'lending_club' references found!"
    fi
    
    echo ""
    echo "Checking for remaining 'lc-pipeline' references..."
    
    remaining_lc=$(grep -r "lc-pipeline" . \
        --exclude-dir=.git \
        --exclude-dir=venv \
        --exclude-dir=node_modules \
        --exclude-dir=backup_* \
        --exclude-dir=target \
        --exclude="rename_to_banking_pipeline.sh" \
        2>/dev/null | wc -l)
    
    if [ "$remaining_lc" -gt 0 ]; then
        print_warning "Found $remaining_lc remaining 'lc-pipeline' references"
        echo "Run this to see them: grep -r 'lc-pipeline' . --exclude-dir=.git --exclude-dir=venv --exclude-dir=backup_*"
    else
        print_success "No 'lc-pipeline' references found!"
    fi
}

# Function to print next steps
print_next_steps() {
    echo ""
    echo "============================================================================"
    print_success "Renaming complete!"
    echo "============================================================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Review changes:"
    echo "   git diff"
    echo ""
    echo "2. Update author information in pyproject.toml"
    echo ""
    echo "3. Clean and reinstall:"
    echo "   pip uninstall lending-club-pipeline"
    echo "   pip install -e ."
    echo ""
    echo "4. Test imports:"
    echo "   python -c 'import banking_pipeline; print(\"✓ Import successful\")'"
    echo ""
    echo "5. Test DBT:"
    echo "   cd dbt_project"
    echo "   dbt debug --profiles-dir ."
    echo "   dbt compile --profiles-dir ."
    echo ""
    echo "6. Test Dagster:"
    echo "   dagster dev"
    echo ""
    echo "7. Run tests:"
    echo "   pytest tests/"
    echo ""
    echo "8. Commit changes:"
    echo "   git add ."
    echo "   git commit -m 'Rebrand to generic banking data pipeline'"
    echo ""
    echo "9. Push to GitHub repository:"
    echo "    git remote set-url origin https://github.com/ai-tech-karthik/banking-data-pipeline.git"
    echo "    git push -u origin main"
    echo ""
    echo "Backup saved in: $BACKUP_DIR"
    echo "============================================================================"
}

# Main execution
main() {
    echo "============================================================================"
    echo "Banking Data Pipeline Renaming Script"
    echo "============================================================================"
    echo ""
    
    # Detect OS
    detect_os
    
    # Confirm before proceeding
    echo ""
    read -p "This will rename all Lending Club references. Continue? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Aborted by user"
        exit 1
    fi
    
    # Create backup
    create_backup
    
    # Execute renaming steps
    rename_directories
    replace_in_files
    update_configs
    update_docs
    clean_cache
    
    # Verify
    verify_changes
    
    # Print next steps
    print_next_steps
}

# Run main function
main
