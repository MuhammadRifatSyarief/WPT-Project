#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick script to run ML pipeline for Project 1
"""
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from modules.ml_pipeline import run_ml_pipeline

if __name__ == "__main__":
    print("Running ML Pipeline for Project 1...")
    print("="*60)
    success, msg, results = run_ml_pipeline('project1', retrain_models=False)
    
    print("\n" + "="*60)
    if success:
        print("[SUCCESS] ML Pipeline completed successfully!")
        print(f"Message: {msg}")
    else:
        print("[FAILED] ML Pipeline failed!")
        print(f"Message: {msg}")
    
    print("="*60)
    print("Pipeline execution finished.")
