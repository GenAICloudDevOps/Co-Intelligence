import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.getcwd())

# Mock environment variables if needed
os.environ["DATABASE_URL"] = "postgres://user:pass@localhost:5432/db"

try:
    print("Importing MLPredictorCoordinator...")
    from apps.ml_predictor.agents.coordinator import MLPredictorCoordinator
    print("✓ Import successful")

    print("Initializing MLPredictorCoordinator...")
    coordinator = MLPredictorCoordinator()
    print("✓ Initialization successful")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
