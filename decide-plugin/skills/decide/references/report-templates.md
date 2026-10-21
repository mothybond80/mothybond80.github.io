# Report templates

## /decide quick

```
# <Neutral question>

**Verdict:** <one of the six verdict sentences>  (certainty: high|moderate|low|very low)
**Refers to the claim:** "<directional claim judged>"

## What the evidence shows (plain language)
3-6 sentences. Magnitude in absolute terms where possible.

## Important counter-evidence
- [R#] First author year, design, n: finding and why it carries the weight it does.

## Confidence and gaps
Why the certainty is what it is; what would change it.

## Practical recommendation
Only if justified. Otherwise: "The evidence does not support choosing one option over another because ...".
Decision assumptions: ... Value judgements: ... (Medical: supervision note.)
You asked: "<original framing>" -> neutral question above.

## Key references
[R#] Authors (year). Title. Journal. DOI/PMID. Design, n. Verified: yes/no.

## Method
Mode quick; databases, dates, queries, hit counts (table from pack.searches); not searched: ...; run dir; lock hashes.
```

## /decide deep

As quick, plus: methodology section (PICO, inclusion criteria, search table,
screening counts: retrieved / tier A / tier B / excluded with reasons); key
studies table (design, population, n, comparator, outcomes, effect with CI,
funding, limitations, abstract-only flag); certainty by outcome (GRADE
domains); contradictory findings and how they were weighed; overlap between
syntheses; alternatives considered; risks; decision analysis (benefits, harms,
probabilities, costs, reversibility, value of information, delay, do-nothing);
challenge summary (challenge_outcome and top three objections with weights);
verification table; limitations; what new findings would change the verdict.

## /decide challenge

```
# Challenge of: "<claim or previous conclusion>"
Neutral question: ...
**Challenge outcome:** verdict_stands | verdict_weakened | verdict_changed | verdict_strengthened
**Does this change the conclusion?** Yes/No, because ...

## Strongest reasons the conclusion could be wrong (ranked, with weight)
1. (high) ...
2. (moderate) ...
3. (low) ...

## Unsupported assumptions / alternative interpretations / missing evidence
## Citation integrity findings
## What would settle it
## Method and references (as quick)
```
