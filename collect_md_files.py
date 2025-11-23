#!/usr/bin/env python3
"""
Collect all markdown files from melancolia_della_resistenza directory structure
and create a JSONL file with metadata.
"""

import json
import re
from pathlib import Path
from typing import Dict, List


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
    # Define paths
    base_dir = Path("/home/rp/data/melancolia_della_resistenza/chunking4/melancolia_della_resistenza")
    output_file = Path("/home/rp/data/melancolia_della_resistenza/chunking4/melanconia_della_resistenza.jsonl")

    print(f"Collecting markdown files from: {base_dir}")

    # Collect all entries
    entries = collect_md_files(base_dir)

    print(f"Found {len(entries)} total lines from markdown files")

    # Write to JSONL
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"Wrote output to: {output_file}")

    # Print some statistics
    languages = {}
    parts = {}
    for entry in entries:
        lang = entry['language']
        part = entry['part']
        languages[lang] = languages.get(lang, 0) + 1
        parts[part] = parts.get(part, 0) + 1

    print(f"\nStatistics:")
    print(f"Languages: {dict(sorted(languages.items()))}")
    print(f"Parts: {dict(sorted(parts.items()))}")


if __name__ == "__main__":
    main()