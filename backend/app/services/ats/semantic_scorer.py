import re
from typing import Any

import structlog

_model: Any = None
_MODEL_NAME = "all-MiniLM-L6-v2"
log = structlog.get_logger("ats.semantic")


def get_model() -> Any:
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(_MODEL_NAME)
            log.info("semantic_scorer.model_loaded", model=_MODEL_NAME)
        except Exception as e:
            log.warning("semantic_scorer.model_unavailable", error=str(e))
    return _model


def _split_sentences(text: str, max_len: int = 60) -> list[str]:
    parts = re.split(r'[.\n•\-\*]', text)
    return [p.strip() for p in parts if len(p.strip()) >= 15][:max_len]


def semantic_sentence_score(jd_parsed: dict, resume_parsed: dict) -> dict:
    model = get_model()
    if model is None:
        return {"score": 65.0, "top_matches": [], "fallback": True}

    jd_text = (
        jd_parsed.get("required_text", "") + " " + jd_parsed.get("preferred_text", "")
    )
    resume_text = (
        resume_parsed.get("experience", "")
        + " "
        + resume_parsed.get("summary", "")
        + " "
        + resume_parsed.get("projects", "")
    )

    jd_sents = _split_sentences(jd_text, 50)
    resume_sents = _split_sentences(resume_text, 80)

    if not jd_sents or not resume_sents:
        return {"score": 65.0, "top_matches": [], "fallback": True}

    try:
        from sentence_transformers import util

        jd_emb = model.encode(jd_sents, convert_to_tensor=True, show_progress_bar=False)
        res_emb = model.encode(
            resume_sents, convert_to_tensor=True, show_progress_bar=False
        )
        cos_scores = util.cos_sim(jd_emb, res_emb)

        per_sentence_max = cos_scores.max(dim=1).values
        avg_sim = float(per_sentence_max.mean())

        top_matches: list[dict] = []
        for i, jd_s in enumerate(jd_sents):
            sim = float(per_sentence_max[i])
            if sim >= 0.50:
                best_idx = int(cos_scores[i].argmax())
                top_matches.append(
                    {
                        "jd": jd_s[:120],
                        "resume": resume_sents[best_idx][:120],
                        "similarity": round(sim * 100, 1),
                    }
                )
        top_matches.sort(key=lambda x: x["similarity"], reverse=True)

        score = round(min((avg_sim / 0.65) * 100, 100), 1)
        return {"score": score, "top_matches": top_matches[:6], "fallback": False}
    except Exception as e:
        log.warning("semantic_scorer.inference_error", error=str(e))
        return {"score": 65.0, "top_matches": [], "fallback": True}
