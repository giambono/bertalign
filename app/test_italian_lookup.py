#!/usr/bin/env python3
"""Test Italian text lookup."""

from chunk_lookup_app import ChunkLookupApp


def test_italian():
    """Test the chunk lookup app with Italian queries."""
    chunks_file = '/home/rp/data/melancolia_della_resistenza/chunking4/melancolia_della_resistenza.jsonl'
    alignments_file = '/home/rp/data/melancolia_della_resistenza/chunking4/experiments/exp_ma4_p15_w20_k10_20251123_152528/alignment_results.validated.jsonl'

    print("Initializing app...")
    app = ChunkLookupApp(chunks_file, alignments_file)
    print(f"Loaded {len(app.chunks)} chunks\n")

    # Test with Italian text
    print("=" * 80)
    print("TEST: Italian excerpt - CONDIZIONI STRAORDINARIE")
    print("=" * 80)
    result = app.lookup("CONDIZIONI STRAORDINARIE")
    if result.get('found'):
        print(f"✓ Found! Chunk ID: {result['query_chunk_id']}")
        print(f"  Language: {result['query_language']}")
        print(f"  EN: {result['src_text']}")
        print(f"  IT: {result['tgt_text']}")
    else:
        print(f"✗ Error: {result.get('error')}")

    print("\n" + "=" * 80)
    print("TEST: Italian excerpt - Introduzione")
    print("=" * 80)
    result = app.lookup("Introduzione")
    if result.get('found'):
        print(f"✓ Found! Chunk ID: {result['query_chunk_id']}")
        print(f"  Language: {result['query_language']}")
        print(f"  EN: {result['src_text']}")
        print(f"  IT: {result['tgt_text']}")
    else:
        print(f"✗ Error: {result.get('error')}")


if __name__ == '__main__':
    test_italian()