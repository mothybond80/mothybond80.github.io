"""Framing-blind question handling.

The user's wording is treated as a hypothesis, never as a search string. This
module:

  1. strips leading / rhetorical framing ("isn't it true that", "surely",
     "actually", "really", "don't you think");
  2. detects the direction the asker is pushing (benefit / harm / none) and
     records it as metadata so the appraisal stage can see what the asker
     expected WITHOUT the expectation shaping the search;
  3. extracts candidate concepts (exposure / intervention and outcome) with a
     small, inspectable heuristic;
  4. produces a neutral research question of the form
        "What is the effect of <exposure> on <outcome> in <population>?"
     and a canonical, direction-free search strategy.

The heuristic is deliberately simple and transparent. The calling LLM is
instructed to review and, if necessary, correct the PICO fields - but the
`framing_hash` is computed from the *direction-free* concept set, so two
oppositely framed questions about the same thing hash identically. The test
suite asserts exactly that.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field

# Words that carry the asker's expectation. They are removed from the concept
# text and recorded as `asker_direction`.
BENEFIT_WORDS = {
    "improve", "improves", "improved", "improving", "improvement", "boost", "boosts", "enhance", "enhances",
    "increase", "increases", "increased", "raise", "raises", "help", "helps", "benefit", "benefits", "beneficial",
    "good", "better", "best", "effective", "effectively", "treat", "treats", "cure", "cures", "prevent", "prevents",
    "protect", "protects", "protective", "extend", "extends", "longer", "healthy", "healthier", "safe", "safely",
    "work", "works", "relieve", "relieves", "great", "excellent", "wonderful", "amazing", "useful", "helpful", "worthwhile",
}
HARM_WORDS = {
    "reduce", "reduces", "reduced", "lower", "lowers", "decrease", "decreases", "shorten", "shortens", "worsen",
    "worsens", "harm", "harms", "harmful", "bad", "worse", "worst", "damage", "damages", "dangerous", "danger",
    "risk", "risky", "kill", "kills", "cause", "causes", "toxic", "unsafe", "ineffective", "useless", "terrible", "awful", "pointless",
}
# Outcome nouns where "reduce" is actually the beneficial direction (symptoms, risk, mortality...)
NEGATIVE_OUTCOMES = {"symptom", "symptoms", "mortality", "death", "deaths", "risk", "anxiety", "depression", "pain",
                     "inflammation", "disease", "cancer", "stroke", "infection", "adhd", "fatigue", "stress", "weight", "obesity"}

RHETORIC_PATTERNS = [
    r"^\s*(isn'?t|aren'?t|doesn'?t|don'?t|wasn'?t|won'?t|couldn'?t|shouldn'?t)\s+(it\s+|that\s+)?(true\s+that\s+|the case that\s+)?",
    r"^\s*(surely|obviously|clearly|everyone knows|it'?s well known that|i (?:think|believe|heard|read) (?:that\s+)?)",
    r"\b(actually|really|truly|honestly|in fact|after all|just|simply)\b",
    r"\b(isn'?t it|right\??|don'?t you think\??|or not\??|though)\s*$",
    r"^\s*(so|but|and)\s+",
]

QUESTION_LEAD = r"^\s*(does|do|is|are|can|could|will|would|should|did|has|have|was|were|might|may)\s+"
NEGATION = r"\b(fail(?:s|ed)? to|doesn'?t|don'?t|can'?t|cannot|won'?t|didn'?t|isn'?t|aren'?t|not|no longer|never)\s+"

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "medicine": ["treat", "therapy", "treatment", "drug", "medication", "patients", "disease", "depression", "adhd",
                 "diabetes", "cancer", "blood pressure", "clinical", "surgery", "dental", "caries", "periodont", "mortality",
                 "headset", "device", "stimulation", "tdcs", "vaccine", "symptom"],
    "nutrition": ["diet", "dietary", "meat", "food", "eat", "eating", "intake", "nutrition", "supplement", "creatine",
                  "protein", "vitamin", "sugar", "fasting", "calorie", "longevity", "lifespan"],
    "psychology": ["attractive", "attraction", "personality", "extravert", "extrovert", "introvert", "cognitive", "cognition",
                   "memory", "happiness", "well-being", "wellbeing", "mood", "behaviour", "behavior", "motivation", "romantic"],
    "economics": ["income", "wealth", "money", "gdp", "tax", "price", "wage", "unemployment", "inflation", "spend"],
    "social_science": ["education", "crime", "policy", "culture", "society", "social", "school", "voting", "inequality"],
    "exercise_science": ["exercise", "training", "strength", "endurance", "athlete", "performance", "cold plunge", "cold water",
                         "sauna", "sleep", "recovery", "vo2"],
    "emerging_technology": ["headset", "wearable", "app", "ai", "device", "neurofeedback", "tdcs", "stimulation", "peptide", "nootropic"],
}


@dataclass
class ParsedQuestion:
    raw: str
    cleaned: str
    asker_direction: str                 # "benefit" | "harm" | "neutral"
    exposure: str
    outcome: str
    population: str | None
    comparator: str | None
    neutral_question: str
    domains: list[str]
    concepts: list[str] = field(default_factory=list)
    framing_hash: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _strip_rhetoric(q: str) -> tuple[str, list[str]]:
    notes = []
    s = q.strip()
    for pat in RHETORIC_PATTERNS:
        new = re.sub(pat, " ", s, flags=re.IGNORECASE)
        if new != s:
            notes.append(f"removed framing matching /{pat}/")
            s = new
    s = re.sub(QUESTION_LEAD, "", s, flags=re.IGNORECASE)
    s = re.sub(r"[?!.]+\s*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s, notes


def _strip_negation(s: str) -> tuple[str, bool]:
    """Remove in-clause negation ('X fails to', 'X doesn't') AFTER rhetoric is gone. A leading
    rhetorical negation ('Isn't X good?') was already removed and is affirmative, not negative."""
    new = re.sub(NEGATION, "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", new).strip(), new != s


INCREASE_WORDS = {"increase", "increases", "increased", "raise", "raises", "boost", "boosts", "extend", "extends", "longer", "more"}
DECREASE_WORDS = {"reduce", "reduces", "reduced", "lower", "lowers", "decrease", "decreases", "shorten", "shortens", "less", "relieve", "relieves"}


def _direction(text: str) -> str:
    """Direction the asker is pushing. Change-verbs are interpreted relative to whether
    the outcome is something people want less of (symptoms, mortality...)."""
    words = re.findall(r"[a-z\-']+", text.lower())
    negative_outcome = any(w in NEGATIVE_OUTCOMES for w in words)
    negated = bool(re.search(NEGATION, text, re.I)) or any(w in {"useless", "ineffective"} for w in words)
    b = h = 0
    for w in words:
        if w in INCREASE_WORDS:
            h += negative_outcome; b += (not negative_outcome)
        elif w in DECREASE_WORDS:
            b += negative_outcome; h += (not negative_outcome)
        elif w in BENEFIT_WORDS:
            b += 1
        elif w in HARM_WORDS:
            h += 1
    if negated:
        b, h = h, b
    if b > h:
        return "benefit"
    if h > b:
        return "harm"
    return "neutral"


LINK_VERBS = (r"(?:increase|increases|increased|decrease|decreases|reduce|reduces|reduced|improve|improves|improved|"
              r"worsen|worsens|boost|boosts|enhance|enhances|help|helps|affect|affects|influence|influences|impact|impacts|"
              r"cause|causes|lower|lowers|raise|raises|extend|extends|shorten|shortens|prevent|prevents|treat|treats|"
              r"effectively treat|protect against|lead to|leads to|make|makes|change|changes|alter|alters|work for|works for|"
              r"good for|bad for|linked to|associated with|related to|effect on|effects on|impact on)")


def _split_exposure_outcome(s: str) -> tuple[str, str, str | None, list[str]]:
    """Return (exposure, outcome, population, notes). Heuristic patterns:
       '<X> <verb> <Y>'              -> X, Y
       '<X> (is|are) more <adj>'     -> X (trait), outcome=<adj>
       '<X> good/bad for <Y>'        -> X, Y
       'effect of <X> on <Y>'        -> X, Y
    """
    notes: list[str] = []
    pop = None
    # population phrases: "in adults", "for people with ADHD", "among older women"
    m = re.search(r"\b(in|for|among)\s+((?:adults?|children|adolescents|people|patients|men|women|older|elderly|athletes|students)[^,]*)$", s, re.I)
    if m:
        pop = m.group(2).strip()
        s = s[: m.start()].strip()
        notes.append("population extracted from trailing 'in/for/among' phrase")
    m = re.search(r"effects?\s+of\s+(.+?)\s+on\s+(.+)$", s, re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip(), pop, notes
    m = re.search(rf"^(.+?)\s+(?:actually\s+|really\s+)?{LINK_VERBS}\s+(.+)$", s, re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip(), pop, notes
    m = re.search(r"^(.+?)\s+(?:is|are|be)?\s*(?:more|less)\s+(.+?)(?:\s+(?:to|for|among)\s+(?:women|men|people|others|partners|the opposite sex))?$", s, re.I)
    if m:
        notes.append("comparative-trait question: exposure is the trait, outcome is the attribute")
        return m.group(1).strip(), m.group(2).strip(), pop, notes
    ADJ = r"(?:good|bad|great|beneficial|harmful|safe|dangerous|useless|useful|helpful|effective|ineffective|terrible|poor|worthwhile|worth it)"
    m = re.search(rf"^(.+?)\s+(?:is|are)?\s*(?:an?\s+)?{ADJ}?\s*(?:treatment|therapy|option|intervention|remedy|idea)?\s*(?:for|against)\s+(.+)$", s, re.I)
    if m and m.group(2).strip():
        return m.group(1).strip(), m.group(2).strip(), pop, notes
    notes.append("could not split exposure/outcome; whole text used as exposure - LLM must set PICO")
    return s, "", pop, notes


def _clean_concept(c: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9\-']+", c)]
    keep = []
    for w in words:
        lw = w.lower()
        if lw in BENEFIT_WORDS or lw in HARM_WORDS or lw in INCREASE_WORDS or lw in DECREASE_WORDS or lw in {"fail", "fails", "failed"}:
            continue
        if lw in {"a", "an", "the", "of", "to", "their", "your", "my", "our", "his", "her", "one's", "someone's", "people's",
                  "more", "less", "much", "very", "any", "some", "overall", "generally"}:
            continue
        keep.append(lw)
    return " ".join(keep)


def parse_question(raw: str) -> ParsedQuestion:
    cleaned, notes = _strip_rhetoric(raw)
    direction = _direction(cleaned)
    cleaned, had_neg = _strip_negation(cleaned)
    if had_neg:
        notes.append("removed in-clause negation (direction recorded separately)")
    exposure, outcome, population, n2 = _split_exposure_outcome(cleaned)
    notes += n2
    exposure_c = _clean_concept(exposure)
    outcome_c = _clean_concept(outcome)
    # Outcome synonym normalisation for a few recurring constructs
    outcome_c = re.sub(r"\b(lifespan|life expectancy|how long .*live|longevity|mortality)\b", "longevity mortality", outcome_c)
    outcome_c = re.sub(r"\b(cognitive performance|cognition|cognitive function|thinking|brain function|memory)\b", "cognitive performance", outcome_c)
    outcome_c = re.sub(r"\b(people|persons|us|you|them|someone|anyone)\s+(happier|happy)\b", "happiness", outcome_c)
    outcome_c = re.sub(r"\b(happier|happy|happiness|life satisfaction|well-?being|subjective well-?being)\b", "SWB", outcome_c)
    outcome_c = re.sub(r"\b(SWB)(\s+SWB)*\b", "subjective well-being happiness", outcome_c)
    outcome_c = re.sub(r"\b(attractive|attractiveness|romantically attractive|romantic attractiveness|desirable)\b", "romantic attractiveness", outcome_c)
    outcome_c = re.sub(r"\badult adhd\b", "adhd symptoms", outcome_c)
    outcome_c = re.sub(r"\badhd( symptoms?)?\b", "adhd symptoms", outcome_c)
    outcome_c = re.sub(r"\b(depression|depressive symptoms|major depressive disorder|mdd)\b", "depression", outcome_c)
    if re.search(r"\badult adhd\b", outcome, re.I) and not population:
        population = "adults"
    outcome_c = re.sub(r"\s+", " ", outcome_c).strip()
    exposure_c = re.sub(r"\b(red meat consumption|red meat intake|eating red meat|red meat)\b", "red meat consumption", exposure_c)
    exposure_c = re.sub(r"\b(creatine supplementation|creatine supplements|creatine monohydrate|creatine)\b", "creatine supplementation", exposure_c)
    exposure_c = re.sub(r"\b(cold plunges?|cold water immersion|ice baths?)\b", "cold water immersion", exposure_c)
    exposure_c = re.sub(r"\b(extraverted|extroverted|extraversion|extroversion)\b", "extraversion", exposure_c)
    exposure_c = re.sub(r"\b(additional income|higher income|income|money|wealth|earnings)\b", "income", exposure_c)
    exposure_c = re.sub(r"\bflow( neuroscience)? (tdcs )?headset\b", "flow neuroscience tdcs headset", exposure_c)
    exposure_c = re.sub(r"\b(men|women|people|adults|individuals)\b$", "", exposure_c).strip()
    exposure_c = re.sub(r"\b(dietary interventions?|diet changes?|diet)\b", "dietary intervention", exposure_c)
    exposure_c = re.sub(r"\s+", " ", exposure_c).strip()
    if re.search(r"\bextrav", exposure_c) and not population and re.search(r"\bmen\b", exposure, re.I):
        population = "men"
    domains = detect_domains(f"{exposure_c} {outcome_c} {population or ''}")
    concepts = sorted({c for c in (exposure_c, outcome_c) if c})
    pop_text = f" in {population}" if population else ""
    neutral = (f"What is the effect of {exposure_c} on {outcome_c}{pop_text}, and in which direction?" if outcome_c
               else f"What does the evidence show about {exposure_c}{pop_text}?")
    pq = ParsedQuestion(raw=raw, cleaned=cleaned, asker_direction=direction, exposure=exposure_c, outcome=outcome_c,
                        population=population, comparator=None, neutral_question=neutral, domains=domains,
                        concepts=concepts, notes=notes)
    pq.framing_hash = framing_hash(pq)
    return pq


def framing_hash(pq: ParsedQuestion) -> str:
    """Hash of the direction-free concept set. Equal across opposite framings."""
    payload = json.dumps({"exposure": pq.exposure, "outcome": pq.outcome, "population": (pq.population or "").lower()}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def detect_domains(text: str) -> list[str]:
    t = text.lower()
    scores = {d: sum(1 for k in kws if re.search(r"\b" + re.escape(k.strip()) + r"\b", t)) for d, kws in DOMAIN_KEYWORDS.items()}
    ranked = [d for d, s in sorted(scores.items(), key=lambda kv: -kv[1]) if s > 0]
    return ranked[:3] or ["general"]


# ----------------------------------------------------------------------------
# Search strategy (direction-free)
# ----------------------------------------------------------------------------

SYNONYMS: dict[str, list[str]] = {
    "creatine supplementation": ["creatine"],
    "cognitive performance": ["cognition", "cognitive", "memory", "executive function", "intelligence"],
    "red meat consumption": ["red meat", "unprocessed meat", "processed meat", "meat consumption"],
    "longevity mortality": ["mortality", "all-cause mortality", "longevity", "life expectancy"],
    "extraversion": ["extraversion", "extroversion", "extravert*", "extrovert*"],
    "romantic attractiveness": ["attractiveness", "mate preference", "romantic attraction", "mate choice", "speed-dating", "desirability", "mate value"],
    "income": ["income", "wealth", "money"],
    "subjective well-being happiness": ["happiness", "subjective well-being", "life satisfaction", "emotional well-being"],
    "cold water immersion": ["cold water immersion", "cold exposure", "ice bath", "cold plunge"],
    "adhd symptoms": ["ADHD", "attention deficit hyperactivity disorder", "attention", "hyperactivity"],
    "dietary intervention": ["diet", "dietary intervention", "elimination diet", "nutrition", "supplementation"],
    "flow neuroscience tdcs headset": ["Flow Neuroscience", "transcranial direct current stimulation", "tDCS", "home-based tDCS"],
    "depression": ["depression", "depressive disorder", "depressive symptoms"],
    "adhd symptoms": ["ADHD", "attention deficit hyperactivity disorder", "attention", "hyperactivity"],
}


# Single-word demographics are nearly always present in abstracts and make boolean searches noisy
# (e.g. "men" pulls in unrelated men's-health epidemiology). They stay in the PICO for the appraiser.
GENERIC_POPULATIONS = {"men", "women", "adults", "people", "humans", "patients", "individuals", "participants"}


def _or_block(concept: str) -> str:
    terms = SYNONYMS.get(concept) or [concept]
    return "(" + " OR ".join(f'"{t}"' if (" " in t and "*" not in t) else (f"{t}[tiab]" if "*" in t else t) for t in dict.fromkeys(terms)) + ")"


def search_strategy(pq: ParsedQuestion) -> dict:
    """Canonical, direction-free query set. Identical for all framings of a question."""
    blocks = [_or_block(c) for c in (pq.exposure, pq.outcome) if c]
    base = " AND ".join(blocks)
    pop = ""
    if pq.population and _clean_concept(pq.population) not in GENERIC_POPULATIONS:
        pop = " AND " + _or_block(_clean_concept(pq.population))
    plain = " ".join(t for c in (pq.exposure, pq.outcome) if c for t in [c])
    return {
        "framing_hash": pq.framing_hash,
        "pubmed": {
            "reviews": f"{base}{pop} AND (systematic[sb] OR meta-analysis[pt] OR \"systematic review\"[pt] OR umbrella review[tiab])",
            "trials": f"{base}{pop} AND (randomized controlled trial[pt] OR controlled clinical trial[pt] OR randomi*[tiab])",
            "observational": f"{base}{pop} AND (cohort[tiab] OR prospective[tiab] OR observational study[pt] OR longitudinal[tiab] OR cross-sectional[tiab])",
            "recent_any": f"{base}{pop}",
        },
        "openalex": {
            "query": plain,
            "filter_reviews": "type:review|article,title_and_abstract.search:" + plain.replace(",", " ") + " meta-analysis",
            "filter_any": None,
        },
        "europepmc": {"query": f"{base}{pop}"},
        "semanticscholar": {"query": plain},
        "concepts": {"exposure": pq.exposure, "outcome": pq.outcome, "population": pq.population},
    }
