"""Auditable local hybrid retrieval: TF-IDF cosine + lexical coverage, no opaque model."""

import hashlib
import json
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from enterprise.config import DOCUMENTS, INDEX

INJECTION = re.compile(
    r"ignore (?:all |previous |prior )*instructions|system prompt|reveal.*secret|execute.*command|<script",
    re.IGNORECASE,
)


def extract(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Missing metadata: {path.name}")
    _, header, content = text.split("---", 2)
    metadata = dict(line.split(": ", 1) for line in header.strip().splitlines())
    for required in ("id", "title", "asset_type", "revision"):
        if not metadata.get(required):
            raise ValueError(f"Missing {required}: {path.name}")
    return metadata, content.strip()


def ingest(source=DOCUMENTS, target=INDEX):
    chunks = []
    paths = sorted(Path(source).glob("*.md"))
    if not paths:
        raise ValueError("No readable Markdown corpus found; check DOCUMENT_PATH and permissions")
    for path in paths:
        metadata, text = extract(path)
        # Paragraph-aware, 160-word windows with 30-word overlap for long paragraphs.
        for paragraph, block in enumerate(text.split("\n\n")):
            words = block.split()
            for offset in range(0, len(words), 130):
                content = " ".join(words[offset : offset + 160])
                if not content or INJECTION.search(content):
                    continue  # Quarantine instruction-like content; never execute retrieved text.
                chunks.append(
                    {
                        **metadata,
                        "file": path.name,
                        "paragraph": paragraph + 1,
                        "chunk_id": f"{metadata['id']}:{paragraph + 1}:{offset}",
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "text": content,
                    }
                )
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_text(json.dumps(chunks, indent=2))
    return chunks


class Retrieval:
    def __init__(self, chunks):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in chunks]) if chunks else None

    def search(self, query, asset_type=None, top_k=3, threshold=0.09):
        if self.matrix is None or not query.strip():
            return []
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        terms = set(re.findall(r"\w+", query.lower()))
        results = []
        for chunk, cosine in zip(self.chunks, scores):
            if asset_type and chunk["asset_type"] not in (asset_type, "all"):
                continue
            if INJECTION.search(chunk["text"]):
                continue
            coverage = len(terms & set(re.findall(r"\w+", chunk["text"].lower()))) / max(
                1, len(terms)
            )
            score = 0.85 * float(cosine) + 0.15 * coverage
            if score >= threshold:
                results.append(
                    {**chunk, "score": round(score, 4), "citation": f"[{chunk['chunk_id']}]"}
                )
        return sorted(results, key=lambda r: r["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    print(f"Indexed {len(ingest())} chunks at {INDEX}")
