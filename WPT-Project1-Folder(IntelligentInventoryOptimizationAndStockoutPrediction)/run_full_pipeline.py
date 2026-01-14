"""
=============================================================================
PROJECT 1 - END-TO-END DATA PIPELINE ORCHESTRATOR
=============================================================================
A single command to run the entire data preparation and feature engineering.

Stages:
  Stage 1: Data Preparation (API Pulling)
    1.1 fixed_field_mapping.py  - Pull all base data from Accurate API
    1.2 pull_real_lead_time.py  - Enrich PO with real receipt dates
    1.3 enrich_lead_time.py     - Calculate incoming stock projections
  
  Stage 2: Feature Engineering
    2.1 feature_engineering_pipeline.py - Calculate all features
    
Output:
  - field_mapping_csv_output/*.csv (5 base datasets)
  - Feature_Engineering/Master_Inventory_Feature_Set.csv
  - Feature_Engineering/Master_Inventory_Feature_Set_PerWarehouse.csv

Usage:
  python run_full_pipeline.py
  python run_full_pipeline.py --skip-data-prep    # Skip API pull, only run FE
  python run_full_pipeline.py --skip-fe           # Only run data prep
  run_full_pipeline.py --start-date 01/01/2023 --end-date 23/12/2025
Author: Auto-generated Orchestrator

=============================================================================
"""

import subprocess
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get the project root directory
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "Feature_Engineering" else SCRIPT_DIR

# Define paths to each script
LOGIC_DEV_DIR = PROJECT_ROOT / "Logic_Development_Project1"
FEATURE_ENG_DIR = PROJECT_ROOT / "Feature_Engineering"
DATA_OUTPUT_DIR = PROJECT_ROOT / "data" / "new_base_dataset_project1"

DATA_PREP_SCRIPTS = [
    {
        "name": "1. Fixed Field Mapping (API Data Pull)",
        "path": LOGIC_DEV_DIR / "fixed_field_mapping.py",
        "cwd": LOGIC_DEV_DIR,
        "description": "Pulls Sales, PO, Stock, Mutations, Master Items from Accurate API"
    },
    {
        "name": "2. Pull Real Lead Time",
        "path": LOGIC_DEV_DIR / "pull_real_lead_time.py",
        "cwd": LOGIC_DEV_DIR,
        "description": "Matches PO with Receive-Item to get real lead times"
    },
    {
        "name": "3. Enrich Lead Time & Stock Projection",
        "path": LOGIC_DEV_DIR / "enrich_lead_time.py",
        "cwd": LOGIC_DEV_DIR,
        "description": "Calculates incoming stock and projected inventory"
    },
]

FEATURE_ENG_SCRIPTS = [
    {
        "name": "4. Feature Engineering Pipeline",
        "path": FEATURE_ENG_DIR / "feature_engineering_pipeline.py",
        "cwd": FEATURE_ENG_DIR,
        "description": "Calculates ABC/XYZ, ROP, Safety Stock, Stockout Risk"
    },
]


import argparse

# ... (Imports remain same)

# =============================================================================
# RUNNER FUNCTIONS
# =============================================================================

def print_header(text: str):
    """Print a formatted header"""
    width = 70
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def print_stage(stage_num: int, total: int, name: str):
    """Print stage progress"""
    print(f"\n[{stage_num}/{total}] {name}")
    print("-" * 60)


def run_script(script_info: dict, extra_args: list = None) -> bool:
    """
    Run a Python script using subprocess.
    """
    name = script_info["name"]
    path = script_info["path"]
    cwd = script_info["cwd"]
    description = script_info.get("description", "")
    
    if not path.exists():
        print(f"  [X] ERROR: Script not found: {path}")
        return False
    
    print(f"  [>] Script: {path.name}")
    print(f"  [i] {description}")
    
    cmd = [sys.executable, str(path)]
    if extra_args:
        cmd.extend(extra_args)
        print(f"  [i] Arguments: {' '.join(extra_args)}")
        
    print(f"  [.] Running...")
    
    start_time = time.time()
    
    try:
        # Run the script
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=None  # User requested NO timeout for large datasets
        )
        
        elapsed = time.time() - start_time
        
        # Print output (last 30 lines if too long)
        stdout_lines = result.stdout.strip().split('\n') if result.stdout else []
        if len(stdout_lines) > 30:
            print(f"  ... (showing last 30 of {len(stdout_lines)} lines)")
            for line in stdout_lines[-30:]:
                print(f"  {line}")
        else:
            for line in stdout_lines:
                print(f"  {line}")
        
        # Check for errors
        if result.returncode != 0:
            print(f"\n  [X] FAILED (exit code {result.returncode})")
            if result.stderr:
                print(f"  STDERR: {result.stderr[:500]}")
            return False
        
        print(f"\n  [OK] Completed in {elapsed:.1f}s")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"  [X] TIMEOUT: Script exceeded 1 hour limit")
        return False
    except Exception as e:
        print(f"  [X] ERROR: {str(e)}")
        return False



    
    print("\n" + "=" * 70)
