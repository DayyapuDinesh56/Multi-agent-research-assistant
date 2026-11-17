import os
import re
import google.generativeai as genai
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunk:
    def __init__(self, text: str, source: str, page: int = None):
        self.text = text
        self.source = source
        self.page = page

def load_and_index(self, api_key: str, log_callback = None):
    """Processes all documents and loads/saves their vector representation into ChromaDB."""
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    if not os.path.exists(self.upload_dir):
        os.makedirs(self.upload_dir)
        return

    files = [f for f in os.listdir(self.upload_dir) if os.path.isfile(os.path.join(self.upload_dir, f))]
    if not files:
        log("RAG: No files found in the document library to index.")
        return

    log(f"RAG: Found {len(files)} files. Syncing database...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
    
    cache_dir = os.path.join(self.upload_dir, ".cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 1. Cleanup orphaned documents in ChromaDB
    try:
        existing = self.collection.get(include=["metadatas"])
        if existing and "metadatas" in existing:
            metadatas = existing["metadatas"]
            sources = {m.get("source") for m in metadatas if m and "source" in m}
            for source in sources:
                if source and not os.path.exists(os.path.join(self.upload_dir, source)):
                    log(f"RAG Clean: Removing orphaned document '{source}' from ChromaDB")
                    self.collection.delete(where={"source": source})
    except Exception as e:
        log(f"RAG Warning: Failed to clean orphaned records from ChromaDB: {e}")

    genai.configure(api_key=api_key)

    for filename in files:
        # Check if file already exists in ChromaDB
        try:
            cached_results = self.collection.get(
                where={"source": filename},
                limit=1
            )
            use_cache = len(cached_results.get("ids", [])) > 0
        except Exception:
            use_cache = False

        if use_cache:
            log(f"RAG: File '{filename}' already fully indexed in ChromaDB.")
            continue

        filepath = os.path.join(self.upload_dir, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        file_chunks = []
        
        if ext == '.pdf':
            try:
                # Check if a cached TXT file exists for this PDF in cache_dir
                cache_txt_path = os.path.join(cache_dir, f"{filename}.txt")
                combined_text = ""
                
                if os.path.exists(cache_txt_path):
                    log(f"RAG: Found cached transcribed text for '{filename}'. Loading...")
                    with open(cache_txt_path, "r", encoding="utf-8") as f_in:
                        combined_text = f_in.read()
                
                if combined_text.strip():
                    page_chunks = text_splitter.split_text(combined_text)
                    for chunk in page_chunks:
                        file_chunks.append(DocumentChunk(text=chunk, source=filename))
                else:
                    # Otherwise, attempt standard digital text extraction
                    from pypdf import PdfReader
                    log(f"RAG: PDF '{filename}' lacks cache. Reading digital text layer...")
                    reader = PdfReader(filepath)
                    chunks_added = 0
                    for page_idx, page in enumerate(reader.pages):
                        page_text = page.extract_text() or ""
                        page_text = re.sub(r'\s+', ' ', page_text).strip()
                        if page_text:
                            page_chunks = text_splitter.split_text(page_text)
                            for chunk in page_chunks:
                                file_chunks.append(DocumentChunk(text=chunk, source=filename, page=page_idx + 1))
                                chunks_added += 1
                                
                    # If standard extraction failed completely (scanned PDF)
                    if chunks_added == 0:
                        log(f"RAG: PDF '{filename}' contains no selectable text. Initiating automatic Gemini OCR...")
                        import fitz  # PyMuPDF
                        import time
                        
                        doc = fitz.open(filepath)
                        total_pages = len(doc)
                        
                        ocr_model = genai.GenerativeModel("models/gemini-3.1-flash-lite")
                        ocr_batch_size = 40
                        ocr_full_text = []
                        
                        for start_page in range(0, total_pages, ocr_batch_size):
                            end_page = min(start_page + ocr_batch_size, total_pages)
                            log(f"  RAG: OCR transcribing pages {start_page+1} to {end_page} of '{filename}'...")
                            
                            inputs = []
                            for p_idx in range(start_page, end_page):
                                p = doc[p_idx]
                                p_pix = p.get_pixmap(dpi=150)
                                p_bytes = p_pix.tobytes("png")
                                inputs.append({"mime_type": "image/png", "data": p_bytes})
                                
                            inputs.append(
                                "Analyze these pages. Extract all technical concepts, notes, and code snippets page-by-page. "
                                "Reorganize the content page-by-page under Markdown headers (e.g. '### Page X: [Title]'). "
                                "Preserve all code blocks, logic, and definitions, but format them cleanly."
                            )
                            
                            genai.configure(api_key=api_key)
                            response = ocr_model.generate_content(inputs)
                            ocr_text = response.text or ""
                            if ocr_text.strip():
                                ocr_full_text.append(ocr_text)
                            
                            # Stay within free-tier limits
                            time.sleep(5.0)
                            
                        # Save the transcribed text to cache_txt_path
                        combined_text = "\n\n".join(ocr_full_text)
                        if combined_text.strip():
                            with open(cache_txt_path, "w", encoding="utf-8") as f_out:
                                f_out.write(combined_text)
                            log(f"RAG: Successfully transcribed '{filename}' and cached in '.cache'.")
                            
                            # Split and load the transcribed text chunks
                            page_chunks = text_splitter.split_text(combined_text)
                            for chunk in page_chunks:
                                file_chunks.append(DocumentChunk(text=chunk, source=filename))
                    else:
                        log(f"RAG: Successfully extracted {chunks_added} chunks from digital text layer of '{filename}'.")
                                
            except Exception as e:
                log(f"RAG Warning: Error parsing PDF '{filename}': {e}")
        elif ext in ['.txt', '.md', '.json', '.csv']:
            try:
                log(f"RAG: Reading plain text file '{filename}'...")
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                content = re.sub(r'\s+', ' ', content).strip()
                if content:
                    file_chunks_texts = text_splitter.split_text(content)
                    for chunk in file_chunks_texts:
                        file_chunks.append(DocumentChunk(text=chunk, source=filename))
                    log(f"RAG: Successfully read {len(file_chunks)} chunks from plain text file '{filename}'.")
            except Exception as e:
                log(f"RAG Warning: Error parsing file '{filename}': {e}")
        
        if not file_chunks:
            continue

        log(f"RAG: Generating local embeddings for '{filename}' ({len(file_chunks)} chunks)...")
        
        # Generate local embeddings in batches of 128
        file_embeddings = []
        batch_size = 128
        for i in range(0, len(file_chunks), batch_size):
            batch = file_chunks[i:i+batch_size]
            batch_texts = [c.text for c in batch]
            
            try:
                embeddings_batch = self.model.encode(batch_texts).tolist()
                file_embeddings.extend(embeddings_batch)
            except Exception as e:
                log(f"RAG Error: Failed to generate local embeddings for batch of '{filename}': {e}")
                file_embeddings.extend([[0.0] * 384 for _ in batch])
        
        # Save to ChromaDB
        try:
            ids = [f"{filename}_{idx}" for idx in range(len(file_chunks))]
            documents = [c.text for c in file_chunks]
            metadatas = [{"source": filename, "page": c.page if c.page is not None else -1} for c in file_chunks]
            
            self.collection.add(
                ids=ids,
                embeddings=file_embeddings,
                documents=documents,
                metadatas=metadatas
            )
            log(f"RAG: Added '{filename}' ({len(file_chunks)} chunks) to ChromaDB.")
        except Exception as e:
            log(f"RAG Error: Failed to save documents to ChromaDB for '{filename}': {e}")

    log("RAG: Successfully completed embedding generation and indexing.")
