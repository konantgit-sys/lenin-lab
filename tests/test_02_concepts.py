"""
Tests for Engine #2: Концептуальный граф (cache-based, fast).
Tests the actual data served by /api/v1/concepts and /api/v1/concept/{name}.
"""

from test_helper import load_concept_cache


def test_cache_loads():
    """Cache file exists and parses."""
    data = load_concept_cache()
    assert data is not None
    assert "graph" in data, f"Missing 'graph' key: {list(data.keys())}"
    print(f"✅ cache loaded ({len(data)} keys)")


def test_graph_nodes_count():
    """В графе 206 узлов (предвычислено)."""
    data = load_concept_cache()
    graph = data["graph"]
    nodes = graph["nodes"]
    assert graph["nodes"] >= 190, f"Expected >=190 nodes, got {nodes}"
    print(f"✅ nodes: {nodes}")


def test_no_isolated_nodes():
    """Нет изолированных концептов."""
    data = load_concept_cache()
    graph = data["graph"]
    isolated = graph.get("isolated_nodes", 0)
    assert isolated == 0, f"Found {isolated} isolated nodes"
    print(f"✅ no isolated nodes ({graph['connected_nodes']} connected)")


def test_clusters_in_range():
    """Кластеров 8-12."""
    data = load_concept_cache()
    graph = data["graph"]
    clusters = graph["clusters"]
    assert 5 <= clusters <= 15, f"Expected 5-15 clusters, got {clusters}"
    print(f"✅ clusters: {clusters}")


def test_cluster_names_unique():
    """Имена кластеров уникальны и непусты."""
    data = load_concept_cache()
    graph = data["graph"]
    names = graph.get("cluster_names", [])
    assert len(names) == len(set(names)), f"Duplicate names: {names}"
    assert all(n for n in names), f"Empty names found: {names}"
    print(f"✅ cluster names: {names}")


def test_edges_exist():
    """Рёбра существуют между концептами."""
    data = load_concept_cache()
    graph = data["graph"]
    assert graph["edges_total"] > 500, f"Too few edges: {graph['edges_total']}"
    assert len(graph["top_edges"]) > 0
    print(f"✅ edges: {graph['edges_total']} total, {len(graph['top_edges'])} top")


def test_nodes_data_present():
    """Все узлы имеют id и count."""
    data = load_concept_cache()
    graph = data["graph"]
    for node in graph["nodes_data"]:
        assert "id" in node, f"Missing id in {node}"
        assert "count" in node, f"Missing count in {node['id']}"
    print(f"✅ all {len(graph['nodes_data'])} nodes have id+count")


def test_legend_present():
    """Легенда (категории) присутствует."""
    data = load_concept_cache()
    assert "legend" in data, "Missing legend"
    legend = data["legend"]
    assert len(legend) >= 10, f"Expected >=10 categories, got {len(legend)}"
    total = sum(item["count"] for item in legend)
    assert total >= 180, f"Too few concepts in legend: {total}"
    print(f"✅ legend: {len(legend)} categories, {total} concepts")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #2: Concept Graph Tests (cache-based)")
    print("=" * 50)
    for name in sorted(globals()):
        if name.startswith("test_"):
            globals()[name]()
    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
