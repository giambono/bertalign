import sys
import os
import json
from typing import List, Tuple

from config import Config
from bertalign import Bertalign
from bertalign.utils import load_jsonl
from transformers import AutoTokenizer


def decompose_text_with_overlap(
    text: str,
    num_tokens: int,
    overlap: int,
    tokenizer_name: str = "bert-base-multilingual-cased"
) -> List[str]:
    """
    Decompose a text into subtexts with overlapping tokens, ensuring words are not broken.

    Args:
        text: Text to decompose
        num_tokens: Number of tokens per chunk (approximate, will adjust to word boundaries)
        overlap: Number of overlapping tokens between consecutive chunks (approximate)
        tokenizer_name: Name of the tokenizer to use (default: BERT multilingual)

    Returns:
        List of text chunks with overlapping tokens, aligned to word boundaries
    """
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

    # Tokenize the text with offset mapping to track word boundaries
    encoding = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    tokens = encoding['input_ids']
    offset_mapping = encoding['offset_mapping']

    chunks = []
    step = num_tokens - overlap

    if step <= 0:
        raise ValueError("overlap must be less than num_tokens")

    def find_word_boundary(idx: int, direction: str = 'right') -> int:
        """Find the nearest word boundary from a given token index."""
        if idx >= len(offset_mapping):
            return len(offset_mapping) - 1
        if idx < 0:
            return 0

        # Get the character position for this token
        char_start, char_end = offset_mapping[idx]

        if direction == 'right':
            # Find the next space or end of text
            next_space = text.find(' ', char_end)
            if next_space == -1:
                next_space = len(text)

            # Find the token that starts at or after this space
            for i in range(idx, len(offset_mapping)):
                token_start, token_end = offset_mapping[i]
                if token_start >= next_space:
                    return i
            return len(offset_mapping)
        else:  # 'left'
            # Find the previous space
            prev_space = text.rfind(' ', 0, char_start)
            if prev_space == -1:
                return 0

            # Find the token that starts after this space
            for i in range(idx, -1, -1):
                token_start, token_end = offset_mapping[i]
                if token_end <= prev_space + 1:
                    return i + 1
            return 0

    # Create sliding windows aligned to word boundaries
    i = 0
    while i < len(tokens):
        # Determine chunk end (approximately num_tokens away)
        chunk_end = min(i + num_tokens, len(tokens))

        # Adjust to word boundary (don't split words)
        if chunk_end < len(tokens):
            chunk_end = find_word_boundary(chunk_end, direction='left')

        # Extract tokens for this chunk
        chunk_tokens = tokens[i:chunk_end]

        if len(chunk_tokens) == 0:
            break

        # Decode tokens back to text
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        chunks.append(chunk_text)

        # Move to next chunk with overlap
        if chunk_end >= len(tokens):
            break

        # Calculate next start position with overlap
        next_start = i + step
        if next_start >= len(tokens):
            break

        # Adjust next start to word boundary
        next_start = find_word_boundary(next_start, direction='right')

        # Ensure we're making progress
        if next_start <= i:
            next_start = chunk_end

        i = next_start

    return chunks


def main():
    jsonl_path = sys.argv[1]
    jsonl_path = os.path.join(Config.ROOT, jsonl_path)
    data = load_jsonl(jsonl_path)

    src = [r["text"] for r in data if r["language"] == "en" and r["part"] == "001"]
    tgt = [r["text"] for r in data if r["language"] == "it" and r["part"] == "001"]

    src = " ".join(src)
    tgt = " ".join(tgt)

    print("src:", src)
    print("\n" + "="*80 + "\n")

    # Example: decompose texts with overlapping tokens
    src_chunks = decompose_text_with_overlap(
        text=src,
        num_tokens=50,  # Each chunk will have 50 tokens
        overlap=10,     # 10 tokens overlap between consecutive chunks
        tokenizer_name="bert-base-multilingual-cased"
    )

    tgt_chunks = decompose_text_with_overlap(
        text=tgt,
        num_tokens=50,
        overlap=10,
        tokenizer_name="bert-base-multilingual-cased"
    )

    # Save chunks to JSONL files
    src_output_path = os.path.join(Config.ROOT, "data/src_chunks.jsonl")
    tgt_output_path = os.path.join(Config.ROOT, "data/tgt_chunks.jsonl")

    print(f"\nSaving source chunks to {src_output_path}")
    with open(src_output_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(src_chunks):
            entry = {
                "chunk_id": i,
                "text": chunk,
                "language": "en"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"Saving target chunks to {tgt_output_path}")
    with open(tgt_output_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(tgt_chunks):
            entry = {
                "chunk_id": i,
                "text": chunk,
                "language": "it"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"\nSaved {len(src_chunks)} source chunks and {len(tgt_chunks)} target chunks")

    # aligner = Bertalign(src, tgt)
    # aligner.align_sents()
    # aligner.print_sents()


if __name__ == "__main__":
    main()
