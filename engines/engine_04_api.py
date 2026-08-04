"""API-роутер для Engine #4: Карта оппонентов."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_04_opponents import get_opponent_stats

def get_json_response():
    return get_opponent_stats()

if __name__ == "__main__":
    print(json.dumps(get_json_response(), indent=2, ensure_ascii=False))
