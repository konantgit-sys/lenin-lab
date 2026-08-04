"""API-роутер для Engine #3: Диалектический парсер."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_03_dialectics import get_dialectical_stats

def get_json_response():
    stats = get_dialectical_stats()
    return stats

if __name__ == "__main__":
    print(json.dumps(get_json_response(), indent=2, ensure_ascii=False))
