"""
Configuration classes for the retrieval system.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from pathlib import Path


@dataclass
class IndexConfig:
    """Configuration for building the FAISS index."""

    # Embedding model configuration
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cuda"  # or "cpu"
    batch_size: int = 32
    normalize_embeddings: bool = True

    # FAISS index configuration
    index_type: Literal["IndexFlatIP", "IndexFlatL2", "IndexIVFFlat"] = "IndexFlatIP"
    # For IndexIVFFlat (larger datasets):
    nlist: Optional[int] = 100  # number of clusters
    nprobe: Optional[int] = 10  # clusters to search

    # Output configuration
    output_dir: Path = Path("data/indices")
    index_filename: str = "embeddings.faiss"
    metadata_filename: str = "metadata.jsonl"
    config_filename: str = "index_config.json"

    def __post_init__(self):
        """Convert Path strings to Path objects."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)


@dataclass
class RetrievalConfig:
    """Configuration for querying the retrieval system."""

    # Index paths
    index_dir: Path = Path("data/indices")

    # Query parameters
    default_top_k: int = 10
    max_top_k: int = 100
    similarity_threshold: float = 0.0  # minimum similarity score (0-1)

    # Re-ranking configuration
    enable_reranking: bool = False
    rerank_top_k: int = 20  # candidates for re-ranking
    rerank_top_n: int = 5   # final results after re-ranking

    # LLM configuration (for re-ranking)
    llm_model: str = "Qwen/Qwen2.5-32B-Instruct-AWQ"
    llm_host: str = "localhost"
    llm_port: int = 8000
    llm_temperature: float = 0.1
    llm_max_tokens: int = 200

    # Metadata filtering
    enable_metadata_filter: bool = True

    def __post_init__(self):
        """Convert Path strings to Path objects."""
        if isinstance(self.index_dir, str):
            self.index_dir = Path(self.index_dir)