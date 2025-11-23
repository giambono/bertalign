import os, sys
import json
import gc
import numpy as np
import psutil
import torch
from typing import List, Dict
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from bertalign import Bertalign
from bertalign.utils import load_jsonl


def get_memory_usage():
    """Get current memory usage in GB."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / (1024 ** 3)  # Convert bytes to GB


def aggressive_cleanup():
    """Perform aggressive memory cleanup."""
    # Force garbage collection multiple times
    for _ in range(3):
        gc.collect()

    # Clear PyTorch cache if using GPU
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

    # Additional garbage collection
    gc.collect()


def json_serializable(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


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
            f.write(json.dumps(alignment, ensure_ascii=False, default=json_serializable) + '\n')
    print(f"Saved {len(alignments)} total alignments to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <absolute_input_path.jsonl>")
        sys.exit(1)

    input_path = sys.argv[1]  # Absolute path

    # BERT aligner configuration
    bert_config = {
        "max_align": 4,        # Max chunks that can be combined
        "min_win_size": 1,     # Minimum window size for first pass
        "percent": 0.15,       # 15% of text length for window
        "win": 20,             # Strict monotonicity window
        "top_k": 10,           # Consider more candidates
        "is_split": True       # Preserves chunk boundaries
    }

    # Generate experiment ID based on config and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_id = f"ma{bert_config['max_align']}_p{int(bert_config['percent']*100)}_w{bert_config['win']}_k{bert_config['top_k']}"
    experiment_id = f"exp_{config_id}_{timestamp}"

    # Create experiments folder in input directory
    input_dir = Path(input_path).parent
    experiments_dir = input_dir / "experiments"
    output_dir = experiments_dir / experiment_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define output paths
    output_path = output_dir / "alignment_results.jsonl"
    metadata_path = output_dir / "metadata.json"

    print(f"Experiment ID: {experiment_id}")
    print(f"Output directory: {output_dir}")

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
    print(f"\nFound {len(parts)} parts: {parts[:10]}{'...' if len(parts) > 10 else ''}")

    # Print initial memory usage
    initial_memory = get_memory_usage()
    print(f"Initial memory usage: {initial_memory:.2f} GB")

    all_alignments = []

    # Process each part
    for part_idx, part in enumerate(parts, 1):
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
            max_align=bert_config['max_align'],
            min_win_size=bert_config['min_win_size'],
            percent=bert_config['percent'],
            win=bert_config['win'],
            top_k=bert_config['top_k'],
            is_split=bert_config['is_split']
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

        # Memory before cleanup
        mem_before_cleanup = get_memory_usage()

        # Explicitly delete large arrays before deleting aligner
        if hasattr(aligner, 'src_vecs'):
            del aligner.src_vecs
        if hasattr(aligner, 'tgt_vecs'):
            del aligner.tgt_vecs
        if hasattr(aligner, 'src_lens'):
            del aligner.src_lens
        if hasattr(aligner, 'tgt_lens'):
            del aligner.tgt_lens

        # Clean up aligner to free memory
        del aligner

        # Perform aggressive memory cleanup
        aggressive_cleanup()

        # Memory after cleanup
        mem_after_cleanup = get_memory_usage()
        print(f"  Memory: {mem_before_cleanup:.2f} GB -> {mem_after_cleanup:.2f} GB (freed {mem_before_cleanup - mem_after_cleanup:.2f} GB)")
        print(f"  Progress: {part_idx}/{len(parts)} parts processed")

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
    save_alignments(all_alignments, str(output_path))

    # Build metadata
    alignment_stats = {}
    for part, count in sorted(by_part_count.items()):
        alignment_stats[part] = {
            'total_alignments': count,
            'alignment_types': {}
        }

    for alignment in all_alignments:
        part = alignment['part']
        atype = alignment['alignment_type']
        if 'alignment_types' not in alignment_stats[part]:
            alignment_stats[part]['alignment_types'] = {}
        alignment_stats[part]['alignment_types'][atype] = alignment_stats[part]['alignment_types'].get(atype, 0) + 1

    metadata = {
        "experiment_id": experiment_id,
        "timestamp": timestamp,
        "input_file": input_path,
        "output_file": str(output_path),
        "total_alignments": len(all_alignments),
        "bert_aligner_config": bert_config,
        "alignment_statistics": alignment_stats,
        "overall_alignment_types": dict(sorted(overall_types.items()))
    }

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Saved metadata to {metadata_path}")
    print(f"Experiment directory: {output_dir}")

    # Print examples
    print(f"\nFirst 3 alignments:")
    for i, alignment in enumerate(all_alignments[:3]):
        print(f"\n--- Alignment {i+1} (Part {alignment['part']}, {alignment['alignment_type']}) ---")
        print(f"EN [{alignment['src_indices']}]: {alignment['src_text'][:80]}...")
        print(f"IT [{alignment['tgt_indices']}]: {alignment['tgt_text'][:80]}...")


if __name__ == "__main__":
    main()
