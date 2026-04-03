@echo off
REM Cleanup script for Privacy Advisor SL
REM Removes old test and temporary Python scripts from root directory

cd /d e:\privacy_advisor_sl

echo Cleaning up temporary and old test files...

del debug_clauses.py 2>nul
del debug_output.txt 2>nul
del temp_output.txt 2>nul
del verify_claims.py 2>nul
del verify_claims2.py 2>nul
del comprehensive_quality_fix.py 2>nul
del fix_legal_clauses_quality.py 2>nul
del enhance_legal_clauses.py 2>nul
del prepare_ml_training.py 2>nul
del quick_ml_integration.py 2>nul
del show_impact_report.py 2>nul
del show_training_complete.py 2>nul
del train_classifier_model.py 2>nul
del train_semantic_model.py 2>nul
del train_semantic_model_simple.py 2>nul
del integrate_ml_training.py 2>nul
del test_system.py 2>nul
del test_explanations.py 2>nul
del verify_enhancements.py 2>nul
del verify_training_data.py 2>nul
del stress_results.txt 2>nul

echo.
echo Cleanup complete! 
echo Old temporary files have been removed.
echo.
echo Remaining important files:
dir /b *.py *.md *.txt | find /v "cleanup"
pause
