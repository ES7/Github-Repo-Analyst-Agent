import os
import shutil
import tempfile
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from git import Repo, GitCommandError

# Using a lightweight local embedding model — no API key needed
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# File extensions we care about — skip binaries, lock files, etc.
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".env.example"
}

# Skip these folders entirely
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "coverage"
}

MAX_CHUNK_CHARS = 1000   # characters per chunk
MAX_FILES = 100          # max files to index (keep it fast)
MAX_RESULTS = 5          # results per search query


class CodebaseRAG:
    """
    Handles cloning, indexing, and searching a GitHub repo's codebase.
    One instance per analysis session — cleaned up after use.
    """

    def __init__(self):
        self._temp_dir: Optional[str] = None
        self._chroma_client = None
        self._collection = None
        self._ready = False
        self._repo_url: Optional[str] = None

    def setup(self, repo_url: str) -> dict:
        """
        Clone the repo and index all code files into ChromaDB.
        Call this once before any search_codebase() calls.
        """
        try:
            self._repo_url = repo_url
            self._temp_dir = tempfile.mkdtemp(prefix="github_analyst_")

            # ── Step 1: Clone the repo ────────────────────────────
            print(f"[RAG] Cloning {repo_url}...")
            Repo.clone_from(repo_url, self._temp_dir, depth=1)  # shallow clone = faster

            # ── Step 2: Collect all code files ───────────────────
            chunks = []
            metadatas = []
            ids = []
            chunk_id = 0

            for root, dirs, files in os.walk(self._temp_dir):
                # Skip unwanted directories in-place
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

                for filename in files:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in CODE_EXTENSIONS:
                        continue

                    filepath = os.path.join(root, filename)
                    relative_path = os.path.relpath(filepath, self._temp_dir)

                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    except Exception:
                        continue

                    if not content.strip():
                        continue

                    # ── Step 3: Chunk the file ────────────────────
                    file_chunks = _chunk_text(content, MAX_CHUNK_CHARS)

                    for i, chunk in enumerate(file_chunks):
                        chunks.append(chunk)
                        metadatas.append({
                            "file": relative_path,
                            "chunk_index": i,
                            "total_chunks": len(file_chunks),
                        })
                        ids.append(f"chunk_{chunk_id}")
                        chunk_id += 1

                    if chunk_id >= MAX_FILES * 10:  # rough cap
                        break

            if not chunks:
                return {"error": "No code files found in repo."}

            # ── Step 4: Embed and store in ChromaDB ──────────────
            print(f"[RAG] Indexing {len(chunks)} chunks from {self._temp_dir}...")

            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )

            self._chroma_client = chromadb.Client()
            self._collection = self._chroma_client.create_collection(
                name="codebase",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )

            # Add in batches of 50 to avoid memory issues
            batch_size = 50
            for i in range(0, len(chunks), batch_size):
                self._collection.add(
                    documents=chunks[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size],
                    ids=ids[i:i+batch_size],
                )

            self._ready = True
            print(f"[RAG] Ready. Indexed {len(chunks)} chunks.")

            return {
                "success": True,
                "chunks_indexed": len(chunks),
                "message": f"Codebase indexed. {len(chunks)} chunks ready to search."
            }

        except GitCommandError as e:
            return {"error": f"Could not clone repo: {str(e)}"}
        except Exception as e:
            return {"error": f"RAG setup failed: {str(e)}"}

    def search(self, query: str) -> dict:
        """
        Semantic search over the indexed codebase.
        Returns the most relevant code chunks for the query.
        """
        if not self._ready:
            return {"error": "RAG not initialized. Call setup() first."}

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(MAX_RESULTS, self._collection.count()),
            )

            hits = []
            for i, doc in enumerate(results["documents"][0]):
                hits.append({
                    "file": results["metadatas"][0][i]["file"],
                    "content": doc,
                    "chunk": results["metadatas"][0][i]["chunk_index"],
                })

            return {
                "query": query,
                "results": hits,
                "total_chunks_searched": self._collection.count(),
            }

        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}

    def cleanup(self):
        """Delete the cloned repo from disk."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            print(f"[RAG] Cleaned up {self._temp_dir}")
        self._ready = False


def _chunk_text(text: str, max_chars: int) -> list[str]:
    """
    Split text into chunks of max_chars.
    Tries to split on newlines to keep code context intact.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks


# ── Singleton instance ────────────────────────────────────────────────────────
# One RAG instance per app session — reset between analyses
_rag_instance: Optional[CodebaseRAG] = None


def get_rag() -> CodebaseRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = CodebaseRAG()
    return _rag_instance


def reset_rag():
    """Call this between analyses to clean up the previous repo."""
    global _rag_instance
    if _rag_instance:
        _rag_instance.cleanup()
    _rag_instance = CodebaseRAG()