"""
FAISS index builder for alignment data.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

try:
    import faiss
except ImportError:
    raise ImportError("FAISS is required. Install with: pip install faiss-gpu or faiss-cpu")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")


from retrieval.config import IndexConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlignmentIndexer:
    """Builds and manages FAISS index for text alignments."""

    def __init__(self, config: Optional[IndexConfig] = None):
        """
        Initialize the indexer.

        Args:
            config: Index configuration. Uses defaults if not provided.
        """
        self.config = config or IndexConfig()
        self.model = None
        self.index = None
        self.metadata = []

    def load_model(self):
        """Load the sentence transformer model."""
        if self.model is not None:
            logger.info("Model already loaded")
            return

        logger.info(f"Loading embedding model: {self.config.model_name}")
        logger.info(f"Using device: {self.config.device}")

        self.model = SentenceTransformer(
            self.config.model_name,
            device=self.config.device
        )

        logger.info(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def load_alignments(self, jsonl_path: Path) -> List[Dict[str, Any]]:
        """
        Load alignments from JSONL file.

        Args:
            jsonl_path: Path to alignment JSONL file

        Returns:
            List of alignment records
        """
        logger.info(f"Loading alignments from: {jsonl_path}")

        alignments = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                try:
                    record = json.loads(line.strip())
                    alignments.append(record)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON at line {i+1}: {e}")
                    continue

        logger.info(f"Loaded {len(alignments)} alignments")
        return alignments

    def embed_texts(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        """
        Embed a list of texts using the sentence transformer model.

        Args:
            texts: List of text strings to embed
            show_progress: Show progress bar

        Returns:
            numpy array of embeddings (num_texts, embedding_dim)
        """
        if self.model is None:
            self.load_model()

        logger.info(f"Embedding {len(texts)} texts...")

        embeddings = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=self.config.normalize_embeddings,
            convert_to_numpy=True
        )

        logger.info(f"Generated embeddings with shape: {embeddings.shape}")
        return embeddings

    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build FAISS index from embeddings.

        Args:
            embeddings: numpy array of embeddings

        Returns:
            FAISS index
        """
        dimension = embeddings.shape[1]
        num_vectors = embeddings.shape[0]

        logger.info(f"Building FAISS index (type: {self.config.index_type})")
        logger.info(f"Dimension: {dimension}, Vectors: {num_vectors}")

        # Build index based on configuration
        if self.config.index_type == "IndexFlatIP":
            # Inner product (use with normalized embeddings)
            index = faiss.IndexFlatIP(dimension)

        elif self.config.index_type == "IndexFlatL2":
            # L2 distance
            index = faiss.IndexFlatL2(dimension)

        elif self.config.index_type == "IndexIVFFlat":
            # IVF index for larger datasets
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(
                quantizer,
                dimension,
                self.config.nlist,
                faiss.METRIC_INNER_PRODUCT
            )

            # Train the index
            logger.info("Training IVF index...")
            index.train(embeddings.astype(np.float32))
            index.nprobe = self.config.nprobe

        else:
            raise ValueError(f"Unknown index type: {self.config.index_type}")

        # Add vectors to index
        logger.info("Adding vectors to index...")
        index.add(embeddings.astype(np.float32))

        logger.info(f"Index built. Total vectors: {index.ntotal}")

        return index

    def build_index(
        self,
        jsonl_path: Path,
        text_field: str = "src_text",
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Build complete index from alignment JSONL file.

        Args:
            jsonl_path: Path to alignment JSONL file
            text_field: Field name containing text to embed (default: "src_text")
            show_progress: Show progress bars

        Returns:
            Dictionary with build statistics
        """
        # Load alignments
        alignments = self.load_alignments(jsonl_path)

        if not alignments:
            raise ValueError("No alignments loaded")

        # Extract texts to embed
        texts = []
        metadata = []

        for i, alignment in enumerate(alignments):
            text = alignment.get(text_field, "")

            if not text:
                logger.warning(f"Skipping alignment {i}: missing '{text_field}'")
                continue

            texts.append(text)
            metadata.append({
                "id": i,
                "src_text": alignment.get("src_text", ""),
                "tgt_text": alignment.get("tgt_text", ""),
                "part": alignment.get("part", ""),
                "src_indices": alignment.get("src_indices", []),
                "tgt_indices": alignment.get("tgt_indices", []),
                "alignment_type": alignment.get("alignment_type", ""),
                "src_chunks": alignment.get("src_chunks", []),
                "tgt_chunks": alignment.get("tgt_chunks", [])
            })

        logger.info(f"Processing {len(texts)} texts from field '{text_field}'")

        # Load model and embed texts
        self.load_model()
        embeddings = self.embed_texts(texts, show_progress=show_progress)

        # Build FAISS index
        self.index = self.build_faiss_index(embeddings)
        self.metadata = metadata

        # Build statistics
        stats = {
            "num_alignments": len(alignments),
            "num_indexed": len(texts),
            "embedding_dim": embeddings.shape[1],
            "index_type": self.config.index_type,
            "model_name": self.config.model_name,
            "text_field": text_field
        }

        logger.info(f"Index built successfully: {stats}")

        return stats

    def save_index(self, output_dir: Optional[Path] = None):
        """
        Save FAISS index and metadata to disk.

        Args:
            output_dir: Output directory (uses config default if not provided)
        """
        if self.index is None:
            raise ValueError("No index to save. Build index first.")

        output_dir = output_dir or self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = output_dir / self.config.index_filename
        logger.info(f"Saving FAISS index to: {index_path}")
        faiss.write_index(self.index, str(index_path))

        # Save metadata
        metadata_path = output_dir / self.config.metadata_filename
        logger.info(f"Saving metadata to: {metadata_path}")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            for record in self.metadata:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

        # Save configuration
        config_path = output_dir / self.config.config_filename
        logger.info(f"Saving config to: {config_path}")
        config_dict = {
            "model_name": self.config.model_name,
            "index_type": self.config.index_type,
            "embedding_dim": self.model.get_sentence_embedding_dimension(),
            "normalize_embeddings": self.config.normalize_embeddings,
            "num_vectors": self.index.ntotal
        }

        if self.config.index_type == "IndexIVFFlat":
            config_dict["nlist"] = self.config.nlist
            config_dict["nprobe"] = self.config.nprobe

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Index saved successfully to: {output_dir}")

    def load_saved_index(self, index_dir: Path):
        """
        Load a previously saved index.

        Args:
            index_dir: Directory containing saved index files
        """
        logger.info(f"Loading index from: {index_dir}")

        # Load config
        config_path = index_dir / self.config.config_filename
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            saved_config = json.load(f)

        # Load FAISS index
        index_path = index_dir / self.config.index_filename
        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")

        logger.info(f"Loading FAISS index...")
        self.index = faiss.read_index(str(index_path))

        # Load metadata
        metadata_path = index_dir / self.config.metadata_filename
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

        logger.info(f"Loading metadata...")
        self.metadata = []
        with open(metadata_path, 'r', encoding='utf-8') as f:
            for line in f:
                self.metadata.append(json.loads(line.strip()))

        # Load model (if needed for querying)
        if saved_config.get("model_name"):
            self.config.model_name = saved_config["model_name"]

        logger.info(f"Index loaded successfully:")
        logger.info(f"  - Vectors: {self.index.ntotal}")
        logger.info(f"  - Metadata records: {len(self.metadata)}")
        logger.info(f"  - Model: {self.config.model_name}")