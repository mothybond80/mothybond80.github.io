"""Study-design classification and domain-aware evidence tiers.

Classification uses PubMed PublicationType tags when present (reliable),
falling back to title/abstract regexes (flagged as heuristic). Sample size is a
regex guess from the abstract and is ALWAYS labelled as such.

Evidence tiers are *domain dependent*. A medical hierarchy (SR of RCTs > RCT >
cohort...) is not applied to economics or psychology, where natural
experiments, replications and pre-registered studies carry weight. The tiers
are guidance for the appraising agent, not an automatic quality score.
"""

from __future__ import annotations

import re
from typing import Any

PUBTYPE_MAP = [
    ("Retracted Publication", "retracted"),
    ("Retraction of Publication", "retraction_notice"),
    ("Published Erratum", "erratum"),
    ("Expression of Concern", "expression_of_concern"),
    ("Meta-Analysis", "meta_analysis"),
    ("Systematic Review", "systematic_review"),
    ("Randomized Controlled Trial", "rct"),
    ("Controlled Clinical Trial", "controlled_trial"),
    ("Clinical Trial", "clinical_trial"),
    ("Pragmatic Clinical Trial", "rct"),
    ("Observational Study", "observational"),
    ("Practice Guideline", "guideline"),
    ("Guideline", "guideline"),
    ("Consensus Development Conference", "guideline"),
    ("Review", "narrative_review"),
    ("Case Reports", "case_report"),
    ("Comment", "comment"),
    ("Letter", "comment"),
    ("Editorial", "comment"),
    ("Comparative Study", None),
    ("Multicenter Study", None),
]

TITLE_PATTERNS = [
    (r"\bumbrella review\b", "umbrella_review"),
    (r"\bmeta-?analy", "meta_analysis"),
    (r"\bsystematic(ally)? review", "systematic_review"),
    (r"\bmendelian randomi[sz]ation\b", "mendelian_randomisation"),
    (r"\brandomi[sz]ed\b|\brandomi[sz]ed,? (double|single)-blind|\bRCT\b|\bplacebo-controlled\b", "rct"),
    (r"\bnatural experiment\b|\bdifference-in-differences\b|\bregression discontinuity\b|\binstrumental variable", "natural_experiment"),
    (r"\bprospective cohort\b|\bcohort stud", "cohort"),
    (r"\bcase-control\b", "case_control"),
    (r"\bcross-sectional\b", "cross_sectional"),
    (r"\blongitudinal\b", "longitudinal"),
    (r"\breplication\b|\bregistered report\b", "replication"),
    (r"\bpilot (study|trial)\b|\bfeasibility\b", "pilot"),
    (r"\bin vitro\b|\bmice\b|\bmouse\b|\brats?\b|\brodent|\banimal model", "preclinical"),
    (r"\bcase report\b|\bcase series\b", "case_report"),
    (r"\bprotocol\b", "protocol"),
    (r"\bletter to the editor\b|\bcomment on\b|\bresponse to\b|\breply\b|\berratum\b|\bcorrigendum\b", "comment"),
    (r"\bnarrative review\b|\breview\b|\bperspective\b|\boverview\b", "narrative_review"),
]

SYNTHESIS_TYPES = {"umbrella_review", "meta_analysis", "systematic_review", "guideline"}
PRIMARY_TYPES = {"rct", "controlled_trial", "clinical_trial", "mendelian_randomisation", "natural_experiment", "cohort",
                 "case_control", "cross_sectional", "longitudinal", "observational", "replication", "pilot", "preclinical", "case_report"}


def classify(rec: dict[str, Any]) -> dict[str, Any]:
    """Return {'study_type', 'basis', 'is_synthesis', 'is_primary', 'sample_size_guess', 'sample_size_basis'}"""
    pts = rec.get("pub_types") or []
    st, basis = None, None
    for tag, label in PUBTYPE_MAP:
        if tag in pts and label:
            st, basis = label, f"PubMed PublicationType '{tag}'"
            break
    text = " ".join(x for x in [rec.get("title") or "", (rec.get("abstract") or "")[:600]] if x)
    if st is None or st in ("narrative_review", "clinical_trial", "observational"):
        for pat, label in TITLE_PATTERNS:
            if re.search(pat, text, re.I):
                # pub-type tags beat title regex except where the tag is generic
                if st is None or (st == "narrative_review" and label in SYNTHESIS_TYPES) or \
                   (st == "clinical_trial" and label == "rct") or (st == "observational" and label in PRIMARY_TYPES):
                    st, basis = label, f"title/abstract regex /{pat}/ (heuristic)"
                break
    if st is None:
        st, basis = "unclassified", "no PublicationType tag and no design keywords"
    n, nb = guess_sample_size(rec.get("abstract") or "")
    return {"study_type": st, "basis": basis, "is_synthesis": st in SYNTHESIS_TYPES, "is_primary": st in PRIMARY_TYPES,
            "sample_size_guess": n, "sample_size_basis": nb}


_N_PATTERNS = [
    r"\b[nN]\s*=\s*([\d,]{2,9})\b",
    r"\b([\d,]{2,9})\s+(?:participants|patients|subjects|adults|individuals|respondents|men|women|children|people|persons|volunteers|students)\b",
    r"\b(?:a total of|total of|included|enrolled|recruited|comprising|involving)\s+([\d,]{2,9})\b",
]


