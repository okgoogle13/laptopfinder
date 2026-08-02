from laptopfinder.qna_filter import build_fact_view, filter_questions, question_is_already_answered


def _listing(**overrides):
    base = {
        "description_text": "",
        "aspects": {},
        "returns_accepted": None,
    }
    base.update(overrides)
    return base


# --- build_fact_view ---

def test_build_fact_view_detects_condition_from_description():
    listing = _listing(description_text="Like New Condition. Original Package. All accessories like new.")
    facts = build_fact_view(listing)
    assert facts["condition"] is True
    assert facts["accessories"] is True


def test_build_fact_view_detects_returns_from_return_terms():
    listing = _listing(returns_accepted=False)
    facts = build_fact_view(listing)
    assert facts["returns"] is True


def test_build_fact_view_all_false_when_nothing_present():
    listing = _listing()
    facts = build_fact_view(listing)
    assert not any(facts.values())


# --- question_is_already_answered ---

def test_question_already_answered_when_domain_covered():
    facts = {"condition": True, "warranty": False, "accessories": False, "returns": False}
    assert question_is_already_answered("What's the cosmetic condition?", facts) is True


def test_question_not_answered_when_domain_not_covered():
    facts = {"condition": False, "warranty": False, "accessories": False, "returns": False}
    assert question_is_already_answered("What's the cosmetic condition?", facts) is False


# --- filter_questions ---

def test_filter_questions_drops_answered_keeps_unanswered():
    listing = _listing(description_text="Like New Condition. Original Package. All accessories like new.")
    questions = [
        "What's the cosmetic condition?",
        "Are the charger and box included?",
        "Would you consider a lower offer?",
    ]
    result = filter_questions(questions, listing)
    assert result == ["Would you consider a lower offer?"]
