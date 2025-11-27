#!/usr/bin/env python3
"""
PDF-based Parallel Viewer for Melancolia della Resistenza
Displays actual English and Italian PDF books side by side with synchronized navigation.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify, send_from_directory


class PDFParallelViewer:
    def __init__(self, chunks_file: str, alignments_file: str, en_pdf: str, it_pdf: str):
        """Initialize the PDF parallel viewer."""
        self.chunks_file = Path(chunks_file)
        self.alignments_file = Path(alignments_file)
        self.en_pdf = Path(en_pdf)
        self.it_pdf = Path(it_pdf)

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
        """Search for text and return page info."""
        query = query.strip().lower()

        # Part offsets for converting local page numbers to global page numbers
        EN_PART_OFFSETS = {'001': 0, '002': 54, '003': 85, '004': 123, '005': 156, '006': 249}
        IT_PART_OFFSETS = {'001': 0, '002': 44, '003': 68, '004': 97, '005': 124, '006': 193}

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
        for alignment in self.alignments:
            chunks = alignment.get(field_to_search, [])
            for chunk in chunks:
                if chunk['chunk_id'] == chunk_id:
                    part = alignment.get('part', '001')

                    # Extract local page numbers and convert to global
                    src_chunks = alignment.get('src_chunks', [])
                    tgt_chunks = alignment.get('tgt_chunks', [])

                    if src_chunks:
                        local_page = min([int(c['page']) for c in src_chunks])
                        en_page = EN_PART_OFFSETS.get(part, 0) + local_page
                    else:
                        en_page = 1

                    if tgt_chunks:
                        local_page = min([int(c['page']) for c in tgt_chunks])
                        it_page = IT_PART_OFFSETS.get(part, 0) + local_page
                    else:
                        it_page = 1

                    return {
                        'found': True,
                        'chunk_id': chunk_id,
                        'language': language,
                        'en_page': en_page,
                        'it_page': it_page,
                        'src_text': alignment['src_text'],
                        'tgt_text': alignment['tgt_text'],
                        'part': part,
                        'confidence': alignment.get('validation', {}).get('confidence'),
                        'alignment_type': alignment.get('alignment_type'),
                        'query': query  # Add original query
                    }

        return {'error': 'No validated alignment found'}


# Initialize Flask app
app = Flask(__name__)
viewer = None


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('pdf_viewer.html')


@app.route('/pdfs/<filename>')
def serve_pdf(filename):
    """Serve PDF files."""
    if filename == 'en.pdf':
        return send_from_directory(viewer.en_pdf.parent, viewer.en_pdf.name)
    elif filename == 'it.pdf':
        return send_from_directory(viewer.it_pdf.parent, viewer.it_pdf.name)
    return "Not found", 404


@app.route('/api/search', methods=['POST'])
def search():
    """Search for text and return page numbers."""
    query = request.json.get('query', '')
    result = viewer.search_text(query)
    return jsonify(result)


def create_html_template():
    """Create the HTML template for PDF viewing."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Melancolia della Resistenza - PDF Parallel Viewer</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #2c3e50;
            overflow: hidden;
        }

        .header {
            background: #34495e;
            color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        h1 {
            font-size: 20px;
            margin-bottom: 10px;
        }

        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }

        .search-group {
            display: flex;
            gap: 10px;
            flex: 1;
            min-width: 300px;
        }

        #searchInput {
            flex: 1;
            padding: 8px 12px;
            font-size: 14px;
            border: none;
            border-radius: 4px;
        }

        button {
            padding: 8px 16px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            white-space: nowrap;
        }

        button:hover {
            background: #2980b9;
        }

        .nav-btn {
            background: #27ae60;
            width: 40px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }

        .nav-btn:hover {
            background: #229954;
        }

        .page-info {
            background: rgba(255,255,255,0.1);
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
            min-width: 100px;
            text-align: center;
        }

        .status {
            padding: 8px 12px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            font-size: 13px;
        }

        .status.success {
            background: #27ae60;
        }

        .status.error {
            background: #e74c3c;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0;
            height: calc(100vh - 120px);
            background: #2c3e50;
        }

        .pdf-panel {
            background: #34495e;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            border: 2px solid #2c3e50;
        }

        .panel-header {
            background: #2c3e50;
            color: white;
            padding: 10px;
            font-weight: bold;
            text-align: center;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-nav {
            display: flex;
            gap: 5px;
            align-items: center;
        }

        .panel-nav input {
            width: 50px;
            padding: 4px;
            text-align: center;
            border: none;
            border-radius: 3px;
        }

        .pdf-container {
            flex: 1;
            overflow: auto;
            background: #1a1a1a;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 20px;
            padding-bottom: 100px;
        }

        .pdf-canvas {
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            background: white;
        }

        .sync-checkbox {
            display: flex;
            align-items: center;
            gap: 5px;
            color: white;
        }

        .info-panel {
            background: rgba(52, 73, 94, 0.95);
            color: white;
            padding: 15px;
            margin: 10px 20px;
            border-radius: 4px;
            display: none;
        }

        .info-panel.show {
            display: block;
        }

        .info-panel h3 {
            margin-bottom: 10px;
            color: #3498db;
        }

        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            font-size: 13px;
        }

        .info-section {
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 4px;
        }

        .info-label {
            color: #95a5a6;
            font-size: 11px;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Melancolia della Resistenza - PDF Parallel Viewer</h1>
        <div class="controls">
            <div class="search-group">
                <input type="text" id="searchInput" placeholder="Search text to sync pages...">
                <button onclick="searchAndSync()">Find & Sync</button>
            </div>

            <div class="sync-checkbox">
                <input type="checkbox" id="syncScroll" checked>
                <label for="syncScroll">Sync Scroll</label>
            </div>

            <button class="nav-btn" onclick="previousPage()">◀</button>
            <button class="nav-btn" onclick="nextPage()">▶</button>

            <div id="status" class="status">Ready</div>
        </div>
    </div>

    <div id="infoPanel" class="info-panel">
        <h3>Search Result</h3>
        <div class="info-grid">
            <div class="info-section">
                <div class="info-label">English Text</div>
                <div id="infoEnText"></div>
            </div>
            <div class="info-section">
                <div class="info-label">Italian Text</div>
                <div id="infoItText"></div>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="pdf-panel" id="enPanel">
            <div class="panel-header">
                <span>ENGLISH</span>
                <div class="panel-nav">
                    <button class="nav-btn" onclick="enPrevPage()">◀</button>
                    <input type="number" id="enPageInput" value="1" min="1" onchange="enGoToPage()">
                    <span class="page-info">/ <span id="enPageCount">-</span></span>
                    <button class="nav-btn" onclick="enNextPage()">▶</button>
                </div>
            </div>
            <div class="pdf-container" id="enContainer">
                <canvas id="enCanvas" class="pdf-canvas"></canvas>
            </div>
        </div>

        <div class="pdf-panel" id="itPanel">
            <div class="panel-header">
                <span>ITALIANO</span>
                <div class="panel-nav">
                    <button class="nav-btn" onclick="itPrevPage()">◀</button>
                    <input type="number" id="itPageInput" value="1" min="1" onchange="itGoToPage()">
                    <span class="page-info">/ <span id="itPageCount">-</span></span>
                    <button class="nav-btn" onclick="itNextPage()">▶</button>
                </div>
            </div>
            <div class="pdf-container" id="itContainer">
                <canvas id="itCanvas" class="pdf-canvas"></canvas>
            </div>
        </div>
    </div>

    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        let enPdf = null;
        let itPdf = null;
        let enCurrentPage = 1;
        let itCurrentPage = 1;
        let enRendering = false;
        let itRendering = false;

        // Load PDFs
        async function loadPDFs() {
            try {
                setStatus('Loading PDFs...', '');

                enPdf = await pdfjsLib.getDocument('/pdfs/en.pdf').promise;
                itPdf = await pdfjsLib.getDocument('/pdfs/it.pdf').promise;

                document.getElementById('enPageCount').textContent = enPdf.numPages;
                document.getElementById('itPageCount').textContent = itPdf.numPages;

                await Promise.all([renderPage('en', 1), renderPage('it', 1)]);
                setStatus('PDFs loaded successfully', 'success');
            } catch (error) {
                setStatus('Error loading PDFs: ' + error.message, 'error');
            }
        }

        async function renderPage(lang, pageNum) {
            const pdf = lang === 'en' ? enPdf : itPdf;
            const canvas = document.getElementById(lang + 'Canvas');
            const ctx = canvas.getContext('2d');
            const pageInput = document.getElementById(lang + 'PageInput');

            // Check language-specific rendering flag
            if (lang === 'en') {
                if (enRendering) return;
                enRendering = true;
            } else {
                if (itRendering) return;
                itRendering = true;
            }

            if (!pdf) {
                if (lang === 'en') enRendering = false;
                else itRendering = false;
                return;
            }

            try {
                const page = await pdf.getPage(pageNum);
                const viewport = page.getViewport({ scale: 1.5 });

                canvas.width = viewport.width;
                canvas.height = viewport.height;

                await page.render({
                    canvasContext: ctx,
                    viewport: viewport
                }).promise;

                if (lang === 'en') {
                    enCurrentPage = pageNum;
                } else {
                    itCurrentPage = pageNum;
                }

                pageInput.value = pageNum;
            } catch (error) {
                console.error('Error rendering page:', error);
            } finally {
                if (lang === 'en') {
                    enRendering = false;
                } else {
                    itRendering = false;
                }
            }
        }

        // Navigation functions
        function enPrevPage() {
            if (enCurrentPage > 1) {
                renderPage('en', enCurrentPage - 1);
                if (document.getElementById('syncScroll').checked) {
                    itPrevPage();
                }
            }
        }

        function enNextPage() {
            if (enPdf && enCurrentPage < enPdf.numPages) {
                renderPage('en', enCurrentPage + 1);
                if (document.getElementById('syncScroll').checked) {
                    itNextPage();
                }
            }
        }

        function itPrevPage() {
            if (itCurrentPage > 1) {
                renderPage('it', itCurrentPage - 1);
            }
        }

        function itNextPage() {
            if (itPdf && itCurrentPage < itPdf.numPages) {
                renderPage('it', itCurrentPage + 1);
            }
        }

        function previousPage() {
            enPrevPage();
            if (document.getElementById('syncScroll').checked) {
                itPrevPage();
            }
        }

        function nextPage() {
            enNextPage();
            if (document.getElementById('syncScroll').checked) {
                itNextPage();
            }
        }

        function enGoToPage() {
            const pageNum = parseInt(document.getElementById('enPageInput').value);
            if (pageNum >= 1 && pageNum <= enPdf.numPages) {
                renderPage('en', pageNum);
            }
        }

        function itGoToPage() {
            const pageNum = parseInt(document.getElementById('itPageInput').value);
            if (pageNum >= 1 && pageNum <= itPdf.numPages) {
                renderPage('it', pageNum);
            }
        }

        // Search functionality
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
                    document.getElementById('infoPanel').classList.remove('show');
                    return;
                }

                // Navigate to pages
                await Promise.all([
                    renderPage('en', result.en_page),
                    renderPage('it', result.it_page)
                ]);

                // Small delay to ensure rendering is complete
                await new Promise(resolve => setTimeout(resolve, 100));

                // Highlight using the actual user query for the searched language
                let enSearchText, itSearchText;
                if (result.language === 'en') {
                    enSearchText = result.query;
                    itSearchText = result.tgt_text.split(/\s+/).slice(0, 2).join(' ').toLowerCase();
                } else {
                    itSearchText = result.query;
                    enSearchText = result.src_text.split(/\s+/).slice(0, 2).join(' ').toLowerCase();
                }

                await Promise.all([
                    scrollToText('en', result.en_page, enSearchText),
                    scrollToText('it', result.it_page, itSearchText)
                ]);

                // Show info
                document.getElementById('infoEnText').textContent = result.src_text;
                document.getElementById('infoItText').textContent = result.tgt_text;
                document.getElementById('infoPanel').classList.add('show');

                setStatus(
                    `Found! Pages: EN ${result.en_page}, IT ${result.it_page} - ` +
                    `Confidence: ${result.confidence?.toFixed(2) || 'N/A'}`,
                    'success'
                );
            } catch (error) {
                setStatus('Error: ' + error.message, 'error');
            }
        }

        async function scrollToText(lang, pageNum, searchText) {
            const pdf = lang === 'en' ? enPdf : itPdf;
            const container = document.getElementById(lang + 'Container');
            const canvas = document.getElementById(lang + 'Canvas');

            try {
                // First, re-render the page to clear any previous highlights
                await renderPage(lang, pageNum);

                // Small delay to ensure render is complete
                await new Promise(resolve => setTimeout(resolve, 100));

                const page = await pdf.getPage(pageNum);
                const textContent = await page.getTextContent();
                const viewport = page.getViewport({ scale: 1.5 });

                // Get all text items
                const textItems = textContent.items;
                let foundItems = [];

                // Filter words: prefer longer words but keep at least some
                const allWords = searchText.toLowerCase().split(/\s+/).filter(w => w.length > 2);
                // Prioritize longer words to reduce false matches, but fallback to shorter if needed
                let searchWords = allWords.filter(w => w.length > 4);
                if (searchWords.length === 0) {
                    searchWords = allWords.filter(w => w.length > 3);
                }
                if (searchWords.length === 0) {
                    searchWords = allWords;
                }

                // Build continuous text with position tracking
                let pageText = '';
                let itemMap = [];
                for (let i = 0; i < textItems.length; i++) {
                    const start = pageText.length;
                    const itemStr = textItems[i].str;
                    pageText += itemStr + ' ';
                    itemMap.push({ start, end: start + itemStr.length, index: i });
                }

                // Match words with word boundaries
                const matchedIndices = new Set();
                const pageTextLower = pageText.toLowerCase();

                for (const word of searchWords) {
                    // Simple substring search in lowercase text
                    const wordLower = word.toLowerCase();
                    let index = pageTextLower.indexOf(wordLower);

                    while (index !== -1) {
                        // Check word boundaries manually
                        const before = index > 0 ? pageTextLower[index - 1] : ' ';
                        const after = index + wordLower.length < pageTextLower.length ?
                                     pageTextLower[index + wordLower.length] : ' ';

                        const isWordBoundaryBefore = !/[a-z0-9]/.test(before);
                        const isWordBoundaryAfter = !/[a-z0-9]/.test(after);

                        if (isWordBoundaryBefore && isWordBoundaryAfter) {
                            // Find which text items contain this match
                            for (const item of itemMap) {
                                if (index >= item.start && index < item.end) {
                                    matchedIndices.add(item.index);
                                    break;
                                }
                            }
                        }

                        index = pageTextLower.indexOf(wordLower, index + 1);
                    }
                }

                // Collect matched items
                for (const idx of matchedIndices) {
                    foundItems.push(textItems[idx]);
                }

                if (foundItems.length > 0) {
                    // Highlight all found text items
                    const ctx = canvas.getContext('2d');
                    ctx.save();

                    const scale = 1.5; // Must match viewport scale

                    for (const item of foundItems) {
                        const tx = item.transform;
                        // Transform matrix: [scaleX, skewY, skewX, scaleY, translateX, translateY]
                        // Apply viewport scale to convert from PDF space to canvas space
                        const x = tx[4] * scale;
                        const y = tx[5] * scale;
                        const width = item.width * scale;
                        const height = item.height * scale;

                        // Convert PDF coordinates (bottom-up) to canvas coordinates (top-down)
                        const canvasX = x;
                        const canvasY = viewport.height - y;

                        // Draw yellow highlight rectangle with some transparency
                        ctx.fillStyle = 'rgba(255, 255, 0, 0.4)';
                        ctx.fillRect(canvasX, canvasY - height, width, height);

                        // Draw colored underline
                        ctx.strokeStyle = 'rgba(255, 165, 0, 0.8)';
                        ctx.lineWidth = 3;
                        ctx.beginPath();
                        ctx.moveTo(canvasX, canvasY);
                        ctx.lineTo(canvasX + width, canvasY);
                        ctx.stroke();
                    }

                    ctx.restore();

                    // Scroll to the first found item
                    const firstItem = foundItems[0];
                    const pdfY = firstItem.transform[5] * scale;
                    const canvasY = viewport.height - pdfY;

                    const containerHeight = container.clientHeight;
                    const scrollY = canvasY - (containerHeight / 2);

                    container.scrollTop = Math.max(0, scrollY);
                }
            } catch (error) {
                console.error('Error scrolling to text:', error);
            }
        }

        function setStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status' + (type ? ' ' + type : '');
        }

        // Allow Enter key to search
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchAndSync();
        });

        // Load PDFs on page load
        window.addEventListener('load', loadPDFs);
    </script>
</body>
</html>"""

    # Create templates directory
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)

    # Write template
    template_file = templates_dir / 'pdf_viewer.html'
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Created template: {template_file}")


def main():
    """Run the PDF viewer application."""
    # Paths (relative to script location)
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'

    chunks_file = data_dir / 'melancolia_della_resistenza.jsonl'
    alignments_file = data_dir / 'alignment_results.validated.jsonl'
    en_pdf = data_dir / 'en.pdf'
    it_pdf = data_dir / 'it.pdf'

    # Create template
    create_html_template()

    # Initialize viewer
    global viewer
    viewer = PDFParallelViewer(chunks_file, alignments_file, en_pdf, it_pdf)

    # Run Flask app
    print("\n" + "="*80)
    print("Starting PDF Parallel Viewer")
    print("="*80)
    print("\nOpen your browser to: http://localhost:5001")
    print("Press Ctrl+C to stop the server\n")

    app.run(host='0.0.0.0', port=5001, debug=False)


if __name__ == '__main__':
    main()