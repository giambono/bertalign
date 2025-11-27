#!/usr/bin/env python3
"""
Web-based Parallel Text Viewer for Melancolia della Resistenza
Displays aligned English and Italian texts side by side with synchronized scrolling.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify


class ParallelTextData:
    def __init__(self, chunks_file: str, alignments_file: str):
        """Initialize and load data."""
        self.chunks_file = Path(chunks_file)
        self.alignments_file = Path(alignments_file)

        print("Loading chunks...")
        self.chunks = self._load_chunks()
        print(f"Loaded {len(self.chunks)} chunks")

        print("Loading alignments...")
        self.alignments = self._load_alignments()
        print(f"Loaded {len(self.alignments)} validated alignments")

        # Create chunk index
        self.chunk_index = {chunk['chunk_id']: chunk for chunk in self.chunks}

    def _load_chunks(self) -> List[Dict[str, Any]]:
        """Load all chunks."""
        chunks = []
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
        return sorted(chunks, key=lambda x: x['chunk_id'])

    def _load_alignments(self) -> List[Dict[str, Any]]:
        """Load validated alignments."""
        alignments = []
        with open(self.alignments_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    alignment = json.loads(line)
                    if alignment.get('validation', {}).get('validation_success', False):
                        alignments.append(alignment)
        return alignments

    def search_text(self, query: str) -> Dict[str, Any]:
        """Search for text and return alignment info."""
        query = query.strip().lower()

        # Find chunk
        found_chunk = None
        for chunk in self.chunks:
            if query in chunk['text'].lower():
                found_chunk = chunk
                break

        if not found_chunk:
            return {'error': 'Text not found in chunks'}

        chunk_id = found_chunk['chunk_id']
        language = found_chunk['language']
        field_to_search = 'src_chunks' if language == 'en' else 'tgt_chunks'

        # Find alignment
        for idx, alignment in enumerate(self.alignments):
            chunks = alignment.get(field_to_search, [])
            for chunk in chunks:
                if chunk['chunk_id'] == chunk_id:
                    return {
                        'found': True,
                        'alignment_index': idx,
                        'chunk_id': chunk_id,
                        'language': language,
                        'src_text': alignment['src_text'],
                        'tgt_text': alignment['tgt_text'],
                        'part': alignment.get('part'),
                        'confidence': alignment.get('validation', {}).get('confidence'),
                        'alignment_type': alignment.get('alignment_type')
                    }

        return {'error': 'No validated alignment found'}

    def get_alignments(self) -> List[Dict[str, Any]]:
        """Get all alignments."""
        return self.alignments


# Initialize Flask app
app = Flask(__name__)
data_handler = None


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('parallel_viewer.html')


@app.route('/api/alignments')
def get_alignments():
    """Get all alignments."""
    return jsonify(data_handler.get_alignments())


@app.route('/api/search', methods=['POST'])
def search():
    """Search for text."""
    query = request.json.get('query', '')
    result = data_handler.search_text(query)
    return jsonify(result)


def create_html_template():
    """Create the HTML template file."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Melancolia della Resistenza - Parallel Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }

        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        h1 {
            color: #333;
            margin-bottom: 15px;
        }

        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }

        #searchInput {
            flex: 1;
            padding: 10px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 4px;
        }

        button {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }

        button:hover {
            background: #0056b3;
        }

        .clear-btn {
            background: #6c757d;
        }

        .clear-btn:hover {
            background: #545b62;
        }

        .status {
            padding: 10px;
            background: #e9ecef;
            border-radius: 4px;
            font-size: 14px;
            color: #495057;
        }

        .status.success {
            background: #d4edda;
            color: #155724;
        }

        .status.error {
            background: #f8d7da;
            color: #721c24;
        }

        .content-wrapper {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            height: calc(100vh - 250px);
        }

        .text-panel {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            background: #343a40;
            color: white;
            padding: 15px;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
        }

        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            font-size: 16px;
            line-height: 1.8;
        }

        .alignment-block {
            margin-bottom: 30px;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #dee2e6;
            border-radius: 4px;
            transition: all 0.3s;
        }

        .alignment-block.highlight {
            background: #fff3cd;
            border-left-color: #ffc107;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .alignment-block.search-match {
            background: #ffe5b4;
            border-left-color: #ff8c00;
        }

        .part-header {
            background: #007bff;
            color: white;
            padding: 10px;
            margin: 20px -20px;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
        }

        .highlight-text {
            background: yellow;
            padding: 2px 4px;
            border-radius: 2px;
        }

        /* Synchronized scrolling */
        .sync-scroll {
            scroll-behavior: smooth;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Melancolia della Resistenza - Parallel Text Viewer</h1>
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Enter text to search and sync...">
            <button onclick="searchAndSync()">Find & Sync</button>
            <button class="clear-btn" onclick="clearHighlights()">Clear</button>
        </div>
        <div id="status" class="status">Ready</div>
    </div>

    <div class="content-wrapper">
        <div class="text-panel">
            <div class="panel-header">ENGLISH</div>
            <div id="enContent" class="panel-content sync-scroll"></div>
        </div>
        <div class="text-panel">
            <div class="panel-header">ITALIANO</div>
            <div id="itContent" class="panel-content sync-scroll"></div>
        </div>
    </div>

    <script>
        let alignments = [];
        let currentPart = null;

        // Load alignments on page load
        window.addEventListener('load', async () => {
            setStatus('Loading alignments...', '');
            try {
                const response = await fetch('/api/alignments');
                alignments = await response.json();
                renderAlignments();
                setStatus(`Loaded ${alignments.length} aligned text pairs`, 'success');
            } catch (error) {
                setStatus('Error loading alignments: ' + error.message, 'error');
            }
        });

        function renderAlignments() {
            const enContent = document.getElementById('enContent');
            const itContent = document.getElementById('itContent');

            alignments.forEach((alignment, idx) => {
                // Add part headers if new part
                if (alignment.part !== currentPart) {
                    currentPart = alignment.part;
                    enContent.innerHTML += `<div class="part-header">PART ${alignment.part}</div>`;
                    itContent.innerHTML += `<div class="part-header">PARTE ${alignment.part}</div>`;
                }

                // Add alignment blocks
                enContent.innerHTML += `
                    <div class="alignment-block" id="en-${idx}" data-index="${idx}">
                        ${escapeHtml(alignment.src_text)}
                    </div>
                `;

                itContent.innerHTML += `
                    <div class="alignment-block" id="it-${idx}" data-index="${idx}">
                        ${escapeHtml(alignment.tgt_text)}
                    </div>
                `;
            });

            // Setup synchronized scrolling
            setupSyncScroll();
        }

        function setupSyncScroll() {
            const enPanel = document.getElementById('enContent');
            const itPanel = document.getElementById('itContent');

            let isScrolling = false;

            enPanel.addEventListener('scroll', () => {
                if (!isScrolling) {
                    isScrolling = true;
                    itPanel.scrollTop = enPanel.scrollTop;
                    setTimeout(() => isScrolling = false, 10);
                }
            });

            itPanel.addEventListener('scroll', () => {
                if (!isScrolling) {
                    isScrolling = true;
                    enPanel.scrollTop = itPanel.scrollTop;
                    setTimeout(() => isScrolling = false, 10);
                }
            });
        }

        async function searchAndSync() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) {
                setStatus('Please enter text to search', 'error');
                return;
            }

            setStatus('Searching...', '');

            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({query})
                });

                const result = await response.json();

                if (result.error) {
                    setStatus('Error: ' + result.error, 'error');
                    return;
                }

                // Clear previous highlights
                clearHighlights();

                // Highlight the found alignment
                const idx = result.alignment_index;
                const enBlock = document.getElementById(`en-${idx}`);
                const itBlock = document.getElementById(`it-${idx}`);

                if (enBlock && itBlock) {
                    enBlock.classList.add('highlight');
                    itBlock.classList.add('highlight');

                    // Highlight search term
                    if (result.language === 'en') {
                        highlightText(enBlock, query);
                    } else {
                        highlightText(itBlock, query);
                    }

                    // Scroll to position
                    enBlock.scrollIntoView({behavior: 'smooth', block: 'center'});

                    setStatus(
                        `Found! Chunk ${result.chunk_id} (${result.language}) - ` +
                        `Confidence: ${result.confidence?.toFixed(2) || 'N/A'} - ` +
                        `Type: ${result.alignment_type}`,
                        'success'
                    );
                }
            } catch (error) {
                setStatus('Error: ' + error.message, 'error');
            }
        }

        function highlightText(element, searchTerm) {
            const text = element.innerHTML;
            const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi');
            element.innerHTML = text.replace(regex, '<span class="highlight-text">$1</span>');
            element.classList.add('search-match');
        }

        function clearHighlights() {
            document.querySelectorAll('.alignment-block').forEach(block => {
                block.classList.remove('highlight', 'search-match');
                // Remove highlight spans
                const text = block.textContent;
                block.textContent = text;
            });
            setStatus('Highlights cleared', '');
        }

        function setStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status' + (type ? ' ' + type : '');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function escapeRegex(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }

        // Allow Enter key to trigger search
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchAndSync();
        });
    </script>
</body>
</html>"""

    # Create templates directory
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)

    # Write template
    template_file = templates_dir / 'parallel_viewer.html'
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Created template: {template_file}")


def main():
    """Run the web application."""
    import sys

    # Default paths
    chunks_file = '../data/melancolia_della_resistenza.jsonl'
    alignments_file = '../data/alignment_results.validated.jsonl'

    # Create template
    create_html_template()

    # Initialize data handler
    global data_handler
    data_handler = ParallelTextData(chunks_file, alignments_file)

    # Run Flask app
    print("\n" + "="*80)
    print("Starting Web Parallel Text Viewer")
    print("="*80)
    print("\nOpen your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")

    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()