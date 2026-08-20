#!/usr/bin/env python3
"""
Export Lenin corpus DB → HuggingFace dataset (parquet).

Reads /home/agent/data/projects/lenin-knowledge/lenin.db and writes:
  data/paragraphs.parquet   — 169,067 rows
  data/quotes.parquet       — 5,000 curated quotes
  data/positions.parquet    — 1,529 Lenin positions
  data/dataset_info.json    — splits/features metadata for HF
"""
import sqlite3
import json
import pandas as pd
from pathlib import Path

DB = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")
OUT = Path("/home/agent/data/projects/lenin-hf/dataset")
OUT.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB)

def load(query: str) -> pd.DataFrame:
    return pd.read_sql_query(query, conn)

print("1/4 paragraphs ...")
par = load("""
    SELECT p.id, p.volume_id, p.paragraph_index, p.year, p.chapter, p.text
    FROM paragraphs p ORDER BY p.id
""")
print(f"   {len(par):,} rows | cols: {list(par.columns)}")

print("2/4 quotes ...")
quotes = load("""
    SELECT id, paragraph_id, year, volume_id, categories, topics, text
    FROM lenin_quotes ORDER BY id
""")
print(f"   {len(quotes):,} rows")

print("3/4 positions ...")
pos = load("""
    SELECT id, topic, year, volume_id, rank, text
    FROM lenin_positions ORDER BY id
""")
print(f"   {len(pos):,} rows")

# Write parquet
par.to_parquet(OUT / "paragraphs.parquet", index=False)
quotes.to_parquet(OUT / "quotes.parquet", index=False)
pos.to_parquet(OUT / "positions.parquet", index=False)

# Dataset card metadata
info = {
    "name": "lenin-complete-works",
    "description": "Lenin Complete Works: 55 volumes, 169,067 annotated paragraphs (1893-1922) with year, volume, chapter, position. Includes 5,000 curated quotes and 1,529 Lenin positions.",
    "languages": ["ru"],
    "license": "texts: public domain; annotations: CC BY 4.0",
    "features": {
        "paragraphs": ["id:int", "volume_id:int", "paragraph_index:int", "year:int", "chapter:str", "text:str"],
        "quotes": ["id:int", "paragraph_id:int", "year:int", "volume_id:int", "categories:str", "topics:str", "text:str"],
        "positions": ["id:int", "topic:str", "year:int", "volume_id:int", "rank:int", "text:str"],
    },
    "splits": {"train": 169067},
    "size": {"paragraphs_bytes": int(par["text"].str.len().sum())},
    "years": {"from": int(par["year"].min()), "to": int(par["year"].max())},
    "volumes": 55,
    "built_with": "V2Bot Agent (github.com/konantgit-sys/lenin-lab)",
}
(OUT / "dataset_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n=== ИТОГ ===")
for f in sorted(OUT.glob("*")):
    print(f"  {f.name}: {f.stat().st_size/1e6:.1f} MB")
print("OK")
