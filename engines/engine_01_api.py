"""API-роутер для Engine #1: Хронологическая разметка."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_01_chronology import get_chronology_stats

def get_json_response():
    """Возвращает JSON для лендинга."""
    stats = get_chronology_stats()
    return stats

if __name__ == "__main__":
    print(json.dumps(get_json_response(), indent=2, ensure_ascii=False))
