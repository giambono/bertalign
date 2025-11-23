#!/usr/bin/env python3
"""
Quick test script to verify index can be loaded and queried.
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval import AlignmentIndexer, IndexConfig


def test_index_load_and_search():
    """Test loading index and performing basic search."""

    index_dir = Path("/home/rp/git/playground/bertalign/data/my_index")

    print("Loading index...")
    indexer = AlignmentIndexer()
    indexer.load_saved_index(index_dir)

    print(f"Index loaded successfully!")
    print(f"  Vectors: {indexer.index.ntotal}")
    print(f"  Metadata records: {len(indexer.metadata)}")

    # Load model for querying
    print("\nLoading embedding model...")
    indexer.load_model()

    # Test query
    query = "nothing anyone could do except to get a tenacious grip on anything that was"
    print(f"\nQuerying: '{query}'")

    # Embed query
    query_embedding = indexer.embed_texts([query], show_progress=False)

    # Search
    k = 3
    distances, indices = indexer.index.search(query_embedding, k)

    print(f"\nTop {k} results:")
    for i, (distance, idx) in enumerate(zip(distances[0], indices[0]), 1):
        metadata = indexer.metadata[idx]
        print(f"\n{i}. Score: {distance:.4f}")
        print(f"   ID: {idx}")
        print(f"   EN: {metadata['src_text'][:100]}")
        print(f"   IT: {metadata['tgt_text'][:100]}")
        print(f"   Part: {metadata['part']}")


if __name__ == "__main__":
    try:
        test_index_load_and_search()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)