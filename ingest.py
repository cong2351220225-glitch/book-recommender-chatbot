"""Load books, create Gemini embeddings, and persist them in ChromaDB."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import chromadb
import pandas as pd
from dotenv import load_dotenv
from google import genai

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "books.csv"
CHROMA_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "books_collection"
EMBEDDING_MODEL = "gemini-embedding-2"
REQUIRED_COLUMNS = {"title", "author", "genre", "description", "year"}
OPTIONAL_DEFAULTS: dict[str, Any] = {
    "book_id": "", "author_id": "", "summary": "", "tags": "", "target_audience": "",
    "mood": "", "difficulty": "", "language": "", "rating": 0.0, "featured": False,
}
MAX_RETRIES = 3

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def get_api_key() -> str:
    """Return the configured Gemini API key or raise a helpful error."""
    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add your key to the .env file "
            "before running ingestion."
        )
    return api_key


def load_books(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the book CSV and validate its required columns and values."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    try:
        books = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read CSV dataset: {error}") from error
    if books.empty:
        raise ValueError("The CSV dataset is empty.")

    missing_columns = sorted(REQUIRED_COLUMNS - set(books.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    for column, default in OPTIONAL_DEFAULTS.items():
        if column not in books.columns:
            books[column] = default
    books = books.copy()
    for column in ("title", "author", "genre", "description"):
        books[column] = books[column].fillna("").astype(str).str.strip()
        if books[column].eq("").any():
            raise ValueError(f"Column '{column}' contains an empty value.")

    numeric_year = pd.to_numeric(books["year"], errors="coerce")
    if numeric_year.isna().any() or (numeric_year % 1 != 0).any():
        raise ValueError("Column 'year' must contain valid integer years.")
    books["year"] = numeric_year.astype(int)
    books["rating"] = pd.to_numeric(books["rating"], errors="coerce").fillna(0.0).astype(float)
    books["featured"] = books["featured"].astype(str).str.lower().isin(("true", "1", "yes", "co", "có"))
    books["book_id"] = books["book_id"].where(books["book_id"].astype(str).str.strip() != "", "")
    books.loc[books["book_id"] == "", "book_id"] = [f"book_{index:03d}" for index in range(1, len(books) + 1) if books.loc[index - 1, "book_id"] == ""]
    books["book_id"] = books["book_id"].astype(str)
    if books["book_id"].duplicated().any():
        raise ValueError("Column 'book_id' must contain unique values.")
    if books["title"].duplicated().any():
        duplicates = sorted(books.loc[books["title"].duplicated(), "title"].unique())
        raise ValueError(f"Duplicate book titles are not allowed: {', '.join(duplicates)}")
    return books.reset_index(drop=True)


def build_book_document(book: pd.Series) -> str:
    """Build the semantic document embedded for one book."""
    return (
        f"Title: {book['title']}\n"
        f"Author: {book['author']}\n"
        f"Genre: {book['genre']}\n"
        f"Publication year: {int(book['year'])}\n"
        f"Tags: {book.get('tags', '')}\n"
        f"Target audience: {book.get('target_audience', '')}\n"
        f"Mood: {book.get('mood', '')}\n"
        f"Difficulty: {book.get('difficulty', '')}\n"
        f"Summary: {book.get('summary', '')}\n"
        f"Description: {book['description']}"
    )


def _extract_embedding(response: Any) -> list[float]:
    embeddings = getattr(response, "embeddings", None)
    if not embeddings:
        raise ValueError("Gemini returned no embedding.")
    values = getattr(embeddings[0], "values", None)
    if not values:
        raise ValueError("Gemini returned an empty embedding vector.")
    vector = [float(value) for value in values]
    if not vector:
        raise ValueError("Gemini returned an invalid embedding vector.")
    return vector


def generate_document_embedding(
    client: genai.Client,
    text: str,
    title: str = "none",
) -> list[float]:
    """Generate one Gemini Embedding 2 document vector with bounded retries."""
    if not text or not text.strip():
        raise ValueError("Cannot embed an empty document.")
    embedding_document = f"title: {title.strip() or 'none'} | text: {text.strip()}"
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=embedding_document,
            )
            return _extract_embedding(response)
        except Exception as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)
    raise RuntimeError(f"Unable to generate document embedding after {MAX_RETRIES} attempts.") from last_error


def create_chroma_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    """Create or replace the collection configured for cosine distance."""
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except (ValueError, Exception) as error:
        if not isinstance(error, ValueError) and "does not exist" not in str(error).lower():
            LOGGER.debug("Existing collection could not be deleted: %s", error)
    return client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def ingest_books(books: pd.DataFrame, gemini_client: genai.Client) -> int:
    """Embed all books, then replace the persisted collection in one batch."""
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, str | int]] = []
    ids: list[str] = []

    LOGGER.info("Embedding %d books:", len(books))
    for index, (_, book) in enumerate(books.iterrows(), start=1):
        title = str(book["title"])
        LOGGER.info("[%d/%d] %s", index, len(books), title)
        documents.append(build_book_document(book))
        embeddings.append(generate_document_embedding(gemini_client, documents[-1], title))
        metadatas.append(
            {
                "title": title,
                "author": str(book["author"]),
                "genre": str(book["genre"]),
                "year": int(book["year"]),
                "book_id": str(book["book_id"]),
                "author_id": str(book.get("author_id", "")),
                "tags": str(book.get("tags", "")),
                "target_audience": str(book.get("target_audience", "")),
                "mood": str(book.get("mood", "")),
                "difficulty": str(book.get("difficulty", "")),
                "rating": float(book.get("rating", 0.0)),
                "featured": bool(book.get("featured", False)),
            }
        )
        ids.append(str(book["book_id"]))

    if len(documents) != len(embeddings):
        raise RuntimeError("Document and embedding counts do not match.")
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = create_chroma_collection(chroma_client)
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return collection.count()


def main() -> None:
    """Run the complete CSV-to-Chroma ingestion pipeline."""
    print("=" * 50)
    print("BOOK RAG INGESTION")
    print("=" * 50)
    print("Loading and validating dataset...")
    books = load_books()
    print(f"Found {len(books)} books.")
    print("Initializing Gemini...")
    gemini_client = genai.Client(api_key=get_api_key())
    print("Embedding and saving vectors...")
    indexed_count = ingest_books(books, gemini_client)
    print("=" * 50)
    print(f"INGESTION COMPLETED | Books indexed: {indexed_count}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Database: {CHROMA_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    main()
