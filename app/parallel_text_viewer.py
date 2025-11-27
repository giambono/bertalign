#!/usr/bin/env python3
"""
Parallel Text Viewer for Melancolia della Resistenza
Displays aligned English and Italian texts side by side with synchronized scrolling.
"""

import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class ParallelTextViewer:
    def __init__(self, chunks_file: str, alignments_file: str):
        """Initialize the parallel text viewer."""
        self.chunks_file = Path(chunks_file)
        self.alignments_file = Path(alignments_file)

        # Load data
        print("Loading chunks...")
        self.chunks = self._load_chunks()
        print(f"Loaded {len(self.chunks)} chunks")

        print("Loading alignments...")
        self.alignments = self._load_alignments()
        print(f"Loaded {len(self.alignments)} alignments")

        # Create chunk index for faster lookup
        self.chunk_index = {chunk['chunk_id']: chunk for chunk in self.chunks}

        # Build the UI
        self.root = tk.Tk()
        self.root.title("Melancolia della Resistenza - Parallel Text Viewer")
        self.root.geometry("1400x900")

        self._setup_ui()
        self._populate_texts()

    def _load_chunks(self) -> List[Dict[str, Any]]:
        """Load all chunks from JSONL file."""
        chunks = []
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
        return sorted(chunks, key=lambda x: x['chunk_id'])

    def _load_alignments(self) -> List[Dict[str, Any]]:
        """Load all validated alignments."""
        alignments = []
        with open(self.alignments_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    alignment = json.loads(line)
                    # Only load validated alignments
                    if alignment.get('validation', {}).get('validation_success', False):
                        alignments.append(alignment)
        return alignments

    def _setup_ui(self):
        """Setup the user interface."""
        # Search frame at top
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind('<Return>', lambda e: self.search_and_sync())

        ttk.Button(search_frame, text="Find & Sync", command=self.search_and_sync).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Clear Highlights", command=self.clear_highlights).pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(search_frame, textvariable=self.status_var, foreground="blue")
        status_label.pack(side=tk.LEFT, padx=20)

        # Main frame with two text areas
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Configure grid
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Headers
        ttk.Label(main_frame, text="ENGLISH", font=('Arial', 12, 'bold')).grid(row=0, column=0, pady=5)
        ttk.Label(main_frame, text="ITALIANO", font=('Arial', 12, 'bold')).grid(row=0, column=1, pady=5)

        # English text area
        self.en_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            width=60,
            height=40,
            font=('Arial', 11),
            padx=10,
            pady=10
        )
        self.en_text.grid(row=1, column=0, sticky='nsew', padx=(0, 5))

        # Italian text area
        self.it_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            width=60,
            height=40,
            font=('Arial', 11),
            padx=10,
            pady=10
        )
        self.it_text.grid(row=1, column=1, sticky='nsew', padx=(5, 0))

        # Configure tags for highlighting
        self.en_text.tag_config("highlight", background="yellow", foreground="black")
        self.en_text.tag_config("search_result", background="orange", foreground="black")
        self.it_text.tag_config("highlight", background="yellow", foreground="black")
        self.it_text.tag_config("search_result", background="orange", foreground="black")

        # Bind synchronized scrolling
        self.en_text.bind('<MouseWheel>', self._on_mousewheel)
        self.it_text.bind('<MouseWheel>', self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Synchronize scrolling between text widgets."""
        # Scroll both text widgets together
        self.en_text.yview_scroll(int(-1*(event.delta/120)), "units")
        self.it_text.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def _populate_texts(self):
        """Populate both text areas with aligned content."""
        self.en_text.config(state=tk.NORMAL)
        self.it_text.config(state=tk.NORMAL)

        self.en_text.delete('1.0', tk.END)
        self.it_text.delete('1.0', tk.END)

        # Store alignment positions for search
        self.alignment_positions = []

        for i, alignment in enumerate(self.alignments):
            part = alignment.get('part', '')
            src_text = alignment.get('src_text', '')
            tgt_text = alignment.get('tgt_text', '')
            src_chunks = alignment.get('src_chunks', [])
            tgt_chunks = alignment.get('tgt_chunks', [])
            confidence = alignment.get('validation', {}).get('confidence', 0)

            # Insert into English text
            en_start = self.en_text.index(tk.INSERT)
            if i == 0 or alignment.get('part') != self.alignments[i-1].get('part'):
                self.en_text.insert(tk.END, f"\n{'='*60}\n")
                self.en_text.insert(tk.END, f"PART {part}\n")
                self.en_text.insert(tk.END, f"{'='*60}\n\n")

            en_start = self.en_text.index(tk.INSERT)
            self.en_text.insert(tk.END, src_text)
            en_end = self.en_text.index(tk.INSERT)
            self.en_text.insert(tk.END, "\n\n")

            # Insert into Italian text
            if i == 0 or alignment.get('part') != self.alignments[i-1].get('part'):
                self.it_text.insert(tk.END, f"\n{'='*60}\n")
                self.it_text.insert(tk.END, f"PARTE {part}\n")
                self.it_text.insert(tk.END, f"{'='*60}\n\n")

            it_start = self.it_text.index(tk.INSERT)
            self.it_text.insert(tk.END, tgt_text)
            it_end = self.it_text.index(tk.INSERT)
            self.it_text.insert(tk.END, "\n\n")

            # Store position info
            self.alignment_positions.append({
                'alignment': alignment,
                'en_start': en_start,
                'en_end': en_end,
                'it_start': it_start,
                'it_end': it_end,
                'index': i
            })

        self.en_text.config(state=tk.DISABLED)
        self.it_text.config(state=tk.DISABLED)

        print(f"Populated {len(self.alignment_positions)} alignment pairs")

    def search_and_sync(self):
        """Search for text and sync both panes to the result."""
        search_text = self.search_var.get().strip().lower()

        if not search_text:
            messagebox.showwarning("Search", "Please enter text to search")
            return

        self.clear_highlights()

        # Search in chunks first to get language
        found_chunk = None
        for chunk in self.chunks:
            if search_text in chunk['text'].lower():
                found_chunk = chunk
                break

        if not found_chunk:
            self.status_var.set(f"❌ Text '{search_text}' not found in chunks")
            return

        chunk_id = found_chunk['chunk_id']
        language = found_chunk['language']

        self.status_var.set(f"Found chunk_id={chunk_id}, language={language}")

        # Find alignment containing this chunk
        found_alignment = None
        field_to_search = 'src_chunks' if language == 'en' else 'tgt_chunks'

        for pos_info in self.alignment_positions:
            alignment = pos_info['alignment']
            chunks = alignment.get(field_to_search, [])

            for chunk in chunks:
                if chunk['chunk_id'] == chunk_id:
                    found_alignment = pos_info
                    break

            if found_alignment:
                break

        if not found_alignment:
            self.status_var.set(f"❌ No validated alignment found for chunk_id={chunk_id}")
            return

        # Highlight and scroll to the position
        self.en_text.config(state=tk.NORMAL)
        self.it_text.config(state=tk.NORMAL)

        # Highlight the matching paragraph
        self.en_text.tag_add("highlight", found_alignment['en_start'], found_alignment['en_end'])
        self.it_text.tag_add("highlight", found_alignment['it_start'], found_alignment['it_end'])

        # Highlight the specific search term
        if language == 'en':
            self._highlight_search_term(self.en_text, found_alignment['en_start'],
                                       found_alignment['en_end'], search_text)
        else:
            self._highlight_search_term(self.it_text, found_alignment['it_start'],
                                       found_alignment['it_end'], search_text)

        # Scroll to position (centered)
        self.en_text.see(found_alignment['en_start'])
        self.it_text.see(found_alignment['it_start'])

        # Mark as current position
        self.en_text.mark_set("current", found_alignment['en_start'])
        self.it_text.mark_set("current", found_alignment['it_start'])

        self.en_text.config(state=tk.DISABLED)
        self.it_text.config(state=tk.DISABLED)

        alignment = found_alignment['alignment']
        confidence = alignment.get('validation', {}).get('confidence', 0)
        self.status_var.set(f"✓ Found! Chunk {chunk_id} ({language}) - Confidence: {confidence:.2f}")

    def _highlight_search_term(self, text_widget, start_pos, end_pos, search_term):
        """Highlight the specific search term within a range."""
        # Get the text content
        content = text_widget.get(start_pos, end_pos).lower()
        search_term = search_term.lower()

        # Find all occurrences
        start_idx = 0
        while True:
            idx = content.find(search_term, start_idx)
            if idx == -1:
                break

            # Calculate positions
            term_start = f"{start_pos} + {idx}c"
            term_end = f"{start_pos} + {idx + len(search_term)}c"

            text_widget.tag_add("search_result", term_start, term_end)
            start_idx = idx + 1

    def clear_highlights(self):
        """Clear all highlights."""
        self.en_text.config(state=tk.NORMAL)
        self.it_text.config(state=tk.NORMAL)

        self.en_text.tag_remove("highlight", "1.0", tk.END)
        self.en_text.tag_remove("search_result", "1.0", tk.END)
        self.it_text.tag_remove("highlight", "1.0", tk.END)
        self.it_text.tag_remove("search_result", "1.0", tk.END)

        self.en_text.config(state=tk.DISABLED)
        self.it_text.config(state=tk.DISABLED)

        self.status_var.set("Highlights cleared")

    def run(self):
        """Start the application."""
        print("Starting GUI...")
        self.root.mainloop()


def main():
    """Main entry point."""
    import sys

    # Default paths (relative to script location)
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'

    chunks_file = data_dir / 'melancolia_della_resistenza.jsonl'
    alignments_file = data_dir / 'alignment_results.validated.jsonl'

    # Allow command line arguments
    if len(sys.argv) > 1:
        chunks_file = sys.argv[1]
    if len(sys.argv) > 2:
        alignments_file = sys.argv[2]

    try:
        app = ParallelTextViewer(chunks_file, alignments_file)
        app.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"\nUsage: {sys.argv[0]} [chunks_file] [alignments_file]")
        print(f"\nDefault paths:")
        print(f"  chunks_file: {chunks_file}")
        print(f"  alignments_file: {alignments_file}")
        sys.exit(1)


if __name__ == '__main__':
    main()