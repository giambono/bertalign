# Cross-Lingual Retrieval System Architecture

## Overview

This document outlines the architecture for a retrieval system that accepts English text queries and returns matching English-Italian text pairs from the alignment corpus.

## System Goal

Given a user query in English, retrieve the most relevant alignment pair:
- **Input**: English sentence/text
- **Output**: Matched English text + corresponding Italian text

## Architecture Components

### Phase 1: Indexing (Offline)

The indexing phase processes alignment data and builds a searchable index.

```
alignment_results.jsonl (source data)
    ↓
[Load alignments]
    ↓
For each alignment:
  - src_text (English)
  - tgt_text (Italian)
  - metadata (part, indices, chunks, etc.)
    ↓
[Embed English texts using sentence-transformers]
    ↓
[Build FAISS vector index]
    ↓
Store:
  - embeddings.faiss (vector index)
  - metadata.jsonl (text pairs + metadata)
```

#### Embedding Model Selection

**Option 1: Multilingual Model** (Recommended for cross-lingual scenarios)
- Models: `multilingual-e5-large`, `paraphrase-multilingual-MiniLM-L12-v2`
- Pros: Can embed both English and Italian, enables cross-lingual queries
- Cons: Slightly larger model size

**Option 2: English-only Model** (Recommended for English-to-English matching)
- Models: `all-MiniLM-L6-v2`, `all-mpnet-base-v2`
- Pros: Faster, smaller, optimized for English
- Cons: Only embeds English text

**Recommendation**: Use `multilingual-e5-base` or `paraphrase-multilingual-MiniLM-L12-v2` for flexibility.

#### Vector Store Selection

**Option 1: FAISS** (Already in dependencies)
- Pros: Fast, memory-efficient, battle-tested
- Cons: In-memory (need to load on startup)
- Best for: Up to ~1M vectors

**Option 2: ChromaDB**
- Pros: Persistent storage, built-in metadata filtering
- Cons: Additional dependency
- Best for: Smaller datasets with rich metadata queries

**Option 3: Qdrant**
- Pros: Production-ready, HTTP API, filtering
- Cons: Requires separate service
- Best for: Production deployments

**Recommendation**: Start with FAISS, migrate to Qdrant if needed for production.

### Phase 2: Query (Runtime)

The query phase handles user requests and returns relevant results.

```
User query: "some English text"
    ↓
[Embed query using same model as indexing]
    ↓
Query vector: [0.23, -0.45, 0.67, ...]
    ↓
[FAISS similarity search]
    ↓
Retrieve top-k candidates (k=10-20)
    ↓
[Optional: LLM re-ranking/filtering]
    ↓
Return top-N results (N=5)
    ↓
Output: [
  {
    "score": 0.92,
    "src_text": "matched English text",
    "tgt_text": "corrispondente testo italiano",
    "metadata": {...}
  },
  ...
]
```

## Three Implementation Approaches

### Approach 1: Pure Vector Similarity (Fast & Simple)

**Architecture:**
```
Query → Embed → FAISS search → Return top-k pairs
```

**Components:**
- Embedding model (sentence-transformers)
- FAISS index
- Metadata lookup

**Pros:**
- Fast (<10ms per query)
- Simple implementation (~100 lines)
- No runtime LLM cost
- Scales to millions of documents

**Cons:**
- May return semantically similar but contextually wrong matches
- No quality validation

**Best for:**
- Interactive applications
- Large-scale retrieval
- High-throughput scenarios

**Code estimate:** ~150 lines (indexing + query)

---

### Approach 2: Vector Search + LLM Re-ranking (Balanced)

**Architecture:**
```
Query → Embed → FAISS top-20 → vLLM re-rank → Return top-5
```

**Components:**
- Embedding model
- FAISS index
- vLLM/Qwen for validation (reuse existing Docker service)
- Metadata lookup

**Workflow:**
1. Vector search retrieves 20 candidates
2. LLM scores each candidate (0-1) for relevance
3. Sort by LLM score and return top 5

**Pros:**
- Higher precision
- Validates semantic match quality
- Can handle nuanced queries
- Reuses existing vLLM infrastructure

**Cons:**
- Slower (~500ms-2s per query depending on LLM)
- LLM inference cost
- More complex implementation

