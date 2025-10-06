"""
Iowa Agronomy RAG - Ingestion & Chunking Service
------------------------------------------------
- Downloads 1..N documents (PDF or HTML)
- Extracts clean text
- Builds two chunked indexes using LlamaIndex:
    1) Sentence-Window nodes
    2) Auto-Merging nodes (hierarchical)
- Persists local artifacts (raw, processed, indexes)
- Optionally uploads artifacts to Google Cloud Storage (GCS)

Design notes:
- OpenAI is OPTIONAL (used only if OPENAI_API_KEY is provided).
- Embeddings default to a local HuggingFace model (BAAI/bge-small-en-v1.5).
- GCS paths are prefixed under: gs://<GCS_BUCKET>/RAG_pipeline/...
- The code is heavily commented so new contributors can follow along.
"""

import os
import json
import hashlib
import logging
from google.cloud import storage
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from charset_normalizer import from_bytes as _cn_from_bytes
from ftfy import fix_text

import requests
import trafilatura
from google.cloud import storage

# LlamaIndex core imports use the v0.10+ namespaced modules
from llama_index.core import (
    Document,
    SimpleDirectoryReader,
    ServiceContext,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import (
    SentenceWindowNodeParser,
    HierarchicalNodeParser,
    get_leaf_nodes,
)

# Optional LLM (only used if OPENAI_API_KEY is present)
from llama_index.llms.openai import OpenAI as LIOpenAI

# Local embedding model (preferred for ingestion to avoid network deps)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("ingestion")


# ---------- Utilities ----------
def sha12(s: str) -> str:
    """Return a 12-char SHA256 hexdigest, used for stable, short IDs."""
    return hashlib.sha256(s.encode()).hexdigest()[:12]

def _robust_decode(html_bytes: bytes) -> tuple[str, str]:
    # 1) If it's valid UTF-8, use that (prevents false cp1252 guesses)
    try:
        return html_bytes.decode("utf-8", errors="strict"), "utf-8"
    except UnicodeDecodeError:
        pass
    # 2) Otherwise use detector's best guess
    probe = _cn_from_bytes(html_bytes).best()
    if probe and getattr(probe, "encoding", None):
        enc = probe.encoding
        try:
            return html_bytes.decode(enc, errors="strict"), enc
        except Exception:
            pass
    # 3) Last resort: cp1252 (common legacy)
    return html_bytes.decode("cp1252", errors="replace"), "cp1252"

def extract_html_text(html_bytes: bytes) -> str:
    html, enc = _robust_decode(html_bytes)
    text = trafilatura.extract(
        html,
        include_tables=True,
        include_comments=False,
        include_images=False,
    ) or ""
    return fix_text(text).strip()

def count_nodes_safely(index: VectorStoreIndex) -> int:
    """
    Return a robust node count across LlamaIndex minor versions.
    We prefer storage_context.docstore.docs, then fall back if needed.
    """
    try:
        return len(index.storage_context.docstore.docs)  # v0.10+ typical path
    except Exception:
        try:
            return len(getattr(index, "docstore").docs)  # older fallback
        except Exception:
            return -1


# ---------- GCS Manager ----------
class GCSStorageManager:
    """
    Thin wrapper around google-cloud-storage to upload artifacts
    into a predictable folder structure under project bucket.
    """

    # Folder structure under base prefix (`RAG_pipeline`)
    FOLDERS = {
        "raw": "data/raw",               # original bytes
        "processed": "data/processed",   # extracted text files
        "indexes": "indexes",            # LlamaIndex persisted snapshots
        "metadata": "metadata",          # per-document metadata JSON
        "logs": "logs",                  # ingestion run logs
    }

    def __init__(self, bucket_name: str, base_prefix: str = "RAG_pipeline"):
        """
        Args:
            bucket_name: Name of the GCS bucket ('agriguard-ac215-data').
            base_prefix: Root folder inside the bucket (default: 'RAG_pipeline').
        """
        self.bucket_name = bucket_name
        self.base_prefix = base_prefix.strip("/")

        # Client will use GOOGLE_APPLICATION_CREDENTIALS env to locate SA JSON.
        # In Docker, mount your SA file and set env to its path.
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

        log.info(f"Connected to GCS bucket: gs://{bucket_name}/{self.base_prefix}/")

    def _path(self, folder_key: str, filename: str) -> str:
        """Build the final GCS object path for a given folder key + filename."""
        subdir = self.FOLDERS[folder_key].strip("/")
        return f"{self.base_prefix}/{subdir}/{filename}"

    def upload_file(self, local_path: str, folder_key: str, filename: str) -> str:
        """
        Upload a single local file to GCS.
        Returns the gs:// URI of the uploaded object.
        """
        gcs_path = self._path(folder_key, filename)
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        uri = f"gs://{self.bucket_name}/{gcs_path}"
        log.info(f"☁️  Uploaded file → {uri}")
        return uri

    def upload_json(self, data: dict, folder_key: str, filename: str) -> str:
        """
        Upload a JSON-serializable Python object to GCS as a .json file.
        Returns the gs:// URI of the uploaded object.
        """
        gcs_path = self._path(folder_key, filename)
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(json.dumps(data, indent=2), content_type="application/json")
        uri = f"gs://{self.bucket_name}/{gcs_path}"
        log.info(f"☁️  Uploaded JSON → {uri}")
        return uri

    def upload_directory(self, local_dir: str, folder_key: str, prefix: str = "") -> List[str]:
        """
        Recursively upload all files under `local_dir` to GCS, preserving
        relative subpaths under the destination folder. Useful for LlamaIndex
        persist directories which contain multiple small files.

        Args:
            local_dir: Path to a local directory to traverse.
            folder_key: One of the keys in FOLDERS (e.g 'indexes').
            prefix: Optional extra subfolder inside the destination folder.

        Returns:
            List of gs:// URIs for uploaded files.
        """
        uploaded = []
        base = Path(local_dir)
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(base).as_posix()
            # Compose: <base_prefix>/<FOLDERS[folder_key]>/<prefix>/<rel>
            subdir = self.FOLDERS[folder_key].strip("/")
            if prefix:
                gcs_path = f"{self.base_prefix}/{subdir}/{prefix.strip('/')}/{rel}"
            else:
                gcs_path = f"{self.base_prefix}/{subdir}/{rel}"
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(str(p))
            uri = f"gs://{self.bucket_name}/{gcs_path}"
            uploaded.append(uri)
        log.info(f"☁️  Uploaded {len(uploaded)} files from {local_dir}")
        return uploaded


# ---------- Document Processor ----------
class DocumentProcessor:
    """
    Responsible for downloading source documents and turning them into
    clean text `Document` objects that LlamaIndex can chunk/index.

    Local directories:
      - data/raw       : the original bytes (PDF/HTML/etc.)
      - data/processed : text files stitched from parsed pages
    """

    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, filename: Optional[str] = None) -> Path:
        """
        Download bytes from a URL and save to data/raw/<filename>.
        Returns the local file path.

        Note:
          - For HTML pages, we still persist the raw HTML so the run is auditable.
          - We do not do content-type sniffing; the extension in `filename`
            guides parsing later ('.pdf' vs '.html').
        """
        if not filename:
            # Best-effort name from URL; fall back to short hash.
            tail = url.split("/")[-1] or ""
            if not tail:
                tail = f"doc_{sha12(url)}.bin"
            filename = tail
        out = self.raw_dir / filename

        log.info(f"Downloading: {url}")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        out.write_bytes(r.content)
        log.info(f"Saved raw → {out} ({len(r.content)/1024:.1f} KB)")
        return out

    def parse_to_documents(self, file_path: Path) -> List[Document]:
        """
        Convert a raw file into LlamaIndex `Document` objects.
        Strategy:
          - PDFs and common formats → SimpleDirectoryReader
          - HTML → Trafilatura for boilerplate removal
          - Fallback → try SDR; if that fails, return an empty doc
        """
        suffix = file_path.suffix.lower()
        log.info(f"Parsing: {file_path.name}")

        if suffix in {".pdf", ".docx", ".pptx", ".txt", ".md"}:
            docs = SimpleDirectoryReader(input_files=[str(file_path)]).load_data()
            log.info(f"Extracted {len(docs)} page(s)")
            return docs

        if suffix in {".html", ".htm"}:
            text = extract_html_text(file_path.read_bytes())
            log.info(f"Extracted {len(text):,} characters from HTML")
            return [Document(text=text, metadata={"file_name": file_path.name})]

        # Try HTML extraction by testing if extension is odd
        try:
            text = extract_html_text(file_path.read_bytes())
            if text.strip():
                log.info(f"Extracted {len(text):,} characters via HTML sniff")
                return [Document(text=text, metadata={"file_name": file_path.name})]
        except Exception:
            pass

        # Fallback to SDR
        try:
            docs = SimpleDirectoryReader(input_files=[str(file_path)]).load_data()
            log.info(f"Extracted {len(docs)} page(s) via SDR fallback")
            return docs
        except Exception as e:
            log.warning(f"Could not parse {file_path.name}: {e}")
            return []

    def save_processed_text(self, docs: List[Document], stem: str) -> Path:
        """
        Write human-readable text artifact that concatenates pages with delimiters.
        Helps with quick manual QA of the extraction phase.
        """
        out = self.processed_dir / f"{stem}.txt"
        with out.open("w", encoding="utf-8") as f:
            for i, d in enumerate(docs, 1):
                f.write(f"--- Page {i} ---\n")
                f.write(d.text or "")
                f.write("\n\n")
        log.info(f"Saved processed text → {out}")
        return out


