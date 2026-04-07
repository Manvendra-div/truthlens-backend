import hashlib
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from fastapi.concurrency import run_in_threadpool

from app.models.post import Post


SIMILARITY_THRESHOLD = 0.85
RECENT_POST_LIMIT = 500


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_hash(title: str, content: str) -> str:
    normalized = _normalize(title + " " + content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ───────────────────────────────────────────────────────────────
# ✅ EXACT DUPLICATE (async DB)
# ───────────────────────────────────────────────────────────────

async def is_exact_duplicate(db: AsyncSession, content_hash: str) -> bool:
    result = await db.execute(
        select(Post.id).where(Post.content_hash == content_hash)
    )
    return result.scalar_one_or_none() is not None


# ───────────────────────────────────────────────────────────────
# ✅ FETCH POSTS (async DB)
# ───────────────────────────────────────────────────────────────

async def _fetch_recent_texts(db: AsyncSession) -> list[tuple[int, str]]:
    result = await db.execute(
        select(Post.id, Post.title, Post.content)
        .order_by(Post.created_at.desc())
        .limit(RECENT_POST_LIMIT)
    )

    posts = result.all()
    return [(p.id, _normalize(p.title + " " + p.content)) for p in posts]


# ───────────────────────────────────────────────────────────────
# ⚠️ CPU HEAVY PART → THREADPOOL
# ───────────────────────────────────────────────────────────────

def _compute_similarity(texts, candidate, ids, exclude_id):
    if exclude_id is not None:
        filtered = [(i, t) for i, t in zip(ids, texts) if i != exclude_id]
        if not filtered:
            return None
        ids, texts = zip(*filtered)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10_000)

    try:
        matrix = vectorizer.fit_transform(list(texts) + [candidate])
    except ValueError:
        return None

    candidate_vec = matrix[-1]
    existing_vecs = matrix[:-1]

    sims = cosine_similarity(candidate_vec, existing_vecs).flatten()
    best_idx = int(np.argmax(sims))
    best_score = float(sims[best_idx])

    if best_score >= SIMILARITY_THRESHOLD:
        return ids[best_idx]

    return None


# ───────────────────────────────────────────────────────────────
# ✅ NEAR DUPLICATE (async-safe)
# ───────────────────────────────────────────────────────────────

async def find_near_duplicate(
    db: AsyncSession,
    title: str,
    content: str,
    exclude_id: Optional[int] = None,
) -> Optional[int]:

    recent = await _fetch_recent_texts(db)
    if not recent:
        return None

    ids, texts = zip(*recent)
    candidate = _normalize(title + " " + content)

    # ⚠️ offload CPU work
    return await run_in_threadpool(
        _compute_similarity,
        texts,
        candidate,
        ids,
        exclude_id
    )


# ───────────────────────────────────────────────────────────────
# RESULT CLASS
# ───────────────────────────────────────────────────────────────

class DuplicateResult:
    def __init__(self, is_duplicate: bool, kind: Optional[str], duplicate_of: Optional[int]):
        self.is_duplicate = is_duplicate
        self.kind = kind
        self.duplicate_of = duplicate_of


# ───────────────────────────────────────────────────────────────
# ✅ MAIN ENTRY (async)
# ───────────────────────────────────────────────────────────────

async def check_duplicate(
    db: AsyncSession,
    title: str,
    content: str
) -> DuplicateResult:

    h = compute_hash(title, content)

    if await is_exact_duplicate(db, h):
        return DuplicateResult(True, "exact", None)

    dup_id = await find_near_duplicate(db, title, content)

    if dup_id is not None:
        return DuplicateResult(True, "near", dup_id)

    return DuplicateResult(False, None, None)