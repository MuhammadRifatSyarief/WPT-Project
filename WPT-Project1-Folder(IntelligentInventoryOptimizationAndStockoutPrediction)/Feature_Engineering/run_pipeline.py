"""
Run feature engineering pipeline with output logging
"""
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Capture all output
output_buffer = io.StringIO()
error_buffer = io.StringIO()

try:
    with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
        import feature_engineering_pipeline
        result = feature_engineering_pipeline.main()
except Exception as e:
    error_buffer.write(f"\n\nException: {str(e)}")
    import traceback
    traceback.print_exc(file=error_buffer)
    result = False

# Write outputs to log file
with open("pipeline_log.txt", "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(output_buffer.getvalue())
    f.write("\n\n=== STDERR ===\n")
    f.write(error_buffer.getvalue())
    f.write(f"\n\n=== RESULT ===\n")
    f.write(f"Success: {result}")

print(f"Log written to pipeline_log.txt")
print(f"Result: {'SUCCESS' if result else 'FAILED'}")
