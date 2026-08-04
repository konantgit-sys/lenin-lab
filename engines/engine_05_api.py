"""API для Engine #5: Машина времени."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_05_timemachine import run_timemachine

def get_json_response(date: str = "1917"):
    return run_timemachine(date)

if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else "1917"
    print(json.dumps(get_json_response(date), indent=2, ensure_ascii=False))
