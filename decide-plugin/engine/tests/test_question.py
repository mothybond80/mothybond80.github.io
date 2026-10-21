"""Framing resistance of the deterministic layer.

For each subject, every framing (positive, negative, leading, neutral) must
produce the same framing_hash, the same PICO concepts and therefore the same
search strategy. The asker's direction must be recorded separately.
"""
import json

import pytest

from decide_engine.question import parse_question, search_strategy

SUBJECTS = {
    "creatine": {
        "framings": [
            ("Does creatine improve cognitive performance?", "benefit"),
            ("Does creatine fail to improve cognition?", "harm"),
            ("Isn't creatine actually great for brain function?", "benefit"),
            ("What is the effect of creatine on cognitive performance?", "neutral"),
        ],
        "exposure": "creatine supplementation", "outcome": "cognitive performance",
    },
    "red_meat": {
        "framings": [
            ("Does red meat increase lifespan?", "benefit"),
            ("Does red meat reduce lifespan?", "harm"),
            ("Isn't red meat actually good for longevity?", "benefit"),
            ("Does red meat increase mortality?", "harm"),
        ],
        "exposure": "red meat consumption", "outcome": "longevity mortality",
    },
    "extraversion": {
        "framings": [
            ("Are extraverted men more romantically attractive?", None),
            ("Are extraverted men less attractive to women?", None),
            ("Surely extroverted men are more attractive, right?", None),
        ],
        "exposure": "extraversion", "outcome": "romantic attractiveness",
    },
    "income": {
        "framings": [
            ("Does additional income increase happiness?", "benefit"),
            ("Does more money fail to make people happier?", "harm"),
            ("Isn't it true that income doesn't really affect happiness?", None),
        ],
        "exposure": "income", "outcome": "subjective well-being happiness",
    },
    "cold_plunge": {
        "framings": [
            ("Do cold plunges improve ADHD symptoms?", "benefit"),
            ("Do cold plunges worsen ADHD symptoms?", "harm"),
            ("Are ice baths useless for ADHD?", None),
        ],
        "exposure": "cold water immersion", "outcome": "adhd symptoms",
    },
    "flow_headset": {
        "framings": [
            ("Does the Flow Neuroscience headset effectively treat depression?", "benefit"),
            ("Is the Flow Neuroscience headset ineffective for depression?", None),
            ("Isn't the Flow headset actually a good treatment for depression?", "benefit"),
        ],
        "exposure": "flow neuroscience tdcs headset", "outcome": "depression",
    },
    "diet_adhd": {
        "framings": [
            ("Can dietary interventions improve adult ADHD?", "benefit"),
            ("Do diet changes fail to help adult ADHD?", "harm"),
            ("Surely diet can't really affect ADHD in adults?", None),
        ],
        "exposure": "dietary intervention", "outcome": "adhd symptoms",
    },
}


@pytest.mark.parametrize("subject", sorted(SUBJECTS))
def test_framings_share_hash_and_strategy(subject):
    spec = SUBJECTS[subject]
    parsed = [parse_question(q) for q, _ in spec["framings"]]
    hashes = {p.framing_hash for p in parsed}
    assert len(hashes) == 1, [(p.raw, p.exposure, p.outcome, p.population) for p in parsed]
    strategies = {json.dumps(search_strategy(p), sort_keys=True) for p in parsed}
    assert len(strategies) == 1
    assert parsed[0].exposure == spec["exposure"]
    assert parsed[0].outcome == spec["outcome"]


@pytest.mark.parametrize("subject", sorted(SUBJECTS))
def test_asker_direction_is_recorded_but_absent_from_strategy(subject):
    for q, expected in SUBJECTS[subject]["framings"]:
        p = parse_question(q)
        if expected is not None:
            assert p.asker_direction == expected, (q, p.asker_direction)
        strat = json.dumps(search_strategy(p)).lower()
        for leak in ("improve", "worsen", "good for", "bad for", "useless", "ineffective", "fail", "increase", "reduce"):
            assert leak not in strat, (q, leak)


def test_neutral_question_has_no_direction_words():
    for spec in SUBJECTS.values():
        for q, _ in spec["framings"]:
            n = parse_question(q).neutral_question.lower()
            assert "which direction" in n
            for w in ("improve", "worsen", "good", "bad", "useless", "fail"):
                assert w not in n


def test_unparseable_question_degrades_gracefully():
    p = parse_question("thoughts on magnesium?")
    assert p.exposure
    assert any("could not split" in n for n in p.notes)
    assert search_strategy(p)["pubmed"]["reviews"]
