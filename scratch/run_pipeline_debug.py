# scratch/run_pipeline_debug.py

import sys
import os
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pipeline_orchestrator import PipelineOrchestrator

try:
    print("Starting pipeline run...")
    PipelineOrchestrator.run_pipeline()
    print("Pipeline run completed successfully.")
except Exception as e:
    print(f"Pipeline crashed with error: {e}")
    with open("scratch/pipeline_error.txt", "w") as f:
        traceback.print_exc(file=f)
    sys.exit(1)
