"""API для Engine #9: Сравнительный анализатор."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_09_comparative import search_comparison, list_comparisons


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--list":
            comps = list_comparisons()
            print(json.dumps({"total": len(comps), "topics": comps}, indent=2, ensure_ascii=False))
        else:
            comp = search_comparison(cmd)
            if comp:
                print(json.dumps(comp, indent=2, ensure_ascii=False))
            else:
                print(json.dumps({"error": f"Topic '{cmd}' not found"}, indent=2, ensure_ascii=False))
    else:
        comps = list_comparisons()
        print(json.dumps({"total": len(comps), "topics": [c["topic"] for c in comps]}, indent=2, ensure_ascii=False))
