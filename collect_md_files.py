#!/usr/bin/env python3
"""
Collect all markdown files from melancolia_della_resistenza directory structure
and create a JSONL file with aligned text pairs.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

from bertalign import Bertalign


def parse_filename(filename: str) -> Dict[str, str]:
    """
    Parse filename to extract language, part, and page.
    Expected format: {title}_{language}-{part}_page_{page}.md
    Example: melancolia_della_resistenza_it-001_page_003.md
    """
    # Pattern: anything_{language}-{part}_page_{page}.md
    pattern = r'_([a-z]{2})-(\d{3})_page_(\d{3})\.md$'
    match = re.search(pattern, filename)

    if match:
        return {
            'language': match.group(1),
            'part': match.group(2),
            'page': match.group(3)
        }
    else:
        raise ValueError(f"Could not parse filename: {filename}")


def collect_md_files(base_dir: Path) -> List[Dict]:
    """
    Collect all markdown files from the directory structure.
    Each line in each markdown file becomes a separate entry.
    """
    entries = []
    chunk_id = 0

    # Find all .md files recursively
    md_files = sorted(base_dir.rglob("*.md"))

    for md_file in md_files:
        try:
            # Parse filename to get metadata
            metadata = parse_filename(md_file.name)

            # Read file content line by line
            lines = md_file.read_text(encoding='utf-8').splitlines()

            # Create an entry for each non-empty line
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    continue

                entry = {
                    'chunk_id': chunk_id,
                    'text': line,
                    'language': metadata['language'],
                    'part': metadata['part'],
                    'page': metadata['page']
                }

                entries.append(entry)
                chunk_id += 1

        except Exception as e:
            print(f"Error processing {md_file}: {e}")
            continue

    return entries


def main():
    # BERT aligner configuration for this experiment
    bert_config = {
        "max_align": 2,        # Max chunks that can be combined
        "min_win_size": 1,     # Minimum window size for first pass
        "percent": 0.15,       # 15% of text length for window
        "win": 10,             # Strict monotonicity window
        "top_k": 10,           # Consider more candidates
        "is_split": True       # Preserves chunk boundaries
    }

    # Generate experiment ID based on config and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_id = f"ma{bert_config['max_align']}_p{int(bert_config['percent']*100)}_w{bert_config['win']}_k{bert_config['top_k']}"
    experiment_id = f"exp_{config_id}_{timestamp}"

    # Define paths
    base_dir = Path("/home/rp/data/melancolia_della_resistenza/chunking4/melancolia_della_resistenza")
    experiments_dir = Path("/home/rp/data/melancolia_della_resistenza/chunking4/experiments")
    output_dir = experiments_dir / experiment_id
    output_file = output_dir / "melanconia_della_resistenza_aligned.jsonl"
    metadata_file = output_dir / "metadata.json"

    print(f"Experiment ID: {experiment_id}")
    print(f"Collecting markdown files from: {base_dir}")

    # Collect all entries
    all_entries = collect_md_files(base_dir)
    print(f"Found {len(all_entries)} total lines from markdown files")

    # Separate by language and part
    parts = set(entry['part'] for entry in all_entries)

    output_dir.mkdir(parents=True, exist_ok=True)
    all_alignments = []
    alignment_stats = {}

    # Process each part separately
    for part in sorted(parts):
        print(f"\nProcessing part {part}...")

        # Get source (English) and target (Italian) texts for this part
        src_entries = [e for e in all_entries if e['language'] == 'en' and e['part'] == part]
        tgt_entries = [e for e in all_entries if e['language'] == 'it' and e['part'] == part]

        src_texts = [e['text'] for e in src_entries]
        tgt_texts = [e['text'] for e in tgt_entries]

        print(f"  Source (EN): {len(src_texts)} lines")
        print(f"  Target (IT): {len(tgt_texts)} lines")

        # Join texts for alignment
        src = "\n".join(src_texts)
        tgt = "\n".join(tgt_texts)

        # Run BERT alignment
        print(f"  Running BERT alignment...")
        aligner = Bertalign(
            src,
            tgt,
            max_align=bert_config['max_align'],
            min_win_size=bert_config['min_win_size'],
            percent=bert_config['percent'],
            win=bert_config['win'],
            top_k=bert_config['top_k'],
            is_split=bert_config['is_split']
        )
        aligner.align_sents()

        # Get aligned sentences from result beads
        aligned_pairs = []
        for bead in aligner.result:
            src_bead, tgt_bead = bead
            # Extract source sentence(s)
            if len(src_bead) > 0:
                src_sent = ' '.join(aligner.src_sents[src_bead[0]:src_bead[-1]+1])
            else:
                src_sent = ''
            # Extract target sentence(s)
            if len(tgt_bead) > 0:
                tgt_sent = ' '.join(aligner.tgt_sents[tgt_bead[0]:tgt_bead[-1]+1])
            else:
                tgt_sent = ''
            aligned_pairs.append((src_sent, tgt_sent))

        print(f"  Aligned: {len(aligned_pairs)} sentence pairs")
        alignment_stats[part] = {
            'src_lines': len(src_texts),
            'tgt_lines': len(tgt_texts),
            'aligned_pairs': len(aligned_pairs)
        }

        # Create alignment entries
        for i, (src_sent, tgt_sent) in enumerate(aligned_pairs):
            alignment_entry = {
                'alignment_id': len(all_alignments),
                'part': part,
                'pair_id_in_part': i,
                'src': src_sent,
                'tgt': tgt_sent,
                'src_lang': 'en',
                'tgt_lang': 'it'
            }
            all_alignments.append(alignment_entry)

    # Write alignments to JSONL
    print(f"\nWriting {len(all_alignments)} aligned pairs to {output_file}")
    with output_file.open('w', encoding='utf-8') as f:
        for entry in all_alignments:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"Wrote output to: {output_file}")

    # Print statistics
    print(f"\nAlignment Statistics:")
    total_pairs = 0
    for part, stats in sorted(alignment_stats.items()):
        print(f"  Part {part}: {stats['src_lines']} EN lines, {stats['tgt_lines']} IT lines → {stats['aligned_pairs']} pairs")
        total_pairs += stats['aligned_pairs']
    print(f"  Total: {total_pairs} aligned pairs")

    # Save metadata with BERT aligner configuration
    metadata = {
        "experiment_id": experiment_id,
        "timestamp": timestamp,
        "data_file": output_file.name,
        "source_directory": str(base_dir),
        "total_aligned_pairs": len(all_alignments),
        "alignment_statistics": alignment_stats,
        "bert_aligner_config": bert_config
    }

    with metadata_file.open('w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\nWrote metadata to: {metadata_file}")
    print(f"Experiment directory: {output_dir}")


if __name__ == "__main__":
    main()