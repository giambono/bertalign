# Chunk Lookup Application

## Overview

This application allows you to search for text excerpts from the Melancolia della Resistenza corpus and retrieve the corresponding aligned translations.

## Files

- `chunk_lookup_app.py` - Main application with CLI interface
- `test_chunk_lookup.py` - Test script for English lookups
- `test_italian_lookup.py` - Test script for Italian lookups

## Usage

### Interactive CLI

Run the application in interactive mode:

```bash
python chunk_lookup_app.py
```

Then enter text excerpts when prompted. The app will:
1. Find the chunk_id and language from the input text
2. Search for aligned translations in the validation results
3. Display the source and target texts with confidence scores

### Programmatic Usage

```python
from chunk_lookup_app import ChunkLookupApp

# Initialize
chunks_file = '/path/to/melancolia_della_resistenza.jsonl'
alignments_file = '/path/to/alignment_results.validated.jsonl'
app = ChunkLookupApp(chunks_file, alignments_file)

# Lookup a text excerpt
result = app.lookup("AN EMERGENCY")

if result.get('found'):
    print(f"Source: {result['src_text']}")
    print(f"Target: {result['tgt_text']}")
else:
    print(f"Error: {result['error']}")
```

## How It Works

1. **Text Search**: The app searches for the input text excerpt in the chunks file
2. **Language Detection**: Determines if the input is English (en) or Italian (it)
3. **Alignment Lookup**: Searches the validation results:
   - For English text: searches in `src_chunks` field
   - For Italian text: searches in `tgt_chunks` field
4. **Validation**: Returns the alignment if `validation_success` is true
5. **Fallback**: If the exact chunk has `validation_success` false, finds the closest previous chunk with validation success

## Example Output

```
Enter text excerpt: Introduction

================================================================================
RESULT:
================================================================================
✓ Found alignment!

Query Chunk ID: 1
Query Language: en
Query Text: Introduction

Alignment Type: 1-1
Confidence: 0.95
Part: 001

--- SOURCE (EN) ---
Introduction

--- TARGET (IT) ---
Introduzione

--- SOURCE CHUNKS ---
  [1] Introduction

--- TARGET CHUNKS ---
  [9970] Introduzione
```

## Testing

Run the test scripts to verify functionality:

```bash
# Test English lookups
python test_chunk_lookup.py

# Test Italian lookups
python test_italian_lookup.py
```

## Data Format

### Input: melancolia_della_resistenza.jsonl
```json
{"chunk_id": 0, "text": "AN EMERGENCY", "language": "en", "part": "001", "page": "001"}
```

### Input: alignment_results.validated.jsonl
```json
{
  "part": "001",
  "src_text": "AN EMERGENCY",
  "tgt_text": "CONDIZIONI STRAORDINARIE",
  "src_chunks": [{"chunk_id": 0, "text": "...", "language": "en", ...}],
  "tgt_chunks": [{"chunk_id": 9969, "text": "...", "language": "it", ...}],
  "alignment_type": "1-1",
  "validation": {
    "is_valid_alignment": true,
    "confidence": 0.85,
    "validation_success": true
  }
}
```