"""API-роутер для Engine #2: Концептуальный граф."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_02_concepts import get_concept_graph, get_concept_evolution, get_legend


def get_graph_json():
    """Возвращает JSON графа для D3.js визуализации."""
    graph = get_concept_graph()
    return graph


def get_evolution_json(concept: str = "революция"):
    """Возвращает JSON эволюции концепта."""
    return get_concept_evolution(concept)


def get_legend_json():
    """Возвращает JSON легенды кластеров."""
    return get_legend()


if __name__ == "__main__":
    data = get_graph_json()
    # Формат для D3.js: nodes + links
    d3_format = {
        "nodes": data["nodes_data"],
        "links": data["top_edges"],
        "clusters": data["cluster_names"],
        "stats": {
            "nodes": data["nodes"],
            "edges_total": data["edges_total"],
            "clusters": data["clusters"],
        }
    }
    print(json.dumps(d3_format, indent=2, ensure_ascii=False))
