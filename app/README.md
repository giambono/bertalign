# Melancolia della Resistenza - Parallel Viewers

This directory contains multiple applications for viewing and searching aligned English-Italian texts from "Melancolia della Resistenza" by László Krasznahorkai.

## Applications

### 1. PDF Parallel Viewer (RECOMMENDED)
**File**: `pdf_parallel_viewer.py`

Displays the actual English and Italian PDF books side by side with synchronized navigation.

**Features**:
- Real PDF viewing using PDF.js
- Side-by-side English/Italian books
- Search text to automatically sync to correct pages
- Manual page navigation (synchronized or independent)
- Toggle sync scroll on/off
- Shows aligned text snippets when searching
- Navigate with arrow buttons or page numbers

**Usage**:
```bash
cd app
python pdf_parallel_viewer.py
# Open browser to http://localhost:5001
```

**Try searching for**:
- "AN EMERGENCY" → jumps to EN page 1, IT page 1
- "PASSENGER TRAIN" → jumps to corresponding pages
- Any text from either language

---

### 2. Web Text Parallel Viewer
**File**: `web_parallel_viewer.py`

Web-based viewer showing aligned text passages (not PDFs).

**Features**:
- Displays all validated alignments in scrollable panels
- Synchronized scrolling between English and Italian
- Search and highlight functionality
- Shows confidence scores and alignment types
- Part headers to organize content

**Usage**:
```bash
cd app
python web_parallel_viewer.py
# Open browser to http://localhost:5000
```

---

### 3. Tkinter GUI Viewer
**File**: `parallel_text_viewer.py`

Desktop GUI application using Tkinter (no browser needed).

**Features**:
- Native desktop application
- Side-by-side text panels
- Synchronized scrolling
- Search and highlight
- Works offline without web browser

**Usage**:
```bash
cd app
python parallel_text_viewer.py
```

---

### 4. CLI Chunk Lookup
**File**: `chunk_lookup_app.py`

Command-line interface for text lookup and alignment retrieval.

**Features**:
- Interactive CLI
- Search by text excerpt
- Returns aligned translations
- Shows chunk IDs, confidence scores
- Displays source and target chunks

**Usage**:
```bash
cd app
python chunk_lookup_app.py

# Interactive prompts:
Enter text excerpt: AN EMERGENCY
# Returns full alignment information
```

---

## Data Requirements

All applications require these data files in the `../data/` directory:

- `melancolia_della_resistenza.jsonl` - All text chunks with metadata
- `alignment_results.validated.jsonl` - Validated alignments between EN/IT
- `en.pdf` - English PDF book (for PDF viewer only)
- `it.pdf` - Italian PDF book (for PDF viewer only)

## Dependencies

Install with `uv`:
```bash
uv pip install flask
```

For Tkinter (usually pre-installed with Python):
```bash
# On Ubuntu/Debian if needed:
sudo apt-get install python3-tk
```

## Test Scripts

- `test_chunk_lookup.py` - Test English text lookups
- `test_italian_lookup.py` - Test Italian text lookups

Run tests:
```bash
python test_chunk_lookup.py
python test_italian_lookup.py
```

## Data Format

### Chunks (melancolia_della_resistenza.jsonl)
```json
{
  "chunk_id": 0,
  "text": "AN EMERGENCY",
  "language": "en",
  "part": "001",
  "page": "001"
}
```

### Alignments (alignment_results.validated.jsonl)
```json
{
  "part": "001",
  "src_text": "AN EMERGENCY",
  "tgt_text": "CONDIZIONI STRAORDINARIE",
  "src_chunks": [{"chunk_id": 0, ...}],
  "tgt_chunks": [{"chunk_id": 9969, ...}],
  "alignment_type": "1-1",
  "validation": {
    "is_valid_alignment": true,
    "confidence": 0.85,
    "validation_success": true
  }
}
```

## How Search Works

1. **Text input**: User enters English or Italian text excerpt
2. **Chunk lookup**: Finds matching chunk in chunks file
3. **Language detection**: Determines if input is EN or IT based on chunk data
4. **Alignment search**:
   - EN text → searches in `src_chunks` field
   - IT text → searches in `tgt_chunks` field
5. **Result display**:
   - PDF viewer → navigates to corresponding pages
   - Text viewers → scrolls to and highlights the alignment
   - CLI → prints alignment details

## Comparison

| Feature | PDF Viewer | Web Text | Tkinter | CLI |
|---------|-----------|----------|---------|-----|
| PDF Display | ✓ | ✗ | ✗ | ✗ |
| Text Display | ✗ | ✓ | ✓ | ✓ |
| Browser Required | ✓ | ✓ | ✗ | ✗ |
| Search & Sync | ✓ | ✓ | ✓ | ✓ |
| Synchronized Scroll | ✓ | ✓ | ✓ | ✗ |
| Page Navigation | ✓ | ✗ | ✗ | ✗ |
| Offline Use | ✗ | ✗ | ✓ | ✓ |
| Visual Formatting | ✓ | Limited | Limited | None |

## Recommended Use Cases

- **Reading the books**: Use **PDF Viewer** for authentic reading experience
- **Analyzing alignments**: Use **Web Text Viewer** to see all alignments at once
- **Offline work**: Use **Tkinter GUI** when no browser available
- **Scripting/automation**: Use **CLI** for programmatic access

## Notes

- All viewers use validated alignments only (`validation_success: true`)
- Search is case-insensitive and supports partial matches
- Page numbers in chunks are 0-padded strings ("001", "002", etc.)
- PDF viewer runs on port 5001, web text viewer on port 5000