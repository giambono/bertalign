#!/usr/bin/env python3
"""Test script for chunk_lookup_app."""

from chunk_lookup_app import ChunkLookupApp


def test_app():
    """Test the chunk lookup app with sample queries."""
    chunks_file = '/home/rp/data/melancolia_della_resistenza/chunking4/melancolia_della_resistenza.jsonl'
    alignments_file = '/home/rp/data/melancolia_della_resistenza/chunking4/experiments/exp_ma4_p15_w20_k10_20251123_152528/alignment_results.validated.jsonl'

    print("Initializing app...")
    app = ChunkLookupApp(chunks_file, alignments_file)
    print(f"Loaded {len(app.chunks)} chunks\n")

    # Test 1: English text (from the data we saw)
    print("=" * 80)
    print("TEST 1: English excerpt")
    print("=" * 80)
    result1 = app.lookup("AN EMERGENCY")
    if result1.get('found'):
        print(f"✓ Found! Chunk ID: {result1['query_chunk_id']}")
        print(f"  EN: {result1['src_text']}")
        print(f"  IT: {result1['tgt_text']}")
    else:
        print(f"✗ Error: {result1.get('error')}")

    print("\n" + "=" * 80)
    print("TEST 2: Another English excerpt")
    print("=" * 80)
    result2 = app.lookup("Introduction")
    if result2.get('found'):
        print(f"✓ Found! Chunk ID: {result2['query_chunk_id']}")
        print(f"  EN: {result2['src_text']}")
        print(f"  IT: {result2['tgt_text']}")
    else:
        print(f"✗ Error: {result2.get('error')}")

    print("\n" + "=" * 80)
    print("TEST 3: Partial text match")
    print("=" * 80)
    result3 = app.lookup("PASSENGER TRAIN")
    if result3.get('found'):
        print(f"✓ Found! Chunk ID: {result3['query_chunk_id']}")
        print(f"  EN: {result3['src_text']}")
        print(f"  IT: {result3['tgt_text']}")
    else:
        print(f"✗ Error: {result3.get('error')}")


if __name__ == '__main__':
    test_app()