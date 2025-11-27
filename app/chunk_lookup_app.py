#!/usr/bin/env python3
"""
Draft application to lookup aligned chunks from Melancolia della Resistenza.

Given a text excerpt, finds the chunk_id and retrieves the corresponding
aligned text from the validation results.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List


class ChunkLookupApp:
    def __init__(self, chunks_file: str, alignments_file: str):
        """
        Initialize the lookup app.

        Args:
            chunks_file: Path to melancolia_della_resistenza.jsonl
            alignments_file: Path to alignment_results.validated.jsonl
        """
        self.chunks_file = Path(chunks_file)
        self.alignments_file = Path(alignments_file)

        # Load chunks into memory (assumes file is not too large)
        self.chunks = self._load_chunks()

    def _load_chunks(self) -> List[Dict[str, Any]]:
        """Load all chunks from the JSONL file."""
        chunks = []
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
        return chunks

    def find_chunk_by_text(self, text_excerpt: str) -> Optional[Dict[str, Any]]:
        """
        Find a chunk by searching for the text excerpt.

        Args:
            text_excerpt: Text excerpt to search for

        Returns:
            Chunk dict if found, None otherwise
        """
        # Normalize for comparison
        excerpt_normalized = text_excerpt.strip().lower()

        for chunk in self.chunks:
            if excerpt_normalized in chunk['text'].lower():
                return chunk

        return None

    def find_alignment_by_chunk_id(
        self,
        chunk_id: int,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find alignment result by chunk_id in either src_chunks or tgt_chunks.

        Args:
            chunk_id: The chunk ID to search for
            language: 'en' for source chunks, 'it' for target chunks

        Returns:
            Alignment dict if found with validation_success=true, otherwise
            the first alignment with chunk_id < provided chunk_id with
            validation_success=true
        """
        field_to_search = 'src_chunks' if language == 'en' else 'tgt_chunks'

        # First pass: look for exact chunk_id with validation_success
        exact_match = None
        fallback_candidates = []

        with open(self.alignments_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                alignment = json.loads(line)

                # Check if validation_success is true
                validation_success = alignment.get('validation', {}).get('validation_success', False)

                # Search in the appropriate chunks field
                chunks = alignment.get(field_to_search, [])

                for chunk in chunks:
                    if chunk['chunk_id'] == chunk_id:
                        if validation_success:
                            return alignment
                        else:
                            exact_match = alignment  # Keep track but don't return yet
                    elif chunk['chunk_id'] < chunk_id and validation_success:
                        # Potential fallback candidate
                        fallback_candidates.append({
                            'chunk_id': chunk['chunk_id'],
                            'alignment': alignment
                        })

        # If exact match exists but validation_success was false,
        # find the largest chunk_id < provided chunk_id with validation_success
        if exact_match or not exact_match:
            if fallback_candidates:
                # Sort by chunk_id descending and get the first (largest chunk_id < target)
                fallback_candidates.sort(key=lambda x: x['chunk_id'], reverse=True)
                return fallback_candidates[0]['alignment']

        return None

    def lookup(self, text_excerpt: str) -> Optional[Dict[str, Any]]:
        """
        Main lookup function.

        Args:
            text_excerpt: User-provided text excerpt

        Returns:
            Dict with src_text, tgt_text, and metadata if found, None otherwise
        """
        # Step 1: Find chunk by text
        chunk = self.find_chunk_by_text(text_excerpt)

        if not chunk:
            return {
                'error': 'Text excerpt not found in chunks',
                'excerpt': text_excerpt
            }

        chunk_id = chunk['chunk_id']
        language = chunk['language']

        # Step 2: Find alignment
        alignment = self.find_alignment_by_chunk_id(chunk_id, language)

        if not alignment:
            return {
                'error': 'No valid alignment found',
                'chunk_id': chunk_id,
                'language': language,
                'chunk_text': chunk['text']
            }

        # Step 3: Return result
        return {
            'found': True,
            'query_chunk_id': chunk_id,
            'query_language': language,
            'query_text': chunk['text'],
            'src_text': alignment['src_text'],
            'tgt_text': alignment['tgt_text'],
            'alignment_type': alignment.get('alignment_type'),
            'confidence': alignment.get('validation', {}).get('confidence'),
            'part': alignment.get('part'),
            'src_chunks': alignment.get('src_chunks'),
            'tgt_chunks': alignment.get('tgt_chunks')
        }


def main():
    """Interactive CLI for the chunk lookup app."""
    import sys

    # Default paths (relative to app directory)
    chunks_file = '../data/melancolia_della_resistenza.jsonl'
    alignments_file = '../data/alignment_results.validated.jsonl'

    print("Initializing Chunk Lookup App...")
    app = ChunkLookupApp(chunks_file, alignments_file)
    print(f"Loaded {len(app.chunks)} chunks")
    print()

    while True:
        print("=" * 80)
        text_excerpt = input("Enter text excerpt (or 'quit' to exit): ").strip()

        if text_excerpt.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break

        if not text_excerpt:
            print("Please enter a text excerpt.")
            continue

        print("\nSearching...")
        result = app.lookup(text_excerpt)

        print("\n" + "=" * 80)
        print("RESULT:")
        print("=" * 80)

        if result.get('error'):
            print(f"❌ Error: {result['error']}")
            if 'chunk_text' in result:
                print(f"Chunk ID: {result['chunk_id']}")
                print(f"Language: {result['language']}")
                print(f"Chunk text: {result['chunk_text']}")
        else:
            print(f"✓ Found alignment!")
            print(f"\nQuery Chunk ID: {result['query_chunk_id']}")
            print(f"Query Language: {result['query_language']}")
            print(f"Query Text: {result['query_text']}")
            print(f"\nAlignment Type: {result['alignment_type']}")
            print(f"Confidence: {result['confidence']}")
            print(f"Part: {result['part']}")
            print(f"\n--- SOURCE (EN) ---")
            print(result['src_text'])
            print(f"\n--- TARGET (IT) ---")
            print(result['tgt_text'])
            print(f"\n--- SOURCE CHUNKS ---")
            for chunk in result['src_chunks']:
                print(f"  [{chunk['chunk_id']}] {chunk['text']}")
            print(f"\n--- TARGET CHUNKS ---")
            for chunk in result['tgt_chunks']:
                print(f"  [{chunk['chunk_id']}] {chunk['text']}")

        print()


if __name__ == '__main__':
    main()