def guess_sample_size(abstract: str) -> tuple[int | None, str]:
    """Largest plausible N mentioned. Heuristic: meta-analyses often state pooled N; trials state enrolled N."""
    cands = []
    for pat in _N_PATTERNS:
        for m in re.finditer(pat, abstract):
            try:
                v = int(m.group(1).replace(",", ""))
            except ValueError:
                continue
            if 5 <= v <= 50_000_000:
                cands.append(v)
    if not cands:
        return None, "no N found in abstract (heuristic)"
    return max(cands), "largest N-like number in abstract (heuristic; verify against full text)"


# ----------------------------------------------------------------------------
# Domain guidance
# ----------------------------------------------------------------------------

DOMAIN_GUIDANCE: dict[str, dict[str, Any]] = {
    "medicine": {
        "preferred_designs": ["systematic_review", "meta_analysis", "rct", "guideline"],
        "supporting_designs": ["cohort", "case_control", "mendelian_randomisation"],
        "weak_designs": ["cross_sectional", "case_report", "preclinical", "narrative_review"],
        "appraisal_tools": ["GRADE for certainty per outcome", "Cochrane RoB 2 for RCTs", "ROBINS-I for non-randomised", "AMSTAR 2 for systematic reviews"],
        "watch_for": ["surrogate vs patient-important outcomes", "industry funding", "small-study effects", "harms under-reported",
                      "guideline recommendations vs evidence certainty", "clinical supervision requirements"],
    },
    "nutrition": {
        "preferred_designs": ["rct", "meta_analysis", "systematic_review", "mendelian_randomisation"],
        "supporting_designs": ["cohort", "longitudinal"],
        "weak_designs": ["cross_sectional", "preclinical", "narrative_review"],
        "appraisal_tools": ["GRADE (note NutriGrade adaptations)", "substitution analysis: replaced with what?", "confounding by healthy-user effect",
                            "dose-response", "measurement error in dietary recall"],
        "watch_for": ["RCTs are usually short and use surrogate outcomes", "cohorts confounded by lifestyle", "processed vs unprocessed conflation",
                      "absolute vs relative risk", "industry funding"],
    },
    "psychology": {
        "preferred_designs": ["meta_analysis", "replication", "rct", "longitudinal"],
        "supporting_designs": ["cross_sectional", "cohort"],
        "weak_designs": ["pilot", "case_report", "narrative_review"],
        "appraisal_tools": ["effect size (d, r) with CI, not p-values", "replication status / Many Labs", "pre-registration", "measurement validity",
                            "WEIRD samples and generalisability", "p-curve / publication bias"],
        "watch_for": ["self-report and demand characteristics", "lab vs ecological validity", "speed-dating vs long-term outcomes",
                      "small samples and flexible analysis", "replication crisis"],
    },
    "economics": {
        "preferred_designs": ["natural_experiment", "rct", "longitudinal", "meta_analysis"],
        "supporting_designs": ["cohort", "cross_sectional"],
        "weak_designs": ["narrative_review", "case_report"],
        "appraisal_tools": ["identification strategy (what exogenous variation?)", "within- vs between-person", "log vs linear income",
                            "experienced vs evaluative well-being", "reverse causation"],
        "watch_for": ["satiation claims depend on measure", "cross-country vs within-country", "lottery / windfall studies as quasi-experiments"],
    },
    "social_science": {
        "preferred_designs": ["natural_experiment", "rct", "longitudinal", "meta_analysis", "replication"],
        "supporting_designs": ["cross_sectional", "cohort"],
        "weak_designs": ["narrative_review", "case_report"],
        "appraisal_tools": ["selection effects", "cross-cultural validity", "generalisability", "pre-registration"],
        "watch_for": ["ecological fallacy", "self-selection", "construct validity"],
    },
    "exercise_science": {
        "preferred_designs": ["rct", "meta_analysis", "systematic_review"],
        "supporting_designs": ["controlled_trial", "cohort"],
        "weak_designs": ["pilot", "cross_sectional", "preclinical"],
        "appraisal_tools": ["blinding is often impossible: expect placebo/expectancy effects", "trained vs untrained", "acute vs chronic",
                            "small samples typical"],
        "watch_for": ["surrogate biomarkers", "industry / brand sponsorship", "very small n"],
    },
    "emerging_technology": {
        "preferred_designs": ["rct", "systematic_review"],
        "supporting_designs": ["pilot", "cohort", "controlled_trial"],
        "weak_designs": ["preclinical", "case_report", "narrative_review"],
        "appraisal_tools": ["sham control present?", "manufacturer involvement", "regulatory status (MHRA/FDA/CE)", "mechanistic plausibility vs demonstrated effect",
                            "pre-registration and outcome switching"],
        "watch_for": ["company-funded trials", "open-label uncontrolled studies", "press releases vs peer review", "surrogate outcomes"],
    },
    "general": {
        "preferred_designs": ["systematic_review", "meta_analysis", "rct", "natural_experiment"],
        "supporting_designs": ["cohort", "longitudinal"],
        "weak_designs": ["cross_sectional", "narrative_review", "case_report", "preclinical"],
        "appraisal_tools": ["GRADE-style certainty", "risk of bias", "replication"],
        "watch_for": ["correlation vs causation", "publication bias", "overstated conclusions"],
    },
}


def domain_guidance(domains: list[str]) -> dict[str, Any]:
    out = {d: DOMAIN_GUIDANCE.get(d, DOMAIN_GUIDANCE["general"]) for d in domains}
    if not out:
        out = {"general": DOMAIN_GUIDANCE["general"]}
    return out
