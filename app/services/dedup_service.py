# backend/app/services/dedup_service.py

import hashlib
import re
from typing import Optional

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.models.post import Post

# ── constants ──────────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.85   # tune this; 0.85 catches heavy paraphrasing
RECENT_POST_LIMIT    = 500    # only compare against the N most recent posts


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_hash(title: str, content: str) -> str:
    """SHA-256 of normalized title + content."""
    normalized = _normalize(title + " " + content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ── exact duplicate check ──────────────────────────────────────────────────

def is_exact_duplicate(db: Session, content_hash: str) -> bool:
    """Returns True if a post with this hash already exists."""
    return db.query(Post).filter(Post.content_hash == content_hash).first() is not None


# ── near-duplicate check ───────────────────────────────────────────────────

def _fetch_recent_texts(db: Session) -> list[tuple[int, str]]:
    """Return (post_id, combined_text) for the N most recent posts."""
    posts = (
        db.query(Post.id, Post.title, Post.content)
        .order_by(Post.created_at.desc())
        .limit(RECENT_POST_LIMIT)
        .all()
    )
    return [(p.id, _normalize(p.title + " " + p.content)) for p in posts]


def find_near_duplicate(
    db: Session,
    title: str,
    content: str,
    exclude_id: Optional[int] = None,
) -> Optional[int]:
    """
    Returns the post_id of the most similar existing post if similarity
    exceeds SIMILARITY_THRESHOLD, otherwise None.
    """
    recent = _fetch_recent_texts(db)
    if not recent:
        return None

    ids, texts = zip(*recent)

    # exclude the post itself (useful when re-checking after save)
    if exclude_id is not None:
        filtered = [(i, t) for i, t in zip(ids, texts) if i != exclude_id]
        if not filtered:
            return None
        ids, texts = zip(*filtered)

    candidate = _normalize(title + " " + content)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10_000)
    try:
        matrix = vectorizer.fit_transform(list(texts) + [candidate])
    except ValueError:
        return None  # empty vocabulary edge case

    # last row is our candidate
    candidate_vec = matrix[-1]
    existing_vecs = matrix[:-1]

    sims = cosine_similarity(candidate_vec, existing_vecs).flatten()
    best_idx = int(np.argmax(sims))
    best_score = float(sims[best_idx])

    if best_score >= SIMILARITY_THRESHOLD:
        return ids[best_idx]

    return None


# ── unified entry point ────────────────────────────────────────────────────

class DuplicateResult:
    def __init__(self, is_duplicate: bool, kind: Optional[str], duplicate_of: Optional[int]):
        self.is_duplicate   = is_duplicate
        self.kind           = kind           # "exact" | "near" | None
        self.duplicate_of   = duplicate_of   # post_id of the original


def check_duplicate(db: Session, title: str, content: str) -> DuplicateResult:
    """
    Full duplicate check. Call this before inserting a new post.
    Returns a DuplicateResult describing what was found.
    """
    h = compute_hash(title, content)

    if is_exact_duplicate(db, h):
        return DuplicateResult(is_duplicate=True, kind="exact", duplicate_of=None)

    dup_id = find_near_duplicate(db, title, content)
    if dup_id is not None:
        return DuplicateResult(is_duplicate=True, kind="near", duplicate_of=dup_id)

    return DuplicateResult(is_duplicate=False, kind=None, duplicate_of=None)