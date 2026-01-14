"""
Data Puller Service Module
===========================
Service untuk menjalankan data puller Project 1 dan Project 2 secara otomatis
dan menyimpan hasil ke database PostgreSQL.
"""

import os
import sys
import time
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
import traceback

# Initialize logger first (before any usage)
logger = logging.getLogger(__name__)

# Add paths for Project 1 and Project 2 modules
project1_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Try multiple possible paths for Project 2
possible_project2_roots = [
    os.path.join(os.path.dirname(os.path.dirname(project1_root)), "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)"),
    os.path.join(os.path.dirname(project1_root), "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)"),
    os.path.join(project1_root, "..", "..", "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)"),
]

# Find existing Project 2 root
project2_root = None
for path in possible_project2_roots:
    abs_path = os.path.abspath(os.path.normpath(path))
    if os.path.exists(abs_path):
        project2_root = abs_path
        logger.info(f"Found Project 2 root: {project2_root}")
        break

if project2_root is None:
    logger.warning("Project 2 root not found. Will try to find it dynamically when needed.")

# Import database functions
from modules.database import (
    create_puller_execution,
    update_puller_execution,
    get_puller_config,
    DATABASE_CONFIG,
    get_db_connection
)
from modules.data_validation import (
    validate_and_adjust_date_range,
    delete_overlapping_data
)

# API Credentials (should be stored securely in production)
API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"