**Best for:**
- When accuracy > speed
- Research/analysis applications
- Validation scenarios

**Code estimate:** ~300 lines (indexing + query + re-ranking)

---

### Approach 3: Hybrid Search (BM25 + Vectors + LLM)

**Architecture:**
```
Query → Parallel:
  ├─ Vector search (semantic) → top-k
  └─ BM25 search (keyword) → top-k
       ↓
  Reciprocal Rank Fusion → top-20
       ↓
  LLM re-rank → top-5
```

**Components:**
- Embedding model
- FAISS index
- BM25 index (using rank-bm25 or Elasticsearch)
- vLLM for re-ranking
- Fusion algorithm

**Pros:**
- Best recall (catches both semantic and exact matches)
- Robust to query variations
- Production-grade quality

**Cons:**
- Most complex to implement
- Requires maintaining two indices
- Slower query time

**Best for:**
- Production systems
- Critical applications requiring high recall
- Diverse query types

**Code estimate:** ~500 lines (full system)

---

## Recommended Technology Stack

Based on existing project dependencies:

### Core Components
```python
# Already available:
- sentence-transformers  # For embeddings
- faiss-gpu             # For vector search
- openai                # For vLLM client
- Docker + vLLM         # For LLM re-ranking

# Additional needed:
- fastapi               # For API server (optional)
- uvicorn               # For serving (optional)
```

### Recommended Starting Point

**Approach 2** (Vector + LLM Re-ranking) because:
1. Leverages existing vLLM infrastructure
2. Balances speed and accuracy
3. Validates retrieval quality
4. Aligns with existing validation script

## Example Data Flow

### Indexing Example
```python
# Input alignment
{
  "part": "006",
  "src_text": "consumed by the force of some incomprehensibly distant edict...",
  "tgt_text": "impensabilmente lontana – come questo libro...",
  "src_indices": [1011, 1012],
  "tgt_indices": [846, 847]
}

↓ [Embed src_text]

embedding: [0.23, -0.45, 0.67, ..., 0.12]  # 768-dim vector

↓ [Add to FAISS]

Index entry: id=42 → embedding
Metadata: id=42 → full alignment record
```

### Query Example
```python
# User query
"some incomprehensibly distant command"

↓ [Embed query]

query_vector: [0.21, -0.43, 0.69, ..., 0.11]

↓ [FAISS search, k=10]

Candidates:
1. score=0.92, id=42: "consumed by the force of some incomprehensibly..."
2. score=0.87, id=115: "under the influence of a remote decree..."
3. score=0.84, id=203: "following orders from far away..."
...

↓ [LLM re-rank top 10]

LLM prompt for each:
"Query: 'some incomprehensibly distant command'
Candidate: 'consumed by the force of some incomprehensibly distant edict'
Relevance score (0-1):"

LLM scores:
1. id=42: 0.95 (strong semantic match)
2. id=115: 0.78 (related but different phrasing)
3. id=203: 0.65 (loosely related)

↓ [Sort by LLM score, return top 5]

Final results:
[
  {
    "rank": 1,
    "similarity_score": 0.92,
    "llm_score": 0.95,
    "src_text": "consumed by the force of some incomprehensibly distant edict...",
    "tgt_text": "impensabilmente lontana – come questo libro...",
    "metadata": {"part": "006", ...}
  },
  ...
]
```

## Proposed File Structure

```
bertalign/
├── validation/
│   ├── validate_alignments.py    # Existing validation script
│   └── README.md
│
├── retrieval/                     # New directory
│   ├── __init__.py
│   ├── indexer.py                # Build FAISS index from alignments
│   ├── searcher.py               # Query interface
│   ├── reranker.py               # LLM-based re-ranking
│   ├── config.py                 # Configuration
│   └── README.md                 # Usage documentation
│
├── api/                          # Optional: API server
│   ├── __init__.py
│   ├── server.py                 # FastAPI server
│   └── schemas.py                # Pydantic models
│
├── data/                         # Generated indices
│   ├── embeddings.faiss          # FAISS index file
│   ├── metadata.jsonl            # Alignment metadata
│   └── config.json               # Index metadata (model name, etc.)
│
├── docs/
│   └── retrieval_system_architecture.md  # This document
│
└── scripts/
    ├── build_index.sh            # Helper script to build index
    └── serve_api.sh              # Helper script to start API
```