# ---------- Chunking / Index Engine ----------
class ChunkingEngine:
    """
    Builds two types of chunked indexes that are well-tested in advanced RAG:
      - Sentence Window: sentence nodes with sliding windows for context
      - Auto-Merging: hierarchical nodes that can merge up for broader context

    The engine constructs a LlamaIndex ServiceContext with:
      - local embedding model (default)
      - optional LLM (if OPENAI_API_KEY is provided)
      - the appropriate node parser per strategy
    """

    def __init__(self, embed_model: HuggingFaceEmbedding, llm: Optional[LIOpenAI]):
        self.embed_model = embed_model
        self.llm = llm

        # Sentence Window Parser (each node = sentence with neighboring context)
        self.sentence_parser = SentenceWindowNodeParser.from_defaults(
            window_size=3,                       # include +/- 3 sentence window
            window_metadata_key="window",        # where to store window text
            original_text_metadata_key="orig",   # where to store original sentence
        )

        # Hierarchical Parser (large->medium->small chunks)
        self.hier_parser = HierarchicalNodeParser.from_defaults(
            chunk_sizes=[2048, 512, 128]         #[parent,child,leaf(what gets embedded)]
            # adjust based on agronomy documents format (might be too big right now)
            # need to test out different types

        )

    def _svc(self, node_parser=None) -> ServiceContext:
        """Build a ServiceContext with the chosen parser + embedding + optional LLM."""
        return ServiceContext.from_defaults(
            llm=self.llm,                        # can be None
            embed_model=self.embed_model,        # local, no network
            node_parser=node_parser              # parser for this strategy
        )

    def sentence_window_index(self, doc: Document, persist_dir: Path) -> VectorStoreIndex:
        """
        Build (or load if present) a Sentence-Window index over a single merged document.
        """
        log.info("Building Sentence-Window index ...")
        svc = self._svc(node_parser=self.sentence_parser)

        if persist_dir.exists():
            log.info(f"Loading existing index from {persist_dir}")
            storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
            return load_index_from_storage(storage_context, service_context=svc)

        index = VectorStoreIndex.from_documents([doc], service_context=svc, show_progress=True)
        persist_dir.mkdir(parents=True, exist_ok=True)
        index.storage_context.persist(persist_dir=str(persist_dir))
        log.info(f"Persisted Sentence-Window index → {persist_dir}")
        return index

    def automerging_index(self, docs: List[Document], persist_dir: Path) -> VectorStoreIndex:
        """
        Build (or load if present) an Auto-Merging index over a list of page documents.
        Steps:
          1) Create hierarchical nodes (large→medium→small).
          2) Keep leaf nodes for indexing (parents allow merging when needed).
        """
        log.info("Building Auto-Merging index ...")
        if persist_dir.exists():
            log.info(f"oading existing index from {persist_dir}")
            storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
            svc = self._svc()
            return load_index_from_storage(storage_context, service_context=svc)

        # Parse hierarchy then get leaves
        all_nodes = self.hier_parser.get_nodes_from_documents(docs)
        leaf_nodes = get_leaf_nodes(all_nodes)
        log.info(f"Hierarchy: {len(all_nodes)} total nodes, {len(leaf_nodes)} leaf nodes")

        # Create a fresh storage context and add the nodes; index on leaves
        storage_context = StorageContext.from_defaults()
        storage_context.docstore.add_documents(all_nodes)
        svc = self._svc()
        index = VectorStoreIndex(leaf_nodes, storage_context=storage_context, service_context=svc, show_progress=True)

        persist_dir.mkdir(parents=True, exist_ok=True)
        index.storage_context.persist(persist_dir=str(persist_dir))
        log.info(f"Persisted Auto-Merging index → {persist_dir}")
        return index