class DataPullerService:
    """Service untuk menjalankan data puller dan menyimpan ke database"""
    
    def __init__(self):
        self.project1_puller = None
        self.project2_puller = None
        
    def _load_project1_puller(self, start_date: str, end_date: str):
        """Load Project 1 puller logic"""
        try:
            # Import Project 1 classes from the module we created
            from modules.data_puller_project1 import Project1DataPuller
            
            return Project1DataPuller(API_TOKEN, SIGNATURE_SECRET, start_date, end_date)
            
        except ImportError as e:
            logger.error(f"Error importing Project 1 puller: {str(e)}")
            raise Exception(f"Failed to import Project 1 puller module: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading Project 1 puller: {str(e)}")
            raise
    
    def _load_project2_puller(self, start_date: str, end_date: str):
        """Load Project 2 puller logic"""
        try:
            # Try to find Project 2 path dynamically
            project2_data_prep = None
            
            # Try with project2_root if available
            if project2_root and os.path.exists(project2_root):
                candidate = os.path.join(
                    project2_root,
                    "V0dev-Project2-DataPreparation",
                    "scripts",
                    "project2_sales_analytics"
                )
                abs_candidate = os.path.abspath(os.path.normpath(candidate))
                if os.path.exists(abs_candidate):
                    project2_data_prep = abs_candidate
                    logger.info(f"Found Project 2 path via project2_root: {project2_data_prep}")
            
            # If not found, try relative paths from current file location
            if project2_data_prep is None:
                current_file = os.path.abspath(__file__)
                current_dir = os.path.dirname(current_file)
                project1_root_dir = os.path.dirname(current_dir)
                
                # Try different relative paths
                possible_paths = [
                    # From project1_root, go up one level to find project2
                    os.path.join(os.path.dirname(project1_root_dir), "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)", "V0dev-Project2-DataPreparation", "scripts", "project2_sales_analytics"),
                    # Direct from current directory
                    os.path.join(current_dir, "..", "..", "..", "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)", "V0dev-Project2-DataPreparation", "scripts", "project2_sales_analytics"),
                    # From project root
                    os.path.join(project1_root_dir, "..", "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)", "V0dev-Project2-DataPreparation", "scripts", "project2_sales_analytics"),
                ]
                
                for path in possible_paths:
                    abs_path = os.path.abspath(os.path.normpath(path))
                    logger.debug(f"Trying Project 2 path: {abs_path}")
                    if os.path.exists(abs_path):
                        project2_data_prep = abs_path
                        logger.info(f"✓ Found Project 2 path: {project2_data_prep}")
                        break
            
            if project2_data_prep is None or not os.path.exists(project2_data_prep):
                error_msg = (
                    f"Project 2 path not found.\n"
                    f"Expected location: .../WPT-Project2-Folder(...)/V0dev-Project2-DataPreparation/scripts/project2_sales_analytics\n"
                    f"Current file: {os.path.abspath(__file__)}\n"
                    f"Project 1 root: {project1_root}\n"
                    f"Please ensure Project 2 folder exists at the expected location relative to Project 1."
                )
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Better approach: Directly call main.py's run_sales_analytics function
            # This follows Project 2's modular architecture - just call the main process
            import importlib.util
            
            main_py_path = os.path.join(project2_data_prep, "main.py")
            
            if not os.path.exists(main_py_path):
                raise FileNotFoundError(f"Project 2 main.py not found at: {main_py_path}")
            
            # Save original state
            original_sys_path = sys.path.copy()
            original_cwd = os.getcwd()
            cached_config_modules = {}  # Store cached modules for restoration
            
            try:
                # Add Project 2 directory to sys.path (must be first to prioritize)
                project2_config_path = os.path.join(project2_data_prep, "config")
                project2_parent = os.path.dirname(project2_data_prep)
                
                # Remove Project 1 paths temporarily to avoid conflicts
                project1_paths = [project1_root, os.path.join(project1_root, "config")]
                filtered_paths = [p for p in sys.path if not any(
                    p.startswith(proj1_path) for proj1_path in project1_paths
                )]
                
                # Build new sys.path with Project 2 first
                new_sys_path = []
                # Add Project 2 paths in correct order for relative imports
                if project2_config_path not in new_sys_path:
                    new_sys_path.append(project2_config_path)
                if project2_data_prep not in new_sys_path:
                    new_sys_path.append(project2_data_prep)
                # Add modules directory for relative imports
                project2_modules_path = os.path.join(project2_data_prep, "modules")
                if project2_modules_path not in new_sys_path:
                    new_sys_path.append(project2_modules_path)
                if project2_parent not in new_sys_path:
                    new_sys_path.append(project2_parent)
                new_sys_path.extend(filtered_paths)
                
                sys.path = new_sys_path
                os.chdir(project2_data_prep)
                
                # CRITICAL: Clear Project 1's config from sys.modules cache
                # This ensures Project 2's config.constants is loaded instead
                import types
                config_modules_to_clear = [
                    'config',
                    'config.constants',
                    'config.constants.py'
                ]
                for mod_name in config_modules_to_clear:
                    if mod_name in sys.modules:
                        cached_config_modules[mod_name] = sys.modules.pop(mod_name)
                        logger.debug(f"Cleared {mod_name} from sys.modules cache")
                
                # CRITICAL: Create config package FIRST (before loading constants)
                config_package = types.ModuleType('config')
                config_package.__path__ = [project2_config_path]
                sys.modules['config'] = config_package
                logger.debug("✓ Created config package")
                
                # Pre-load Project 2's config.constants (must be after config package is created)
                project2_constants_path = os.path.join(project2_config_path, "constants.py")
                if os.path.exists(project2_constants_path):
                    try:
                        constants_spec = importlib.util.spec_from_file_location(
                            "config.constants",
                            project2_constants_path
                        )
                        if constants_spec and constants_spec.loader:
                            constants_module = importlib.util.module_from_spec(constants_spec)
                            constants_module.__file__ = project2_constants_path
                            constants_module.__package__ = "config"
                            # Ensure config package exists
                            if 'config' not in sys.modules:
                                sys.modules['config'] = config_package
                            sys.modules['config.constants'] = constants_module
                            # Execute to load all constants
                            constants_spec.loader.exec_module(constants_module)
                            logger.info("✓ Pre-loaded Project 2's config.constants")
                            
                            # Verify it loaded correctly
                            if hasattr(constants_module, 'API_CONFIG'):
                                logger.debug("✓ API_CONFIG found in Project 2's config.constants")
                            else:
                                logger.warning("⚠ API_CONFIG not found in Project 2's config.constants")
                    except Exception as e:
                        logger.error(f"Could not pre-load Project 2 config.constants: {str(e)}")
                        raise ImportError(f"Failed to load Project 2 config.constants: {str(e)}")
                else:
                    raise FileNotFoundError(f"Project 2 config.constants not found at: {project2_constants_path}")
                
                # Pre-load modules to handle relative imports
                # Create modules package structure
                import types
                modules_package = types.ModuleType('modules')
                modules_package.__path__ = [project2_modules_path]
                sys.modules['modules'] = modules_package
                
                # Pre-load api_client to handle relative import in data_puller
                api_client_path = os.path.join(project2_modules_path, "api_client.py")
                if os.path.exists(api_client_path):
                    try:
                        api_spec = importlib.util.spec_from_file_location(
                            "modules.api_client",
                            api_client_path
                        )
                        if api_spec and api_spec.loader:
                            api_module = importlib.util.module_from_spec(api_spec)
                            api_module.__file__ = api_client_path
                            api_module.__package__ = "modules"
                            sys.modules['modules.api_client'] = api_module
                            # Execute to handle its imports (should now use Project 2's config)
                            api_spec.loader.exec_module(api_module)
                            logger.debug("✓ Pre-loaded modules.api_client")
                    except Exception as e:
                        logger.warning(f"Could not pre-load api_client: {str(e)}")
                        # Continue, will try to load when main.py executes
                
                # Pre-load other modules that might be needed
                modules_to_preload = ['data_puller', 'data_enricher', 'rfm_analyzer', 'market_basket_analyzer']
                for mod_name in modules_to_preload:
                    mod_path = os.path.join(project2_modules_path, f"{mod_name}.py")
                    if os.path.exists(mod_path):
                        try:
                            mod_spec = importlib.util.spec_from_file_location(
                                f"modules.{mod_name}",
                                mod_path
                            )
                            if mod_spec and mod_spec.loader:
                                mod_module = importlib.util.module_from_spec(mod_spec)
                                mod_module.__file__ = mod_path
                                mod_module.__package__ = "modules"
                                sys.modules[f'modules.{mod_name}'] = mod_module
                                mod_spec.loader.exec_module(mod_module)
                        except Exception as e:
                            logger.debug(f"Could not pre-load {mod_name}: {str(e)}")
                            # Continue, will be loaded when needed
                
                # Now load and execute main.py
                spec = importlib.util.spec_from_file_location(
                    "project2_main",
                    main_py_path
                )
                
                if spec is None or spec.loader is None:
                    raise ImportError("Could not create module spec for Project 2 main.py")
                
                main_module = importlib.util.module_from_spec(spec)
                main_module.__file__ = main_py_path
                
                # Execute main.py (relative imports should work now)
                spec.loader.exec_module(main_module)
                
                # Get run_sales_analytics function
                if not hasattr(main_module, 'run_sales_analytics'):
                    raise ImportError("run_sales_analytics function not found in Project 2 main.py")
                
                run_sales_analytics = main_module.run_sales_analytics
                
                logger.info("✓ Successfully loaded Project 2 main.py and run_sales_analytics function")
                
                # Return a wrapper that will call run_sales_analytics and extract data
                class Project2MainWrapper:
                    def __init__(self, run_func, start_date, end_date):
                        self.run_func = run_func
                        self.start_date = start_date
                        self.end_date = end_date
                        self.data = {}
                        self.results = None
                        self.puller = None  # Will store puller reference if accessible
                    
                    def run_and_extract_data(self):
                        """
                        Run Project 2 main process and extract data for database storage.
                        Since run_sales_analytics doesn't return data directly, we'll:
                        1. Call run_sales_analytics (which creates puller internally)
                        2. Read data from Excel output file, OR
                        3. Access puller.data if we can get reference to it
                        """
                        logger.info("Running Project 2 main process (run_sales_analytics)...")
                        
                        # Call run_sales_analytics function
                        # This will: pull data → enrich → RFM → MBA → export to Excel
                        self.results = self.run_func(
                            api_token=API_TOKEN,
                            signature_secret=SIGNATURE_SECRET,
                            start_date=self.start_date,
                            end_date=self.end_date,
                            output_file=None,  # Will use default from FILE_PATHS
                            resume_from_checkpoint=False,  # Don't resume in automated mode
                            debug_mode=False  # Less verbose in automated mode
                        )
                        
                        if not self.results.get('success', False):
                            logger.warning("Project 2 main process completed with errors")
                            return self.data
                        
                        # Extract data from Excel output file
                        # run_sales_analytics exports data to Excel, we'll read from there
                        try:
                            # Try multiple possible paths where Excel file might be saved
                            # Excel exporter saves to current working directory (project2_data_prep) by default
                            excel_path = None
                            possible_paths = []
                            
                            # 1. Try to get from results output_file if available
                            if self.results and self.results.get('output_file'):
                                possible_paths.append(self.results['output_file'])
                            
                            # 2. Try config FILE_PATHS (might be relative path)
                            try:
                                from config.constants import FILE_PATHS
                                config_path = FILE_PATHS.get('OUTPUT_EXCEL')
                                if config_path:
                                    # If relative, try relative to project2_data_prep
                                    if not os.path.isabs(config_path):
                                        possible_paths.append(os.path.join(project2_data_prep, config_path))
                                    else:
                                        possible_paths.append(config_path)
                            except:
                                pass
                            
                            # 3. Current working directory (where Excel is likely saved)
                            possible_paths.append(os.path.join(project2_data_prep, "sales_performance_analytics.xlsx"))
                            
                            # 4. Data subdirectory (fallback)
                            possible_paths.append(os.path.join(project2_data_prep, "data_project2", "sales_performance_analytics.xlsx"))
                            
                            # Find first existing path
                            for path in possible_paths:
                                if path and os.path.exists(path):
                                    excel_path = path
                                    break
                            
                            if excel_path and os.path.exists(excel_path):
                                logger.info(f"Reading data from Excel output: {excel_path}")
                                import pandas as pd
                                
                                # Read all sheets from Excel
                                excel_file = pd.ExcelFile(excel_path)
                                sheet_mapping = {
                                    '5_Sales_Details': 'sales_details',
                                    '6_Sales_By_Customer': 'sales_by_customer',
                                    '7_Sales_By_Product': 'sales_by_product',
                                    '8_Customer_Master': 'customers',
                                    '9_Item_Master': 'items',
                                    '1_RFM_Analysis': 'rfm_analysis',
                                    '2_Customer_Segments': 'customer_segments',
                                    '3_Market_Basket': 'market_basket',
                                    '4_Product_Associations': 'product_associations'
                                }
                                
                                for sheet_name in excel_file.sheet_names:
                                    df = pd.read_excel(excel_path, sheet_name=sheet_name)
                                    
                                    # Try exact match first
                                    if sheet_name in sheet_mapping:
                                        self.data[sheet_mapping[sheet_name]] = df
                                    else:
                                        # Try fuzzy matching
                                        sheet_lower = sheet_name.lower()
                                        if 'sales' in sheet_lower and 'detail' in sheet_lower:
                                            self.data['sales_details'] = df
                                        elif 'sales' in sheet_lower and 'customer' in sheet_lower:
                                            self.data['sales_by_customer'] = df
                                        elif 'sales' in sheet_lower and 'product' in sheet_lower:
                                            self.data['sales_by_product'] = df
                                        elif 'customer' in sheet_lower and ('master' in sheet_lower or 'master' in sheet_name):
                                            self.data['customers'] = df
                                        elif 'item' in sheet_lower and ('master' in sheet_lower or 'master' in sheet_name):
                                            self.data['items'] = df
                                        elif 'rfm' in sheet_lower:
                                            self.data['rfm_analysis'] = df
                                
                                logger.info(f"✓ Extracted {len(self.data)} data tables from Excel: {list(self.data.keys())}")
                            else:
                                logger.warning(f"Excel output file not found. Checked paths:")
                                for i, path in enumerate(possible_paths, 1):
                                    if path:
                                        exists = "✓ EXISTS" if os.path.exists(path) else "✗ NOT FOUND"
                                        logger.warning(f"  {i}. {exists}: {path}")
                                logger.warning(f"Current working directory: {os.getcwd()}")
                                logger.info("Project 2 main process completed, but data extraction from Excel failed.")
                                logger.info("You may need to manually check the Excel output file location.")
                                
                        except Exception as e:
                            logger.warning(f"Could not extract data from Excel: {str(e)}")
                            logger.info("Project 2 main process may have completed successfully.")
                            logger.info("Data may be available in Excel output file or needs to be extracted differently.")
                        
                        return self.data
                
                return Project2MainWrapper(run_sales_analytics, start_date, end_date)
                
            finally:
                # Restore cached config modules (Project 1's config)
                for mod_name, mod_obj in cached_config_modules.items():
                    sys.modules[mod_name] = mod_obj
                
                # Restore original state
                sys.path = original_sys_path
                os.chdir(original_cwd)
            
        except ImportError as e:
            logger.error(f"Error importing Project 2 modules: {str(e)}")
            logger.warning("Trying alternative approach: subprocess execution...")
            
            # Fallback: Use subprocess for complete isolation
            return self._load_project2_via_subprocess(start_date, end_date)
            
        except Exception as e:
            logger.error(f"Error loading Project 2 puller: {str(e)}")
            logger.warning("Trying alternative approach: subprocess execution...")
            
            # Fallback: Use subprocess for complete isolation
            return self._load_project2_via_subprocess(start_date, end_date)
    
    def _load_project2_via_subprocess(self, start_date: str, end_date: str):
        """
        Alternative approach: Run Project 2 main.py as subprocess for complete isolation.
        This avoids all import conflicts but requires reading data from Excel output.
        """
        logger.info("Using subprocess approach for Project 2 (complete isolation)...")
        
        project2_data_prep = None
        if project2_root and os.path.exists(project2_root):
            candidate = os.path.join(
                project2_root,
                "V0dev-Project2-DataPreparation",
                "scripts",
                "project2_sales_analytics"
            )
            if os.path.exists(candidate):
                project2_data_prep = candidate
        
        if not project2_data_prep:
            raise FileNotFoundError("Project 2 path not found")
        
        main_py_path = os.path.join(project2_data_prep, "main.py")
        if not os.path.exists(main_py_path):
            raise FileNotFoundError(f"Project 2 main.py not found at: {main_py_path}")
        
        # Create a wrapper script that calls run_sales_analytics
        # This script will be executed in subprocess with Project 2's environment
        import tempfile
        import json
        
        # Create temporary script
        wrapper_script = f"""
import sys
import os
sys.path.insert(0, r'{project2_data_prep}')

from main import run_sales_analytics
import json

# Run the main process
results = run_sales_analytics(
    api_token=r'{API_TOKEN}',
    signature_secret=r'{SIGNATURE_SECRET}',
    start_date=r'{start_date}',
    end_date=r'{end_date}',
    output_file=None,
    resume_from_checkpoint=False,
    debug_mode=False
)

# Output results as JSON
print("__RESULTS_START__")
print(json.dumps({{
    'success': results.get('success', False),
    'stages_completed': results.get('stages_completed', []),
    'output_file': results.get('output_file', '')
}}))
print("__RESULTS_END__")
"""
        
        # Write wrapper script to temp file
        temp_script_path = os.path.join(tempfile.gettempdir(), "project2_wrapper.py")
        with open(temp_script_path, 'w', encoding='utf-8') as f:
            f.write(wrapper_script)
        
        try:
            # Run subprocess
            import subprocess
            result = subprocess.run(
                [sys.executable, temp_script_path],
                cwd=project2_data_prep,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Project 2 subprocess failed: {result.stderr}")
                raise Exception(f"Subprocess execution failed: {result.stderr}")
            
            # Parse results from output
            output = result.stdout
            if "__RESULTS_START__" in output and "__RESULTS_END__" in output:
                results_json = output.split("__RESULTS_START__")[1].split("__RESULTS_END__")[0].strip()
                results = json.loads(results_json)
            else:
                results = {'success': True}  # Assume success if no error
            
            logger.info("✓ Project 2 subprocess completed successfully")
            
            # Return wrapper that extracts data from Excel
            class Project2SubprocessWrapper:
                def __init__(self, results, project2_data_prep):
                    self.results = results
                    self.project2_data_prep = project2_data_prep
                    self.data = {}
                
                def run_and_extract_data(self):
                    """Extract data from Excel output file"""
                    logger.info("Extracting data from Project 2 Excel output...")
                    
                    # Find Excel output file
                    excel_paths = [
                        os.path.join(self.project2_data_prep, "data_project2", "sales_performance_analytics.xlsx"),
                        os.path.join(self.project2_data_prep, "sales_performance_analytics.xlsx"),
                    ]
                    
                    excel_path = None
                    for path in excel_paths:
                        if os.path.exists(path):
                            excel_path = path
                            break
                    
                    if not excel_path:
                        logger.warning("Excel output file not found. Project 2 may have completed but no data to extract.")
                        return self.data
                    
                    # Read Excel file
                    try:
                        import pandas as pd
                        excel_file = pd.ExcelFile(excel_path)
                        
                        sheet_mapping = {
                            '5_Sales_Details': 'sales_details',
                            '6_Sales_By_Customer': 'sales_by_customer',
                            '7_Sales_By_Product': 'sales_by_product',
                            '8_Customer_Master': 'customers',
                            '9_Item_Master': 'items',
                            '1_RFM_Analysis': 'rfm_analysis',
                            '2_Customer_Segments': 'customer_segments',
                            '3_Market_Basket': 'market_basket',
                            '4_Product_Associations': 'product_associations'
                        }
                        
                        for sheet_name in excel_file.sheet_names:
                            df = pd.read_excel(excel_path, sheet_name=sheet_name)
                            
                            if sheet_name in sheet_mapping:
                                self.data[sheet_mapping[sheet_name]] = df
                            else:
                                # Fuzzy matching
                                sheet_lower = sheet_name.lower()
                                if 'sales' in sheet_lower and 'detail' in sheet_lower:
                                    self.data['sales_details'] = df
                                elif 'sales' in sheet_lower and 'customer' in sheet_lower:
                                    self.data['sales_by_customer'] = df
                                elif 'sales' in sheet_lower and 'product' in sheet_lower:
                                    self.data['sales_by_product'] = df
                                elif 'customer' in sheet_lower and 'master' in sheet_lower:
                                    self.data['customers'] = df
                                elif 'item' in sheet_lower and 'master' in sheet_lower:
                                    self.data['items'] = df
                        
                        logger.info(f"✓ Extracted {len(self.data)} data tables from Excel: {list(self.data.keys())}")
                        
                    except Exception as e:
                        logger.error(f"Error reading Excel file: {str(e)}")
                    
                    return self.data
            
            return Project2SubprocessWrapper(results, project2_data_prep)
            
        finally:
            # Clean up temp script
            if os.path.exists(temp_script_path):
                try:
                    os.remove(temp_script_path)
                except:
                    pass
    
    def _save_to_database(self, data: Dict[str, pd.DataFrame], project_name: str, execution_id: int):
        """Save pulled data to PostgreSQL database"""
        try:
            try:
                from sqlalchemy import create_engine
            except ImportError:
                logger.warning("SQLAlchemy not available, using psycopg2 directly")
                return self._save_to_database_psycopg2(data, project_name, execution_id)
            
            # Create database connection
            db_uri = f"postgresql://{DATABASE_CONFIG['username']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
            engine = create_engine(db_uri)
            
            records_saved = 0
            
            for table_name, df in data.items():
                if df is None or df.empty:
                    continue
                
                # Clean table name for database
                clean_table_name = f"{project_name}_{table_name}".lower().replace(' ', '_').replace('-', '_')
                
                # Limit table name length
                if len(clean_table_name) > 63:
                    clean_table_name = clean_table_name[:63]
                
                try:
                    # Flatten dict/list columns to JSON strings
                    df_clean = df.copy()
                    for col in df_clean.columns:
                        # Check if column contains dict or list
                        if df_clean[col].dtype == 'object':
                            sample_val = df_clean[col].dropna().iloc[0] if not df_clean[col].dropna().empty else None
                            if isinstance(sample_val, dict):
                                # Convert dict to JSON string
                                import json
                                df_clean[col] = df_clean[col].apply(
                                    lambda x: json.dumps(x) if isinstance(x, dict) else x
                                )
                            elif isinstance(sample_val, list):
                                # Convert list to JSON string
                                import json
                                df_clean[col] = df_clean[col].apply(
                                    lambda x: json.dumps(x) if isinstance(x, list) else x
                                )
                    
                    # Save to database (replace existing data for this execution)
                    df_clean.to_sql(
                        clean_table_name,
                        engine,
                        if_exists='replace',
                        index=False,
                        method='multi',
                        chunksize=1000
                    )
                    
                    records_saved += len(df_clean)
                    logger.info(f"Saved {len(df_clean)} records to {clean_table_name}")
                    
                except Exception as e:
                    logger.warning(f"Error saving {table_name} to database: {str(e)}")
                    continue
            
            return records_saved
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            # Fallback to psycopg2 method
            return self._save_to_database_psycopg2(data, project_name, execution_id)
    
    def _track_data_ranges(
        self,
        project_name: str,
        data: Dict[str, pd.DataFrame],
        start_date,
        end_date,
        execution_id: Optional[int]
    ):
        """Track data ranges in database"""
        try:
            conn = get_db_connection()
            if conn is None:
                return
            
            cursor = conn.cursor()
            
            for table_name, df in data.items():
                if df.empty:
                    continue
                
                # Find date column
                date_cols = [col for col in df.columns if 'date' in col.lower() or 'transdate' in col.lower()]
                if not date_cols:
                    continue
                
                # Get actual date range from data
                date_col = date_cols[0]
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                actual_start = df[date_col].min().date() if not df[date_col].isna().all() else start_date
                actual_end = df[date_col].max().date() if not df[date_col].isna().all() else end_date
                
                # Insert or update data range
                cursor.execute("""
                    INSERT INTO data_ranges 
                    (project_name, table_name, start_date, end_date, records_count, execution_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (project_name, table_name, start_date, end_date)
                    DO UPDATE SET 
                        records_count = EXCLUDED.records_count,
                        execution_id = EXCLUDED.execution_id,
                        created_at = CURRENT_TIMESTAMP
                """, (project_name, table_name, actual_start, actual_end, len(df), execution_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Error tracking data ranges: {str(e)}")
            if conn:
                conn.rollback()
                conn.close()
    
    def _save_to_database_psycopg2(self, data: Dict[str, pd.DataFrame], project_name: str, execution_id: int):
        """Fallback method using psycopg2 directly"""
        try:
            import psycopg2
            from psycopg2.extras import execute_values
            
            conn = psycopg2.connect(
                host=DATABASE_CONFIG['host'],
                port=DATABASE_CONFIG['port'],
                user=DATABASE_CONFIG['username'],
                password=DATABASE_CONFIG['password'],
                database=DATABASE_CONFIG['database']
            )
            
            records_saved = 0
            
            for table_name, df in data.items():
                if df is None or df.empty:
                    continue
                
                # Clean table name
                clean_table_name = f"{project_name}_{table_name}".lower().replace(' ', '_').replace('-', '_')
                if len(clean_table_name) > 63:
                    clean_table_name = clean_table_name[:63]
                
                try:
                    cursor = conn.cursor()
                    
                    # Drop table if exists
                    cursor.execute(f"DROP TABLE IF EXISTS {clean_table_name}")
                    
                    # Create table
                    # Convert DataFrame to SQL-friendly format
                    columns = ', '.join([f'"{col}" TEXT' for col in df.columns])
                    cursor.execute(f"CREATE TABLE {clean_table_name} ({columns})")
                    
                    # Insert data
                    for _, row in df.iterrows():
                        values = tuple(str(val) if pd.notna(val) else None for val in row)
                        placeholders = ', '.join(['%s'] * len(values))
                        cursor.execute(
                            f"INSERT INTO {clean_table_name} VALUES ({placeholders})",
                            values
                        )
                    
                    conn.commit()
                    records_saved += len(df)
                    logger.info(f"Saved {len(df)} records to {clean_table_name}")
                    cursor.close()
                    
                except Exception as e:
                    logger.warning(f"Error saving {table_name}: {str(e)}")
                    conn.rollback()
                    continue
            
            conn.close()
            return records_saved
            
        except Exception as e:
            logger.error(f"Error in psycopg2 fallback: {str(e)}")
            return 0
    
    def run_project1_puller(
        self,
        start_date: str,
        end_date: str,
        config_id: Optional[int] = None,
        executed_by: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """
        Run Project 1 data puller
        
        Returns:
            (success, message, execution_id)
        """
        execution_id = None
        start_time = time.time()
        
        try:
            # Create execution record
            if config_id:
                execution_id = create_puller_execution(
                    config_id, 'project1', start_date, end_date, executed_by
                )
            
            logger.info(f"Starting Project 1 data puller: {start_date} to {end_date}")
            
            # Validate date range and check for duplicates
            from datetime import date as date_type
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if '-' in start_date else datetime.strptime(start_date, '%d/%m/%Y').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if '-' in end_date else datetime.strptime(end_date, '%d/%m/%Y').date()
            
            # Check for overlap in main tables
            should_proceed, adjusted_start, adjusted_end, validation_msg = validate_and_adjust_date_range(
                'project1', 'sales_invoices', start_date_obj, end_date_obj, strategy='delete'
            )
            
            if not should_proceed:
                return False, validation_msg, execution_id or 0
            
            # Use adjusted dates if provided
            if adjusted_start and adjusted_end:
                start_date_obj = adjusted_start
                end_date_obj = adjusted_end
                logger.info(f"Date range adjusted: {validation_msg}")
            
            # Delete overlapping data if needed
            if 'delete' in validation_msg.lower() or 'overlap' in validation_msg.lower():
                delete_overlapping_data('project1', 'sales_invoices', start_date_obj, end_date_obj)
                delete_overlapping_data('project1', 'purchase_orders', start_date_obj, end_date_obj)
            
            # Convert date format from YYYY-MM-DD to DD/MM/YYYY for Project 1
            start_date_formatted = start_date_obj.strftime('%d/%m/%Y')
            end_date_formatted = end_date_obj.strftime('%d/%m/%Y')
            
            # Load and run Project 1 puller
            puller = self._load_project1_puller(start_date_formatted, end_date_formatted)
            
            # Run puller
            puller.pull_master_data()
            puller.pull_inventory_data()
            puller.pull_sales_data()
            puller.pull_purchase_data()
            puller.calculate_comprehensive_metrics()
            puller.enrich_all_dataframes()
            puller.generate_optimization_insights()
            
            # Save to database
            total_records = self._save_to_database(puller.data, 'project1', execution_id or 0)
            
            # Track data ranges
            self._track_data_ranges('project1', puller.data, start_date_obj, end_date_obj, execution_id)
            
            execution_time = time.time() - start_time
            
            # Update execution record
            if execution_id:
                update_puller_execution(
                    execution_id,
                    'completed',
                    total_records,
                    execution_time
                )
            
            logger.info(f"Project 1 puller completed: {total_records} records in {execution_time:.1f}s")
            
            # Run ML pipeline automatically
            try:
                from modules.ml_pipeline import run_ml_pipeline
                logger.info("Starting ML pipeline for Project 1...")
                pipeline_success, pipeline_msg, pipeline_results = run_ml_pipeline('project1')
                if pipeline_success:
                    logger.info(f"ML pipeline completed: {pipeline_msg}")
                else:
                    logger.warning(f"ML pipeline failed: {pipeline_msg}")
            except Exception as e:
                logger.warning(f"ML pipeline error (non-critical): {str(e)}")
            
            return True, f"Successfully pulled {total_records} records", execution_id or 0
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Project 1 puller failed: {error_msg}")
            traceback.print_exc()
            
            execution_time = time.time() - start_time
            
            if execution_id:
                update_puller_execution(
                    execution_id,
                    'failed',
                    0,
                    execution_time,
                    error_msg
                )
            
            return False, f"Error: {error_msg}", execution_id or 0
    
    def run_project2_puller(
        self,
        start_date: str,
        end_date: str,
        config_id: Optional[int] = None,
        executed_by: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """
        Run Project 2 data puller
        
        Returns:
            (success, message, execution_id)
        """
        execution_id = None
        start_time = time.time()
        
        try:
            # Create execution record
            if config_id:
                execution_id = create_puller_execution(
                    config_id, 'project2', start_date, end_date, executed_by
                )
            
            logger.info(f"Starting Project 2 data puller: {start_date} to {end_date}")
            
            # Validate date range and check for duplicates
            from datetime import date as date_type
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if '-' in start_date else datetime.strptime(start_date, '%d/%m/%Y').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if '-' in end_date else datetime.strptime(end_date, '%d/%m/%Y').date()
            
            # Check for overlap in main tables
            should_proceed, adjusted_start, adjusted_end, validation_msg = validate_and_adjust_date_range(
                'project2', 'sales_details', start_date_obj, end_date_obj, strategy='delete'
            )
            
            if not should_proceed:
                return False, validation_msg, execution_id or 0
            
            # Use adjusted dates if provided
            if adjusted_start and adjusted_end:
                start_date_obj = adjusted_start
                end_date_obj = adjusted_end
                logger.info(f"Date range adjusted: {validation_msg}")
            
            # Delete overlapping data if needed
            if 'delete' in validation_msg.lower() or 'overlap' in validation_msg.lower():
                delete_overlapping_data('project2', 'sales_details', start_date_obj, end_date_obj)
            
            # Convert date format from YYYY-MM-DD to DD/MM/YYYY for Project 2
            start_date_formatted = start_date_obj.strftime('%d/%m/%Y')
            end_date_formatted = end_date_obj.strftime('%d/%m/%Y')
            
            # Load Project 2 main wrapper (calls run_sales_analytics from main.py)
            wrapper = self._load_project2_puller(start_date_formatted, end_date_formatted)
            
            # Run Project 2 main process and extract data
            # This will: pull data → enrich → RFM → MBA → export to Excel
            wrapper.run_and_extract_data()
            
            # Get data from wrapper (extracted from Excel output)
            data = wrapper.data
            
            if not data:
                logger.warning("No data extracted from Project 2 main process. Results may be in Excel file only.")
                # Try to get data from results if available
                if wrapper.results and wrapper.results.get('success'):
                    logger.info("Project 2 main process succeeded, but data extraction failed.")
                    logger.info("Data may be available in Excel output file.")
            
            # Save to database
            total_records = self._save_to_database(data, 'project2', execution_id or 0)
            
            # Track data ranges
            self._track_data_ranges('project2', data, start_date_obj, end_date_obj, execution_id)
            
            execution_time = time.time() - start_time
            
            # Update execution record
            if execution_id:
                update_puller_execution(
                    execution_id,
                    'completed',
                    total_records,
                    execution_time
                )
            
            logger.info(f"Project 2 puller completed: {total_records} records in {execution_time:.1f}s")
            
            # Run ML pipeline automatically
            try:
                from modules.ml_pipeline import run_ml_pipeline
                logger.info("Starting ML pipeline for Project 2...")
                pipeline_success, pipeline_msg, pipeline_results = run_ml_pipeline('project2')
                if pipeline_success:
                    logger.info(f"ML pipeline completed: {pipeline_msg}")
                else:
                    logger.warning(f"ML pipeline failed: {pipeline_msg}")
            except Exception as e:
                logger.warning(f"ML pipeline error (non-critical): {str(e)}")
            
            return True, f"Successfully pulled {total_records} records", execution_id or 0
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Project 2 puller failed: {error_msg}")
            traceback.print_exc()
            
            execution_time = time.time() - start_time
            
            if execution_id:
                update_puller_execution(
                    execution_id,
                    'failed',
                    0,
                    execution_time,
                    error_msg
                )
            
            return False, f"Error: {error_msg}", execution_id or 0
    
    def run_both_pullers(
        self,
        start_date: str,
        end_date: str,
        config_id: Optional[int] = None,
        executed_by: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, int]]:
        """
        Run both Project 1 and Project 2 pullers
        
        Returns:
            (success, message, execution_ids)
        """
        results = {}
        
        # Run Project 1
        success1, msg1, exec_id1 = self.run_project1_puller(
            start_date, end_date, config_id, executed_by
        )
        results['project1'] = exec_id1
        
        # Run Project 2
        success2, msg2, exec_id2 = self.run_project2_puller(
            start_date, end_date, config_id, executed_by
        )
        results['project2'] = exec_id2
        
        overall_success = success1 and success2
        overall_msg = f"Project 1: {msg1}\nProject 2: {msg2}"
        
        return overall_success, overall_msg, results


# Global service instance
_service_instance = None

def get_puller_service() -> DataPullerService:
    """Get or create puller service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataPullerService()
    return _service_instance
