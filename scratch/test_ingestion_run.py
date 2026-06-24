# scratch/test_ingestion_run.py

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.system_initializer import initialize_system
from consumer.consumer_service import ConsumerService

def run():
    initialize_system()
    ConsumerService().run_sync()

if __name__ == "__main__":
    run()
