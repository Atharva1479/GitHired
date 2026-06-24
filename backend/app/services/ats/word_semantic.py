import logging
import re
import threading
from typing import Any

_wv: Any = None
_MODEL_NAME = "word2vec-google-news-300"
_lock = threading.Lock()
log = logging.getLogger("ats.word_semantic")


def get_vectors() -> Any:
    global _wv
    if _wv is not None:
        return _wv
    with _lock:
        # Double-checked: another thread may have loaded it while we waited
        if _wv is not None:
            return _wv
        try:
            import gensim.downloader as api
            _wv = api.load(_MODEL_NAME)
            log.info("word_semantic: model loaded — %s", _MODEL_NAME)
        except Exception as e:
            err = str(e)
            # WinError 183: two concurrent callers raced to rename the _tmp dir.
            # The model directory already exists — load directly from it.
            if "183" in err or "already exists" in err:
                try:
                    import os
                    from gensim.models import KeyedVectors
                    path = os.path.join(
                        os.path.expanduser("~"),
                        "gensim-data",
                        _MODEL_NAME,
                        f"{_MODEL_NAME}.gz",
                    )
                    _wv = KeyedVectors.load_word2vec_format(path, binary=True)
                    log.info("word_semantic: model loaded from cache — %s", _MODEL_NAME)
                except Exception as e2:
                    log.warning("word_semantic: cache load failed — %s", str(e2))
            else:
                log.warning("word_semantic: model unavailable — %s", err)
    return _wv


def unload() -> None:
    """Release the 1.7 GB word2vec model from memory. Call on worker shutdown."""
    global _wv
    with _lock:
        _wv = None
    log.info("word_semantic: model unloaded")


def word_similarity_score(jd_keywords: list[str], resume_parsed: dict) -> dict:
    wv = get_vectors()
    if wv is None:
        return {"score": 65.0, "semantic_matches": [], "fallback": True}

    resume_full = " ".join(str(v) for v in resume_parsed.values()).lower()
    resume_words = set(re.findall(r'\b[a-z]{3,}\b', resume_full))

    semantic_matches: list[dict] = []
    matched_count = 0.0

    for kw in jd_keywords:
        kw_lower = kw.lower()
        if kw_lower in resume_full:
            matched_count += 1.0
            continue

        candidates = [
            kw_lower.replace(" ", "_"),
            kw_lower.replace(" ", ""),
            kw_lower.split()[-1] if " " in kw_lower else None,
        ]
        kw_token = next((c for c in candidates if c and c in wv), None)
        if kw_token is None:
            continue

        try:
            similar = wv.most_similar(kw_token, topn=20)
        except Exception:
            continue

        for sim_word, sim_score in similar:
            if sim_score < 0.70:
                break
            if sim_word in resume_words:
                semantic_matches.append(
                    {
                        "jd_term": kw,
                        "resume_term": sim_word,
                        "similarity": round(sim_score * 100, 1),
                    }
                )
                matched_count += 0.80
                break

    total = len(jd_keywords)
    score = round(min((matched_count / total) * 100, 100), 1) if total > 0 else 50.0
    return {"score": score, "semantic_matches": semantic_matches, "fallback": False}
