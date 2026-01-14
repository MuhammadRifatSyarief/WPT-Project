"""
Run Data Puller for Project 1
=============================
This script runs the data puller to fetch fresh data from Accurate API
"""

import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    from modules.data_puller_service import DataPullerService
    
    # Default date range (last 6 months)
    start_date = "01/07/2025"
    end_date = "14/12/2025"
    
    # Check command line arguments
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    
    print("="*60)
    print("🚀 RUNNING DATA PULLER FOR PROJECT 1")
    print("="*60)
    print(f"Date Range: {start_date} to {end_date}")
    print("="*60)
    
    try:
        service = DataPullerService()
        
        # Run data puller for Project 1
        success, message, execution_id = service.run_project1_puller(
            start_date=start_date,
            end_date=end_date,
            executed_by="command_line"
        )
        
        print("="*60)
        if success:
            print(f"✅ SUCCESS: {message}")
            print(f"📊 Execution ID: {execution_id}")
        else:
            print(f"❌ FAILED: {message}")
        print("="*60)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