## Implementation Phases

### Phase 1: Basic Retrieval (Week 1)
- [ ] Implement `indexer.py` - build FAISS index from alignments
- [ ] Implement `searcher.py` - basic vector similarity search
- [ ] CLI interface for testing
- [ ] Validation with sample queries

**Deliverable**: Working command-line retrieval tool

### Phase 2: LLM Re-ranking (Week 2)
- [ ] Implement `reranker.py` - integrate with vLLM
- [ ] Design re-ranking prompts
- [ ] Compare results with/without re-ranking
- [ ] Optimize top-k parameters

**Deliverable**: Enhanced retrieval with quality validation

### Phase 3: API Server (Week 3)
- [ ] Implement FastAPI server
- [ ] Add batch query support
- [ ] Add filtering by metadata (part, page, etc.)
- [ ] Documentation and examples

**Deliverable**: Production-ready API

### Phase 4: Optimization (Week 4)
- [ ] Benchmark different embedding models
- [ ] Tune FAISS parameters (nprobe, etc.)
- [ ] Add caching for common queries
- [ ] Performance monitoring

**Deliverable**: Optimized system with benchmarks

## Configuration Options

### Embedding Configuration
```python
{
  "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
  "device": "cuda",  # or "cpu"
  "batch_size": 32,
  "normalize_embeddings": true
}
```

### FAISS Configuration
```python
{
  "index_type": "IndexFlatIP",  # Inner product (for normalized vectors)
  # For larger datasets:
  # "index_type": "IndexIVFFlat",
  # "nlist": 100,  # number of clusters
  # "nprobe": 10   # search clusters
}
```

### Re-ranking Configuration
```python
{
  "enabled": true,
  "top_k_candidates": 20,  # retrieve from vector search
  "top_n_results": 5,      # return after re-ranking
  "llm_model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
  "llm_host": "localhost",
  "llm_port": 8000,
  "temperature": 0.1
}
```

### Query Configuration
```python
{
  "default_top_k": 10,
  "max_top_k": 100,
  "similarity_threshold": 0.7,  # minimum similarity score
  "enable_metadata_filter": true
}
```

## Evaluation Metrics

To measure system quality:

1. **Precision@k**: How many of top-k results are relevant?
2. **Recall@k**: What fraction of relevant documents are in top-k?
3. **MRR (Mean Reciprocal Rank)**: Average position of first relevant result
4. **Latency**: Query response time
5. **Throughput**: Queries per second

### Evaluation Setup
```python
# Create test set from validated alignments
test_queries = [
  {
    "query": "some text from src_text",
    "expected_id": 42,  # alignment id
    "variations": ["paraphrase 1", "paraphrase 2"]
  },
  ...
]

# Run evaluation
for test in test_queries:
  results = retrieval_system.search(test["query"], top_k=10)
  check if test["expected_id"] in results
  measure rank position
```

## Security Considerations

1. **Input validation**: Sanitize user queries
2. **Rate limiting**: Prevent API abuse
3. **Query length limits**: Avoid excessive LLM costs
4. **Authentication**: If deploying as service
5. **Logging**: Track queries for debugging (respect privacy)

## Scaling Considerations

### Small Scale (<100K alignments)
- In-memory FAISS
- Single process
- Simple Python script

### Medium Scale (100K-1M alignments)
- Memory-mapped FAISS
- Multi-process workers
- Redis caching
- Load balancer

### Large Scale (>1M alignments)
- Sharded FAISS indices
- Distributed search (e.g., Qdrant cluster)
- Async processing
- Horizontal scaling

## Next Steps

1. **Decide on approach**: Start with Approach 2 (Vector + LLM)?
2. **Choose embedding model**: Test multilingual vs English-only
3. **Build indexer**: Create FAISS index from alignment_results.jsonl
4. **Test retrieval**: Validate with sample queries
5. **Add re-ranking**: Integrate vLLM for quality filtering
6. **Deploy API**: FastAPI server for production use

## References

- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)
- [Retrieval Augmented Generation (RAG)](https://arxiv.org/abs/2005.11401)
- [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)