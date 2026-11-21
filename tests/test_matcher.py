from app.services.matcher import extract_skills, match_resume_to_job


def test_matcher_detects_shared_and_missing_skills():
    result = match_resume_to_job(
        "Python FastAPI SQL Git Docker",
        "Looking for Python, FastAPI, SQL and AWS experience.",
    )
    assert "python" in result["matched_skills"]
    assert "aws" in result["missing_skills"]
    assert result["skill_match_score"] > 0


def test_skill_regex_matches_words_and_phrases():
    skills = extract_skills("Customer service, IT support, troubleshooting and documentation.")
    assert {"customer service", "technical support", "troubleshooting", "documentation"} <= set(skills)


def test_skill_matching_is_case_insensitive_and_not_substring_based():
    skills = extract_skills("PYTHON and SQL are used. The word flask appears.")
    assert {"python", "sql", "flask"} <= set(skills)
    assert "git" not in extract_skills("digital skills are useful")


def test_sentence_evidence_splits_on_newlines():
    result = match_resume_to_job(
        "Resolved customer support tickets.\nDocumented troubleshooting steps.",
        "Customer support and troubleshooting documentation required.",
    )
    assert result["retrieved_resume_evidence"]
    assert result["matched_skills"]


def test_empty_inputs_are_rejected():
    try:
        match_resume_to_job("", "Python required")
        assert False, "Expected ValueError"
    except ValueError:
        pass