...
def run_data_preparation(date_args: list = None, resume_at: int = 1) -> bool:
    """Run all data preparation scripts"""
    print_header("STAGE 1: DATA PREPARATION (API PULLING)")
    
    total = len(DATA_PREP_SCRIPTS)
    success_count = 0
    
    for i, script in enumerate(DATA_PREP_SCRIPTS, 1):
        if i < resume_at:
            success_count += 1 # Count skipped steps as done
            continue
            
        print_stage(i, total, script["name"])
        
        # Only pass date args to scripts 1 and 2
        # Script 3 (Enrichment) doesn't need API dates
        current_args = date_args if i <= 2 else None
        
        if run_script(script, extra_args=current_args):
            success_count += 1
        else:
            print(f"\n  [!] Warning: {script['name']} failed. Continuing...")
    
    print(f"\n  [i] Data Preparation: {success_count}/{total} scripts completed")
    return success_count == total


def run_feature_engineering() -> bool:
    """Run feature engineering pipeline"""
    print_header("STAGE 2: FEATURE ENGINEERING")
    
    total = len(FEATURE_ENG_SCRIPTS)
    success_count = 0
    
    for i, script in enumerate(FEATURE_ENG_SCRIPTS, 1):
        print_stage(i, total, script["name"])
        if run_script(script):
            success_count += 1
    
    print(f"\n  [i] Feature Engineering: {success_count}/{total} scripts completed")
    return success_count == total


def verify_outputs():
    """Verify that expected output files exist"""
    print_header("VERIFICATION")
    
    expected_files = [
        DATA_OUTPUT_DIR / "1_Sales_Details.csv",
        DATA_OUTPUT_DIR / "2_PO_Details.csv",
        DATA_OUTPUT_DIR / "3_Stock_Mutations.csv",
        DATA_OUTPUT_DIR / "4_Current_Stock.csv",
        DATA_OUTPUT_DIR / "5_Master_Items.csv",
        DATA_OUTPUT_DIR / "Master_Inventory_Feature_Set.csv",
        DATA_OUTPUT_DIR / "Master_Inventory_Feature_Set_PerWarehouse.csv",
    ]
    
    all_exist = True
    for f in expected_files:
        exists = f.exists()
        status = "[OK]" if exists else "[X]"
        size = f.stat().st_size if exists else 0
        size_str = f"{size:,} bytes" if exists else "NOT FOUND"
        print(f"  {status} {f.name}: {size_str}")
        if not exists:
            all_exist = False
    
    return all_exist


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main orchestrator function"""
    start_time = datetime.now()
    
    parser = argparse.ArgumentParser(description='Project 1 Data Pipeline Orchestrator')
    parser.add_argument('--skip-data-prep', '--skip-stage1', action='store_true', help='Skip API data pulling (Stage 1)')
    parser.add_argument('--skip-fe', '--skip-stage2', action='store_true', help='Skip Feature Engineering (Stage 2)')
    parser.add_argument('--resume-step', type=int, default=1, help='Resume Data Prep from specific step (1=Pull, 2=RealTime, 3=Enrich)')
    parser.add_argument('--start-date', type=str, help='Start Date (dd/mm/yyyy)')
    parser.add_argument('--end-date', type=str, help='End Date (dd/mm/yyyy)')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("  PROJECT 1 - FULL DATA PIPELINE")
    print("  Intelligent Inventory Optimization & Stockout Prediction")
    print("=" * 70)
    print(f"  Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Project Root: {PROJECT_ROOT}")
    
    if args.start_date:
        print(f"  [i] Date Range: {args.start_date} - {args.end_date or 'Today'}")
    
    if args.skip_data_prep:
        print("  [>] Skipping data preparation (--skip-data-prep)")
    elif args.resume_step > 1:
        print(f"  [>] Resuming Data Prep from Step {args.resume_step}...")

    if args.skip_fe:
        print("  [>] Skipping feature engineering (--skip-fe)")
    
    # Run stages
    data_prep_ok = True
    fe_ok = True
    
    if not args.skip_data_prep:
        date_args = []
        if args.start_date: date_args.extend(['--start-date', args.start_date])
        if args.end_date: date_args.extend(['--end-date', args.end_date])
        
        data_prep_ok = run_data_preparation(date_args, resume_at=args.resume_step)
    
    if not args.skip_fe:
        fe_ok = run_feature_engineering()
    
    # Verify outputs
    outputs_ok = verify_outputs()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_header("PIPELINE COMPLETE")
    print(f"  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"  Data Preparation: {'[OK]' if data_prep_ok else '[!] Issues'}")
    print(f"  Feature Engineering: {'[OK]' if fe_ok else '[!] Issues'}")
    print(f"  Output Files: {'[OK] All exist' if outputs_ok else '[!] Some missing'}")
    
    if data_prep_ok and fe_ok and outputs_ok:
        print("\n  >>> PIPELINE COMPLETED SUCCESSFULLY! <<<")
        print(f"\n  Output files ready at:")
        print(f"    {DATA_OUTPUT_DIR / 'Master_Inventory_Feature_Set.csv'}")
        print(f"    {DATA_OUTPUT_DIR / 'Master_Inventory_Feature_Set_PerWarehouse.csv'}")
        return 0
    else:
        print("\n  [!] Pipeline completed with warnings. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