# ---------- Orchestrator ----------
class IngestionPipeline:
    """
    Orchestrates a full pass for one document:
      1) Download raw bytes
      2) Parse into text `Document` objects
      3) Save a stitched text artifact (for QA)
      4) Build Sentence-Window & Auto-Merging indexes
      5) Upload artifacts/metadata to GCS (if configured)
    """

    def __init__(self):
        # Local dirs for artifacts
        self.data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
        self.index_root = Path(os.getenv("INDEX_DIR", "/app/indexes"))
        self.sentence_dir = self.index_root / "sentence_window"
        self.automerge_dir = self.index_root / "automerging"

        # Optional GCS
        self.gcs_bucket = os.getenv("GCS_BUCKET")                  # e.g., agriguard-ac215-data (don't hard code bucket name to push to git)
        self.gcs_prefix = os.getenv("GCS_BASE_PREFIX", "RAG_pipeline")
        self.gcs = GCSStorageManager(self.gcs_bucket, self.gcs_prefix) if self.gcs_bucket else None

        # OpenAI (optional) + local embeddings (always)
        openai_key = os.getenv("OPENAI_API_KEY")
        self.llm = LIOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=openai_key) if openai_key else None
        self.embed = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

        # Worker components
        self.docproc = DocumentProcessor(data_dir=str(self.data_dir))
        self.chunker = ChunkingEngine(embed_model=self.embed, llm=self.llm)

        log.info("Ingestion Pipeline initialized")

    def ingest_one(self, url: str, filename: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict:
        """
        Run the complete ingestion flow for a single document URL.

        Returns:
            A dict with status, GCS URIs (if enabled), basic stats, and timing info.
        """
        meta = metadata or {}
        start = datetime.now()
        doc_id = sha12(url)

        result = {
            "id": doc_id,
            "url": url,
            "filename": filename,
            "metadata": meta,
            "gcs_uris": {},
            "status": "started",
            "started_at": start.isoformat()
        }

        try:
            # 1) Download
            log.info("=" * 70)
            log.info(f"INGESTING DOCUMENT\nURL: {url}")
            raw_path = self.docproc.download(url, filename)

            # Upload raw to GCS
            if self.gcs:
                result["gcs_uris"]["raw"] = self.gcs.upload_file(str(raw_path), "raw", raw_path.name)

            # 2) Parse
            docs = self.docproc.parse_to_documents(raw_path)
            if not docs:
                raise RuntimeError("Parser produced 0 documents (empty text).")

            # 3) Save stitched text for QA
            processed = self.docproc.save_processed_text(docs, raw_path.stem)
            if self.gcs:
                result["gcs_uris"]["processed"] = self.gcs.upload_file(str(processed), "processed", processed.name)

            # 4) Metadata JSON
            meta_out = {
                "doc_id": doc_id,
                "source_url": url,
                "filename": raw_path.name,
                "num_pages": len(docs),
                "total_chars": sum(len(d.text or "") for d in docs),
                "ingested_at": datetime.now().isoformat(),
                "custom": meta,
            }
            if self.gcs:
                result["gcs_uris"]["metadata"] = self.gcs.upload_json(meta_out, "metadata", f"{raw_path.stem}_metadata.json")

            # 5) Build Sentence-Window index (merge pages into one logical doc)
            merged = Document(text="\n\n".join([d.text or "" for d in docs]), metadata={"source_url": url})
            sentence_idx_dir = self.sentence_dir / raw_path.stem
            sent_index = self.chunker.sentence_window_index(merged, sentence_idx_dir)
            if self.gcs:
                result["gcs_uris"]["sentence_index"] = self.gcs.upload_directory(str(sentence_idx_dir), "indexes", f"sentence_window/{raw_path.stem}")

            # 6) Build Auto-Merging index
            automerge_idx_dir = self.automerge_dir / raw_path.stem
            merge_index = self.chunker.automerging_index(docs, automerge_idx_dir)
            if self.gcs:
                result["gcs_uris"]["automerge_index"] = self.gcs.upload_directory(str(automerge_idx_dir), "indexes", f"automerging/{raw_path.stem}")

            # 7) Done
            end = datetime.now()
            result.update({
                "status": "success",
                "duration_seconds": (end - start).total_seconds(),
                "sentence_nodes": count_nodes_safely(sent_index),
                "automerge_nodes": count_nodes_safely(merge_index),
            })

            log.info("-" * 70)
            log.info("INGESTION COMPLETE")
            log.info(f"Duration: {result['duration_seconds']:.1f}s")
            log.info(f"Sentence-Window nodes: {result['sentence_nodes']}")
            log.info(f"Auto-Merging nodes  : {result['automerge_nodes']}")
            return result

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            log.exception("INGESTION FAILED")
            return result


# ---------- Entrypoint ----------
def main():
    """
    Example run that ingests two representative sources:
      - ISU extension PDF
      - ISU crop page (HTML)

    Can replace/extend the list.
    """
    log.info("=" * 70)
    log.info("IOWA AGRONOMY RAG - INGESTION SERVICE")

    # Define seed docs here
    docs = [
        {
            "url": "https://www.extension.iastate.edu/agdm/crops/pdf/a1-14.pdf",
            "filename": "iowa-corn-profitability.pdf",
            "metadata": {
                "source_type": "extension_guide",
                "crop_focus": "corn",
                "state": "Iowa",
                "organization": "Iowa State Extension",
            },
        },
        {
            "url": "https://iowaagriculture.gov/news/crop-progress-report-Sept-29-2025",
            "filename": "corn.html",
            "metadata": {
                "source_type": "web_article",
                "crop_focus": "corn",
                "state": "Iowa",
                "organization": "Iowa State Extension",
            },
        },
    ]

    pipe = IngestionPipeline()
    results = []

    for d in docs:
        r = pipe.ingest_one(url=d["url"], filename=d.get("filename"), metadata=d.get("metadata"))
        results.append(r)

    # Upload a summary log if GCS is configured
    succ = [x for x in results if x["status"] == "success"]
    fail = [x for x in results if x["status"] == "failed"]

    summary = {
        "ingestion_date": datetime.now().isoformat(),
        "total_documents": len(results),
        "successful": len(succ),
        "failed": len(fail),
        "results": results,
    }

    if pipe.gcs:
        pipe.gcs.upload_json(summary, "logs", f"ingestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    log.info("=" * 70)
    log.info("INGESTION SERVICE COMPLETE")
    log.info(f"Total: {len(results)} | Success: {len(succ)} | Failed: {len(fail)}")


if __name__ == "__main__":
    main()