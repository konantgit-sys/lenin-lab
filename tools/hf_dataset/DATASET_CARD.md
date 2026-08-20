---
license: cc-by-4.0
language:
- ru
tags:
- lenin
- russian
- historical-corpus
- nlp
- full-text-search
- digital-humanities
- 20th-century
pretty_name: Lenin Complete Works (55 volumes, annotated)
task_categories:
- text-classification
- text-generation
- question-answering
---

# Lenin Complete Works — Annotated Corpus

**55 volumes · 169,067 paragraphs · 1893–1922 · Russian language**

A complete, machine-readable corpus of V. I. Lenin's collected works (Полное собрание сочинений, 5-е издание) with rich metadata — ready for historical NLP, digital humanities research, and language model work.

## Highlights

- **Complete**: all 55 volumes of the 5th edition, every paragraph with stable ID.
- **Annotated**: each paragraph carries `year`, `volume_id`, `chapter`, `paragraph_index`.
- **Curated quotes**: 5,000 top aphorisms/citations with categories and topics, ranked by relevance score.
- **Lenin positions**: 1,529 extracted positions (policy stances) with topic and rank.
- **No boilerplate**: headers, footnotes and editorial noise are excluded; text is clean prose.
- **Provenance**: built with a reproducible pipeline; full project with 100/100 tests and live API at [lenin-book.v2.site](https://lenin-book.v2.site).

## Dataset Structure

### `paragraphs` (169,067 rows)
| field | type | description |
|---|---|---|
| id | int | stable paragraph ID |
| volume_id | int | volume number (1–55) |
| paragraph_index | int | position inside the volume |
| year | int | year of writing (1893–1922) |
| chapter | str | chapter/section title |
| text | str | paragraph text (Russian) |

### `quotes` (5,000 rows)
Curated citations with `categories`, `topics`, `year`, `volume_id`, `paragraph_id`.

### `positions` (1,529 rows)
Extracted Lenin positions: `topic`, `rank`, `year`, `volume_id`, `text`.

## Use Cases

- Historical text analysis and stylometry of early-20th-century Russian political prose
- Chronological studies: how ideas evolved 1893→1922 (`year` field enables time-series NLP)
- Fine-tuning / evaluation of Russian language models on historical register
- Benchmark for retrieval (semantic search over the corpus)

## Licensing

- **The source texts** (Lenin's works) are in the **public domain** (author died 1924).
- **The annotations, metadata and dataset curation** are licensed under **CC BY 4.0** — free for commercial and academic use with attribution.

## Citation

```bibtex
@misc{lenin-complete-works-2026,
  title={Lenin Complete Works: An Annotated Corpus of 55 Volumes for Historical NLP},
  author={Anton K. and V2Bot Agent},
  year={2026},
  howpublished={https://huggingface.co/datasets/konantgit/lenin-complete-works},
  note={Built with the open-source pipeline: github.com/konantgit-sys/lenin-lab}
}
```

## Built With

The corpus is produced by the [lenin-lab](https://github.com/konantgit-sys/lenin-lab) pipeline: 9 analytical engines (full-text search, timeline, concept graph with 206 concepts / 12,735 edges, semantic Oracle with 93,711 embeddings, comparative analysis, dialectics), 100/100 tests, continuous integration. A live API with the same corpus runs at [lenin-book.v2.site](https://lenin-book.v2.site). Co-created with V2Bot Agent ([v2bot.ai](https://v2bot.ai/?r=FC28B6B3)).
