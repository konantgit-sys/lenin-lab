"""API для Engine #6: Риторический отпечаток."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_06_rhetoric import get_rhetorical_fingerprint

if __name__ == "__main__":
    year = sys.argv[1] if len(sys.argv) > 1 else None
    result = get_rhetorical_fingerprint(year)
    print(json.dumps(result, indent=2, ensure_ascii=False))
