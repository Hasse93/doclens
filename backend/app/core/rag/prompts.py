"""Prompt templates.

Mode-specific behaviour lives here. The retrieval pipeline is identical across
modes; only these strings and the extraction schema change.
"""

RESEARCH_SYSTEM = (
    "You are a precise research assistant. Answer strictly from the provided "
    "context passages. When you use information from a passage, cite it inline "
    "with its marker, for example [1] or [2]. If the answer is not contained in "
    "the context, say so plainly instead of guessing."
)


def build_qa_prompt(question: str, passages: list[str]) -> str:
    context = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(passages))
    return (
        f"Context passages:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the context above and cite the passages you rely on."
    )


SUMMARY_SYSTEM = (
    "You are a research assistant who writes clear, faithful summaries of "
    "academic documents without adding outside information."
)


def build_summary_prompt(text: str) -> str:
    return (
        "Summarise the following document in 4-6 sentences. Cover the goal, the "
        "method, and the main findings.\n\n"
        f"{text}"
    )


EXTRACTION_SYSTEM = (
    "You extract structured metadata from academic documents. Respond with a "
    "single JSON object and nothing else."
)


def build_extraction_prompt(text: str) -> str:
    return (
        "From the document below, extract these fields as JSON: "
        '"title", "authors" (array of strings), "methodology", "dataset", '
        '"key_findings" (array of strings), "limitations". Use null or an empty '
        "array when a field is not stated. Do not invent information.\n\n"
        f"{text}"
    )


# --- Recruitment mode --------------------------------------------------------

RECRUITMENT_EXTRACTION_SYSTEM = (
    "You extract structured fields from a candidate's résumé. Respond with a "
    "single JSON object and nothing else."
)


def build_recruitment_extraction_prompt(text: str) -> str:
    return (
        "From the résumé below, extract these fields as JSON: "
        '"name", "email", "current_title", "skills" (array of strings), '
        '"years_experience" (number), "education" (array of strings). Use null or '
        "an empty array when a field is not stated. Do not invent information.\n\n"
        f"{text}"
    )


MATCH_SYSTEM = (
    "You are an experienced technical recruiter. You evaluate a candidate "
    "objectively against a job description and return a single strict JSON "
    "object. Judge only from the texts provided; never invent qualifications."
)


def build_match_prompt(job_text: str, resume_text: str) -> str:
    return (
        f"Job description:\n{job_text}\n\n"
        f"Candidate résumé:\n{resume_text}\n\n"
        "Assess how well the candidate fits the role. Respond with a single JSON "
        'object with these keys: "overall_score" (integer 0-100), '
        '"matched_skills" (array of requirements the candidate clearly meets), '
        '"missing_skills" (array of requirements the candidate appears to lack), '
        '"summary" (2-3 sentences explaining the fit and any gaps).'
    )
