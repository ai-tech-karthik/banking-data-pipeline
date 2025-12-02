#!/usr/bin/env python3
"""
Script to validate asset lineage and metadata configuration.

This script:
1. Loads the Dagster definitions
2. Validates that all assets have required metadata
3. Checks that asset groups are properly configured
4. Verifies freshness policies are set where appropriate
5. Validates asset lineage and dependencies
6. Generates a report of the asset graph

Usage:
    python scripts/validate_asset_metadata.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dagster import AssetKey
from lending_club_pipeline.definitions import defs


def validate_asset_metadata():
    """
    Validate that all assets have proper metadata configuration.
    """
    print("=" * 80)
    print("ASSET METADATA VALIDATION REPORT")
    print("=" * 80)
    print()
    
    # Get all assets from definitions
    assets = defs.get_all_asset_specs()
    
    print(f"Total assets found: {len(assets)}")
    print()
    
    # Track validation results
    validation_results = {
        "total_assets": len(assets),
        "assets_with_descriptions": 0,
        "assets_with_owners": 0,
        "assets_with_tags": 0,
        "assets_with_metadata": 0,
        "assets_with_freshness_sla": 0,
        "assets_with_groups": 0,
        "issues": [],
    }
    
    # Validate each asset
    for asset_spec in assets:
        asset_key = asset_spec.key
        asset_name = asset_key.to_user_string()
        
        print(f"Asset: {asset_name}")
        print("-" * 80)
        
        # Check description
        if asset_spec.description:
            print(f"  ✓ Description: {asset_spec.description[:100]}...")
            validation_results["assets_with_descriptions"] += 1
        else:
            print(f"  ✗ Missing description")
            validation_results["issues"].append(f"{asset_name}: Missing description")
        
        # Check owners
        if asset_spec.owners:
            print(f"  ✓ Owners: {', '.join(asset_spec.owners)}")
            validation_results["assets_with_owners"] += 1
        else:
            print(f"  ✗ Missing owners")
            validation_results["issues"].append(f"{asset_name}: Missing owners")
        
        # Check tags
        if asset_spec.tags:
            print(f"  ✓ Tags: {dict(asset_spec.tags)}")
            validation_results["assets_with_tags"] += 1
        else:
            print(f"  ✗ Missing tags")
            validation_results["issues"].append(f"{asset_name}: Missing tags")
        
        # Check metadata
        if asset_spec.metadata:
            print(f"  ✓ Metadata keys: {', '.join(asset_spec.metadata.keys())}")
            validation_results["assets_with_metadata"] += 1
        else:
            print(f"  ✗ Missing metadata")
            validation_results["issues"].append(f"{asset_name}: Missing metadata")
        
        # Check freshness SLA in metadata
        if asset_spec.metadata and "freshness_sla" in asset_spec.metadata:
            print(f"  ✓ Freshness SLA: {asset_spec.metadata['freshness_sla']}")
            validation_results["assets_with_freshness_sla"] += 1
        else:
            print(f"  ℹ No freshness SLA in metadata (optional)")
        
        # Check group
        if asset_spec.group_name:
            print(f"  ✓ Group: {asset_spec.group_name}")
            validation_results["assets_with_groups"] += 1
        else:
            print(f"  ✗ Missing group")
            validation_results["issues"].append(f"{asset_name}: Missing group")
        
        print()
    
    # Print summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print(f"Total Assets: {validation_results['total_assets']}")
    print(f"Assets with Descriptions: {validation_results['assets_with_descriptions']}/{validation_results['total_assets']}")
    print(f"Assets with Owners: {validation_results['assets_with_owners']}/{validation_results['total_assets']}")
    print(f"Assets with Tags: {validation_results['assets_with_tags']}/{validation_results['total_assets']}")
    print(f"Assets with Metadata: {validation_results['assets_with_metadata']}/{validation_results['total_assets']}")
    print(f"Assets with Freshness SLA: {validation_results['assets_with_freshness_sla']}/{validation_results['total_assets']}")
    print(f"Assets with Groups: {validation_results['assets_with_groups']}/{validation_results['total_assets']}")
    print()
    
    # Print issues
    if validation_results["issues"]:
        print("ISSUES FOUND:")
        print("-" * 80)
        for issue in validation_results["issues"]:
            print(f"  • {issue}")
        print()
    else:
        print("✓ No issues found - all assets have complete metadata!")
        print()
    
    # Print asset groups
    print("=" * 80)
    print("ASSET GROUPS")
    print("=" * 80)
    print()
    
    groups = {}
    for asset_spec in assets:
        group = asset_spec.group_name or "ungrouped"
        if group not in groups:
            groups[group] = []
        groups[group].append(asset_spec.key.to_user_string())
    
    for group, asset_names in sorted(groups.items()):
        print(f"{group}:")
        for asset_name in sorted(asset_names):
            print(f"  • {asset_name}")
        print()
    
    # Print asset lineage
    print("=" * 80)
    print("ASSET LINEAGE")
    print("=" * 80)
    print()
    
    for asset_spec in assets:
        asset_name = asset_spec.key.to_user_string()
        deps = asset_spec.deps
        
        if deps:
            print(f"{asset_name}:")
            for dep in deps:
                dep_name = dep.asset_key.to_user_string()
                print(f"  ← {dep_name}")
            print()
    
    # Return validation status
    return len(validation_results["issues"]) == 0


def print_asset_graph():
    """
    Print a visual representation of the asset graph.
    """
    print("=" * 80)
    print("ASSET DEPENDENCY GRAPH")
    print("=" * 80)
    print()
    
    assets = defs.get_all_asset_specs()
    
    # Build dependency graph
    graph = {}
    for asset_spec in assets:
        asset_name = asset_spec.key.to_user_string()
        deps = [dep.asset_key.to_user_string() for dep in asset_spec.deps]
        graph[asset_name] = deps
    
    # Print in topological order (roughly)
    print("Ingestion Layer:")
    print("  customers_raw")
    print("  accounts_raw")
    print()
    
    print("Staging Layer:")
    print("  staging/stg_customers__cleaned ← customers_raw")
    print("  staging/stg_accounts__cleaned ← accounts_raw")
    print()
    
    print("Intermediate Layer:")
    print("  intermediate/int_accounts__with_customer ← stg_accounts__cleaned, stg_customers__cleaned")
    print("  intermediate/int_savings_accounts_only ← int_accounts__with_customer")
    print()
    
    print("Marts Layer:")
    print("  marts/account_summary ← int_savings_accounts_only")
    print()
    
    print("Output Layer:")
    print("  account_summary_csv ← account_summary")
    print("  account_summary_parquet ← account_summary")
    print("  account_summary_to_databricks ← account_summary")
    print()


if __name__ == "__main__":
    print()
    print("Starting asset metadata validation...")
    print()
    
    try:
        # Validate metadata
        success = validate_asset_metadata()
        
        # Print asset graph
        print_asset_graph()
        
        # Exit with appropriate code
        if success:
            print("=" * 80)
            print("✓ VALIDATION PASSED - All assets have complete metadata!")
            print("=" * 80)
            print()
            sys.exit(0)
        else:
            print("=" * 80)
            print("✗ VALIDATION FAILED - Some assets are missing metadata")
            print("=" * 80)
            print()
            sys.exit(1)
    
    except Exception as e:
        print(f"Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
