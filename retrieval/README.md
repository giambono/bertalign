# Retrieval System

FAISS-based retrieval system for cross-lingual text alignment.

## Overview

This module provides tools to build and query a vector similarity search system for English-Italian text alignments. It uses sentence transformers for embedding and FAISS for efficient similarity search.

## Components

- `config.py` - Configuration classes for indexing and retrieval
- `indexer.py` - FAISS index builder
- `build_index.py` - CLI tool for building indices
- `searcher.py` - Query interface (to be implemented)
- `reranker.py` - LLM-based re-ranking (to be implemented)

## Building an Index

### Basic Usage

```bash
# Build index from alignment file
python -m retrieval.build_index alignment_results.jsonl
```

This will:
1. Load alignments from the JSONL file
2. Embed `src_text` fields using a multilingual sentence transformer
3. Build a FAISS index
4. Save to `data/indices/`

### Advanced Options

```bash
# Specify output directory
python -m retrieval.build_index alignment_results.jsonl \
    --output-dir data/my_index

# Use a different embedding model
python -m retrieval.build_index alignment_results.jsonl \
    --model sentence-transformers/all-MiniLM-L6-v2 \
    --device cpu

# Build IVF index for large datasets (>100K vectors)
python -m retrieval.build_index alignment_results.jsonl \
    --index-type IndexIVFFlat \
    --nlist 100 \
    --nprobe 10

# Embed target text instead of source
python -m retrieval.build_index alignment_results.jsonl \
    --text-field tgt_text
```

### Command-Line Arguments

- `input_file` - Path to alignment JSONL file (required)
- `--output-dir` - Output directory (default: `data/indices`)
- `--text-field` - Field to embed (default: `src_text`)
- `--model` - Sentence transformer model (default: `paraphrase-multilingual-MiniLM-L12-v2`)
- `--device` - Device: `cuda` or `cpu` (default: `cuda`)
- `--batch-size` - Embedding batch size (default: 32)
- `--index-type` - FAISS index type: `IndexFlatIP`, `IndexFlatL2`, `IndexIVFFlat` (default: `IndexFlatIP`)
- `--nlist` - IVF clusters (default: 100)
- `--nprobe` - IVF search clusters (default: 10)
- `--no-normalize` - Don't normalize embeddings
- `--no-progress` - Hide progress bars

## Output Files

After building, the index directory contains:

```
data/indices/
├── embeddings.faiss      # FAISS index file
├── metadata.jsonl        # Alignment metadata (texts, indices, etc.)
└── index_config.json     # Index configuration
```

## Embedding Models

### Recommended Models

**Multilingual** (for cross-lingual scenarios):
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (default)
  - 384 dimensions, balanced speed/quality
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
  - 768 dimensions, higher quality, slower

**English-only** (if only querying in English):
- `sentence-transformers/all-MiniLM-L6-v2`
  - 384 dimensions, very fast
- `sentence-transformers/all-mpnet-base-v2`
  - 768 dimensions, high quality

### Model Comparison

| Model | Dimensions | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| multilingual-MiniLM-L12-v2 | 384 | Fast | Good | Default choice |
| multilingual-mpnet-base-v2 | 768 | Medium | Better | High quality needed |
| all-MiniLM-L6-v2 | 384 | Very fast | Good | English queries only |
| all-mpnet-base-v2 | 768 | Medium | Better | English, high quality |

## FAISS Index Types

### IndexFlatIP (Default)
- Inner product similarity
- Exact search, no approximation
- Best for: <100K vectors
- Requires: Normalized embeddings

### IndexFlatL2
- L2 (Euclidean) distance
- Exact search
- Best for: <100K vectors, unnormalized embeddings

### IndexIVFFlat
- Inverted file index with clustering
- Approximate search (faster)
- Best for: >100K vectors
- Parameters:
  - `nlist`: Number of clusters (e.g., sqrt(N))
  - `nprobe`: Clusters to search (higher = more accurate, slower)

## Programmatic Usage

```python
from pathlib import Path
from retrieval import AlignmentIndexer, IndexConfig

# Create configuration
config = IndexConfig(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cuda",
    batch_size=32,
    index_type="IndexFlatIP",
    output_dir=Path("data/indices")
)

# Build index
indexer = AlignmentIndexer(config=config)
stats = indexer.build_index(
    jsonl_path=Path("alignment_results.jsonl"),
    text_field="src_text"
)

# Save index
indexer.save_index()

print(f"Indexed {stats['num_indexed']} texts")
```

## Performance Tips

1. **GPU acceleration**: Use `--device cuda` if available (much faster)
2. **Batch size**: Increase `--batch-size` for faster embedding (if GPU memory allows)
3. **Large datasets**: Use `IndexIVFFlat` for >100K vectors
4. **Model selection**: Smaller models (384-dim) are 2x faster than larger (768-dim)
5. **Normalization**: Keep enabled for `IndexFlatIP` (cosine similarity)

## Troubleshooting

### CUDA Out of Memory
```bash
# Reduce batch size
python -m retrieval.build_index alignment_results.jsonl --batch-size 16

# Or use CPU
python -m retrieval.build_index alignment_results.jsonl --device cpu
```

### Slow Indexing
```bash
# Use smaller/faster model
python -m retrieval.build_index alignment_results.jsonl \
    --model sentence-transformers/all-MiniLM-L6-v2

# Increase batch size (if memory allows)
python -m retrieval.build_index alignment_results.jsonl --batch-size 64
```

### Index Too Large
```bash
# Use IVF index for compression
python -m retrieval.build_index alignment_results.jsonl \
    --index-type IndexIVFFlat
```

## Next Steps

After building the index:
1. Implement query interface (`searcher.py`)
2. Add LLM re-ranking (`reranker.py`)
3. Create API server for production use

See `/docs/retrieval_system_architecture.md` for full system design.