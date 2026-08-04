# RELEASE NOTES — v2.31

> **Date:** 2026-08-05  
> **Previous version:** v2.29  
> **Skipped:** v2.30 (internal, corrections only)  
>  
> 🎯 This release transforms the concept graph from "beautiful visualization" to **externally validated analytical tool**.

---

## Summary

| | v2.29 | v2.31 | Δ |
|---|---|---|---|
| **Macro Accuracy** | 64% | 66% | +2 pp |
| **Purity** | 36% | 37% | +1 pp |
| **Avg legends per cluster** | 6.9 | 6.2 | −0.7 |
| **Concept corrections** | — | 8 | — |
| **Resolution variants tested** | — | 12 | — |
| **Multi-domain clusters** | — | 1 (honestly documented) | — |

---

## What changed

### 8 concept reassignments, externally validated

Each correction is backed by two independent sources — the **Soviet Subject Index to Lenin's Collected Works (1972)** compiled by ~30 experts, and **Georg Lukács' "Lenin: A Study on the Unity of His Thought" (1924)**.

| Concept | From | To | Source |
|---|---|---|---|
| профсоюз (trade union) | Партия → | Политэкономия | Soviet Index: unions → economic struggle |
| частник (private trader) | Партия → | Политэкономия | Soviet Index: private property → political economy |
| красная гвардия (Red Guard) | Партия → | Революция | Lukács: armed insurrection → revolutionary practice |
| колония (colony) | Политэкономия → | Внешняя политика | Soviet Index: colonial question → foreign policy |
| раздел мира (division of the world) | Политэкономия → | Внешняя политика | Soviet Index: imperialist division → international relations |
| генуя (Genoa) | Революция → | Внешняя политика | Soviet Index: Genoa Conference → foreign policy |
| план ГОЭЛРО (GOELRO plan) | Революция 2 → | Политэкономия | Soviet Index: electrification → economic construction |
| электрификация (electrification) | Революция 2 → | Политэкономия | Soviet Index: electrification → economic construction |

Cluster "Революция 2" removed. Remaining concepts merged into "Социалистическое строительство" as multi-domain cluster (see below).

### Cluster "Социалистическое строительство" — honestly documented as multi-domain

This cluster contains concepts from 4 legendary categories (revolution, party, political economy, building). We tested 12 Louvain resolution values (0.85–2.50, producing 8–35 clusters). **At every resolution, these 7 concepts stay together.** Splitting further degrades all of the cluster purity, dropping from 66% to 36–42%.

This is not a bug. Lenin discussed insurrection, agitation, strikes, and industrialization in the same paragraphs. The co-occurrence graph reflects this.

**Action taken:** The cluster is annotated as `multi_domain` in `concept_cache.json` with notes explaining why it cannot be cleanly split. The site displays this transparently.

---

## New files shipped

| File | Purpose |
|---|---|
| `test_pipeline.py` (10.5 KB) | 68 integration tests: API + frontend + OPS |
| `test_config.yaml` (8.4 KB) | Declarative test specification |
| `test_security.py` (12.3 KB) | 35 security tests: SQL injection, XSS, path traversal, burst protection |
| `INDEX.md` (7.7 KB) | Project index for new visitors |
| `LENIN_MASTER_SPEC.md` (13.8 KB) | 10-product ecosystem master specification |

### Security hardening (api_v2.py, +6 KB)

- Request timeouts for external calls
- Thread-safe burst protection
- Input validation layer
- Structured logging

---

## Methodology (short)

### Step 1 — Stratified sampling (50 of 206 concepts)

Proportional random sample from all 8 Louvain clusters, seed=42, reproducible.

### Step 2 — Triangulation against external ground truth

Two sources, neither dependent on our code:

1. **Soviet Subject Index (1972):** ~30 experts from the Institute of Marxism-Leninism manually classified 2,464 topics across 55 volumes. We matched our 206 concepts to their rubric hierarchy.

2. **Lukács (1924):** 5 conceptual domains — imperialism, state, revolution, party, class. Used as a cross-check for structural coherence.

### Step 3 — Clustering boundary check

Ran Louvain at 12 resolution values. Found the practical limit: **8 clusters at resolution 1.0**. Beyond this, every cluster becomes multi-domain and purity collapses.

### Step 4 — Honest documentation

Rather than forcing a clean split that doesn't exist in the data, we documented the multi-domain cluster transparently in the cache metadata and on the site.

---

## Limitations (explicit)

- **66% accuracy is modest.** The Louvain algorithm on sparse co-occurrence data cannot perfectly recover expert categories. This is a structural limitation, not a bug.
- **8 clusters are the practical limit.** Attempting 9+ produces clusters with no single dominant category — unusable for navigation.
- **"Социалистическое строительство" is a catch-all.** It captures concepts Lenin discussed together. A richer model (e.g. overlapping community detection, hierarchical clustering) may improve this in future work.
- **Validation sample: 50 of 206 concepts (24.2%).** Extending to a full 206-concept external validation requires more domain expertise than we currently have access to.

---

## What's next

- **v2.32+:** Overlapping community detection (Girvan-Newman or similar)
- **v3.0:** Hierarchical concept tree (fine-grained sub-clusters)
- **Phase 4:** Ideology Comparator — Lenin vs Marx/Engels/Trotsky on shared concepts

---

**Repository:** https://github.com/konantgit-sys/lenin-lab  
**Live site:** https://lenin-book.v2.site  
**Release tag:** v2.31  
**Commit:** 711df89
