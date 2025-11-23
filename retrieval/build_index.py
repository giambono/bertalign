#!/usr/bin/env python3
"""
Command-line tool to build FAISS index from alignment data.
"""

import argparse
import sys
from pathlib import Path
import logging

from retrieval.config import IndexConfig
from retrieval.indexer import AlignmentIndexer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Build FAISS index from alignment JSONL file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build index from alignments with defaults
  python -m retrieval.build_index alignment_results.jsonl

  # Specify output directory and custom model
  python -m retrieval.build_index alignment_results.jsonl \\
      --output-dir data/my_index \\
      --model sentence-transformers/all-MiniLM-L6-v2

  # Use CPU instead of GPU
  python -m retrieval.build_index alignment_results.jsonl --device cpu

  # Build IVF index for larger datasets
  python -m retrieval.build_index alignment_results.jsonl \\
      --index-type IndexIVFFlat \\
      --nlist 100 \\
      --nprobe 10
        """
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Input JSONL file containing alignments"
    )

    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("data/indices"),
        help="Output directory for index files (default: data/indices)"
    )

    parser.add_argument(
        "--text-field",
        default="src_text",
        help="Field name to embed (default: src_text)"
    )

    parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="Sentence transformer model name (default: paraphrase-multilingual-MiniLM-L12-v2)"
    )

    parser.add_argument(
        "--device",
        choices=["cuda", "cpu"],
        default="cuda",
        help="Device to use for embedding (default: cuda)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding (default: 32)"
    )

    parser.add_argument(
        "--index-type",
        choices=["IndexFlatIP", "IndexFlatL2", "IndexIVFFlat"],
        default="IndexFlatIP",
        help="FAISS index type (default: IndexFlatIP)"
    )

    parser.add_argument(
        "--nlist",
        type=int,
        default=100,
        help="Number of clusters for IVF index (default: 100)"
    )

    parser.add_argument(
        "--nprobe",
        type=int,
        default=10,
        help="Number of clusters to search for IVF index (default: 10)"
    )

    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Don't normalize embeddings (default: normalize)"
    )

    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Don't show progress bars"
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input_file.exists():
        logger.error(f"Input file not found: {args.input_file}")
        sys.exit(1)

    # Create configuration
    config = IndexConfig(
        model_name=args.model,
        device=args.device,
        batch_size=args.batch_size,
        normalize_embeddings=not args.no_normalize,
        index_type=args.index_type,
        nlist=args.nlist,
        nprobe=args.nprobe,
        output_dir=args.output_dir
    )

    logger.info("=" * 80)
    logger.info("FAISS Index Builder")
    logger.info("=" * 80)
    logger.info(f"Input file: {args.input_file}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Text field: {args.text_field}")
    logger.info(f"Model: {config.model_name}")
    logger.info(f"Device: {config.device}")
    logger.info(f"Index type: {config.index_type}")
    logger.info(f"Normalize embeddings: {config.normalize_embeddings}")
    logger.info("=" * 80)

    try:
        # Create indexer
        indexer = AlignmentIndexer(config=config)

        # Build index
        stats = indexer.build_index(
            jsonl_path=args.input_file,
            text_field=args.text_field,
            show_progress=not args.no_progress
        )

        # Save index
        indexer.save_index()

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("INDEX BUILD SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total alignments: {stats['num_alignments']}")
        logger.info(f"Indexed texts: {stats['num_indexed']}")
        logger.info(f"Embedding dimension: {stats['embedding_dim']}")
        logger.info(f"Index type: {stats['index_type']}")
        logger.info(f"Model: {stats['model_name']}")
        logger.info(f"Text field: {stats['text_field']}")
        logger.info("")
        logger.info(f"Index saved to: {args.output_dir}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error building index: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()