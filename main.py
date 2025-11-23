import os, sys
import json
import gc
from typing import List, Dict, Tuple
from collections import defaultdict

from config import Config
from bertalign import Bertalign
from bertalign.utils import load_jsonl


def extract_alignments_with_metadata(
    aligner: Bertalign,
    src_data: List[Dict],
    tgt_data: List[Dict],
    part: str
) -> List[Dict]:
    """
    Extract alignments from Bertalign result with full metadata preserved.

    Args:
        aligner: Bertalign instance with alignment results
        src_data: Original source data with metadata
        tgt_data: Original target data with metadata
        part: Part identifier

    Returns:
        List of dictionaries with aligned chunks and their metadata
    """
    alignments = []

    for bead in aligner.result:
        src_indices = bead[0]  # List of source line indices
        tgt_indices = bead[1]  # List of target line indices

        # Get the actual text
        src_text = aligner._get_line(src_indices, aligner.src_sents)
        tgt_text = aligner._get_line(tgt_indices, aligner.tgt_sents)

        # Collect metadata for source chunks
        src_chunks = []
        for idx in src_indices:
            chunk_meta = src_data[idx].copy()
            src_chunks.append(chunk_meta)

        # Collect metadata for target chunks
        tgt_chunks = []
        for idx in tgt_indices:
            chunk_meta = tgt_data[idx].copy()
            tgt_chunks.append(chunk_meta)

        alignment = {
            'part': part,
            'src_indices': list(src_indices),
            'tgt_indices': list(tgt_indices),
            'src_text': src_text,
            'tgt_text': tgt_text,
            'src_chunks': src_chunks,
            'tgt_chunks': tgt_chunks,
            'alignment_type': f"{len(src_indices)}-{len(tgt_indices)}"
        }

        alignments.append(alignment)

    return alignments


def save_alignments(alignments: List[Dict], output_path: str):
    """Save alignments to JSONL file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for alignment in alignments:
            f.write(json.dumps(alignment, ensure_ascii=False) + '\n')
    print(f"Saved {len(alignments)} total alignments to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_file.jsonl> [output_file.jsonl]")
        sys.exit(1)

    input_filename = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else "alignment_results.jsonl"

    input_path = os.path.join(Config.ROOT, "data", input_filename)
    output_path = os.path.join(Config.ROOT, "data", output_filename)

    # Load data
    print(f"Loading data from {input_path}...")
    data = load_jsonl(input_path)
    print(f"Loaded {len(data)} total chunks")

    # Group by part and language
    by_part = defaultdict(lambda: {'en': [], 'it': []})
    for item in data:
        part = item.get('part', '001')
        lang = item.get('language', 'en')
        by_part[part][lang].append(item)

    parts = sorted(by_part.keys())
    print(f"\nFound {len(parts)} parts: {parts}")

    all_alignments = []

    # Process each part
    for part in parts:
        src_data = by_part[part]['en']
        tgt_data = by_part[part]['it']

        if not src_data or not tgt_data:
            print(f"\nSkipping part {part}: missing data (en={len(src_data)}, it={len(tgt_data)})")
            continue

        print(f"\n{'='*60}")
        print(f"Processing part {part}")
        print(f"{'='*60}")
        print(f"  EN chunks: {len(src_data)}")
        print(f"  IT chunks: {len(tgt_data)}")

        # Extract texts
        src_texts = [item["text"] for item in src_data]
        tgt_texts = [item["text"] for item in tgt_data]

        src_str = "\n".join(src_texts)
        tgt_str = "\n".join(tgt_texts)

        print(f"  EN chars: {len(src_str)}")
        print(f"  IT chars: {len(tgt_str)}")

        # Run alignment
        aligner = Bertalign(
            src_str, tgt_str,
            max_align=2,         # Max chunks that can be combined
            min_win_size=1,      # Minimum window size for first pass
            percent=0.15,        # 15% of text length for window
            win=10,               # Strict monotonicity window
            top_k=10,            # Consider more candidates
            is_split=True        # Preserves chunk boundaries
        )

        aligner.align_sents()

        print(f"  Alignments found: {len(aligner.result)}")

        # Extract alignments with metadata
        part_alignments = extract_alignments_with_metadata(aligner, src_data, tgt_data, part)
        all_alignments.extend(part_alignments)

        # Print alignment statistics for this part
        alignment_types = {}
        for alignment in part_alignments:
            atype = alignment['alignment_type']
            alignment_types[atype] = alignment_types.get(atype, 0) + 1

        print(f"  Alignment types: {dict(sorted(alignment_types.items()))}")

        # Clean up aligner to free memory
        del aligner
        gc.collect()

    # Print overall statistics
    print(f"\n{'='*60}")
    print(f"OVERALL STATISTICS")
    print(f"{'='*60}")
    print(f"Total alignments: {len(all_alignments)}")

    overall_types = {}
    by_part_count = defaultdict(int)
    for alignment in all_alignments:
        atype = alignment['alignment_type']
        overall_types[atype] = overall_types.get(atype, 0) + 1
        by_part_count[alignment['part']] += 1

    print(f"\nAlignment type distribution:")
    for atype, count in sorted(overall_types.items()):
        print(f"  {atype}: {count}")

    print(f"\nAlignments by part:")
    for part, count in sorted(by_part_count.items()):
        print(f"  Part {part}: {count}")

    # Save results
    print()
    save_alignments(all_alignments, output_path)

    # Print examples
    print(f"\nFirst 3 alignments:")
    for i, alignment in enumerate(all_alignments[:3]):
        print(f"\n--- Alignment {i+1} (Part {alignment['part']}, {alignment['alignment_type']}) ---")
        print(f"EN [{alignment['src_indices']}]: {alignment['src_text'][:80]}...")
        print(f"IT [{alignment['tgt_indices']}]: {alignment['tgt_text'][:80]}...")


if __name__ == "__main__":
    main()
