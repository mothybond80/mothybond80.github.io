# Challenge report: creatine supplementation and cognitive performance

Reviewed: `pack.json` (76 records, pack_hash 12f24687...), `appraisal.md`, `appraisal.json`.
Preliminary verdict under review: **suggests_with_uncertainty** (memory, older or sleep-deprived adults; null for general cognition in healthy young adults).

Attempted extra search: `decide-engine --offline search ... --mode deep` returned 0 records; all six search URLs (PubMed reviews/trials/observational/recent, OpenAlex, Europe PMC) were reported "blocked (offline, not cached)". No new records could be checked, so nothing below is based on evidence outside the pack.

## 1. Contradictory studies that might have been missed

Only PubMed (3 queries, 65 of 2,168 hits retrieved) and one citation-sorted OpenAlex query (almost entirely off-topic) were run; the planned observational, OpenAlex-review, Europe PMC and Semantic Scholar searches are in `search_strategy` but absent from `searches`, and `errors` is empty, so they failed silently. No trial registry (ClinicalTrials.gov, DRKS, ISRCTN, all of which the included trials R12, R14, R20, R21 use), no Cochrane/Embase/PsycINFO/SPORTDiscus, no preprints or grey literature, and no synonym coverage for "sleep deprivation", "hypoxia", "vegan", "attention", "reaction time" or "processing speed". The study most likely missing is a completed-but-unpublished or low-visibility *null* RCT (the kind that lives in registries), plus the original 2024 meta-analysis whose erratum is R5, and the published critiques of R7 (PMID 36644917) and R1 (PMIDs 41405444, 41405942), which could change how R7's pooled estimate is read.

## 2. Weakest link from evidence to verdict

The older-adult subgroup of R7 (SMD 0.88, 95% CI 0.22 to 1.55, I2 83%) [R7]. R7's own duration range "5 days to 24 weeks" shows the null 24-week trial R21 is already inside that subgroup, so a pooled 0.88 with I2 83% must be carried by one or two tiny positive trials of the R23 type (n=32, one week, "divided into two groups", randomisation not stated) with very large effects [R21, R23]. The appraisal rests its headline subgroup on exactly the trials with the fewest participants and the poorest reporting.

## 3. Alternative explanations

Expectancy/unblinding: creatine caused side effects 4.25 times as often as placebo [R20], and water-weight gain is well known (not verified in pack), so small trials may be functionally unblinded. Multiplicity and no dose-response: R12 reports a reaction-time win for the medium dose only, with the low dose and HCl+EE arms silent, among many outcomes in ~9 per arm [R12]; R16, R19 and R13 each report one or two significant tests among many [R16, R19, R13]. Practice effects: in R24 the creatine group showed a "significant linear improvement" across the session while the between-group difference appeared on one task at one time point [R24]. Confounding: four of R1's six "positive" studies are cross-sectional dietary-recall associations, exposed to meat/protein intake and healthy-user bias [R1].

## 4. Correlation treated as causation

Mostly avoided. The appraisal correctly labels R1's cross-sectional studies and R26's perceptions as observational [R1, R26]. Two slips: the prose says "A 2026 review of six older-adult studies counted five as positive" without noting in that sentence that the count mixes associations with trials, and the R28 pilot (n=20, "associated with improved fluid cognition") is quoted as mechanistic support although the abstract gives no control group [R28].

## 5. Replication

Reasoning (Raven's): R25 (n=45) not replicated by R20 (n=123, same 5 g x 6 weeks; eta2p 0.008) [R25, R20]. Vegetarian advantage: R22 and R25 not replicated by R20 ("Vegetarians did not benefit more") [R22, R25, R20]. Older adults: R23 (1 week, positive) versus R21 (24 weeks, null) [R23, R21]. Working memory (backward digit span) is the only measure with same-direction results from two independent groups (R25 p<0.0001; R20 p=0.064, eta2p 0.029) [R25, R20]. Sleep deprivation: two independent groups (McMorris, Gordji-Nejad) report the same direction, but on different tasks, doses (20 g/d x 7 d vs single 0.2 g/kg) and with exercise as a co-intervention in R24 [R24, R13].

## 6. Negative or null findings under-weighted

Nulls are weighted well on the whole (R21 and R20 are given "high" weight). The under-weighted item is actually the most precise estimate in the pack: the young-adult subgroup SMD 0.03 (95% CI -0.14 to 0.20, I2 0%) [R7], together with R20, bounds any effect in young adults below about 0.2; the appraisal says "null" but does not use this to question why the older subgroup should differ by 0.85 SMD. Conversely, the prose omits that R20's abstract states "Bayesian evidence supported a small beneficial effect of creatine" [R20], which under-reports evidence *for* the verdict.

## 7. Publication bias and small-study effects

No funnel plot or Egger test appears in any abstract [R7, R11, R6, R1, R2]; with 8 pooled trials R7 could not have tested it reliably anyway. The pack itself shows the small-study pattern: significant results come from n=12, 14, 29, 32, 36 and 45 [R19, R16, R13, R23, R12, R25] while the three largest trials (n=123, 128, 56) are borderline or null [R20, R22, R21]. The appraisal's "undetected but suspected" understates this; "suspected, with the small-study pattern visible in the pack" would be accurate.

## 8. Conclusions stronger than the data

(a) GRADE arithmetic: for memory the appraisal records risk of bias serious, inconsistency serious, imprecision serious and publication bias suspected yet assigns "low"; for sleep deprivation it records serious, serious and very serious yet assigns "low". Three or more downgrades from RCT evidence is very_low. (b) "The most consistent signal is under acute sleep deprivation" rests on one task at one time point in R24, an abstract with no effect sizes and a maximum ("up to 12%") in R13, and a review that calls the research "sparse" [R24, R13, R2]. (c) Surrogates: brain-creatine increases (16.4% in R12, 11% in R28) are used as plausibility; R9 reports no effect on brain phosphocreatine in vegetarians [R12, R28, R9]. (d) No absolute test-score differences are available anywhere; everything is SMD, p or percent change.

## 9. Newer studies challenging older syntheses

R20 (2023, n=123) post-dates R7's search (September 2021) and is not in any synthesis in the pack; it fails to reproduce the reasoning gains that R11 and R25 rest on [R20, R11, R25]. R6 (2024) reads largely the same trials as R7 (containment 0.457) and calls the cognitive results "somewhat equivocal" [R6]. R26 (2026) is the only effectiveness-type data and is unfavourable [R26]. The appraisal handles these correctly.

## 10. Citation integrity

All [R#] refs cited in the appraisal exist in the pack and match the described papers (authors checked for R1, R2, R5, R6, R7, R11, R12, R13, R14, R16, R18, R19, R20, R21, R22, R23, R24, R25, R26, R28). Numerical claims:

| Claim | Supporting abstract sentence | Status |
|---|---|---|
| R7 SMD 0.29 (0.04-0.53), I2 66%, 8 of 10 RCTs, search to Sept 2021 | "Overall, creatine supplementation improved measures of memory compared with placebo (standard mean difference [SMD] = 0.29, 95%CI, 0.04-0.53; I2 = 66%; P = 0.02)"; "Ten RCTs ... 8 of which were included in the meta-analysis"; "from inception until September 2021" | supported |
| R7 older 0.88 (0.22-1.55), I2 83%; younger 0.03 (-0.14 to 0.20), I2 0% | "older adults (66-76 years) (SMD = 0.88; 95%CI, 0.22-1.55; I2 = 83%; P = 0.009) ... younger counterparts (11-31 years) (SMD = 0.03; 95%CI, -0.14 to 0.20; I2 = 0%; P = 0.72)" | supported |
| R20 n=123, 5 g x 6 wk, BDS p=0.064 eta2p=0.029, RAPM p=0.327 eta2p=0.008, RR 4.25, 8 exploratory tasks | "daily supplementation of 5 g for 6 weeks"; "About half of our 123 participants"; "bordered significance for BDS (p = 0.064, η2P = 0.029) but not RAPM (p = 0.327, η2P = 0.008)"; "Side effects ... (p = 0.002, RR = 4.25)"; "eight exploratory cognitive tests" | supported |
| R25 n=45 vegetarians, p<0.0001 on BDS and RAPM | "45 young adult, vegetarian subjects"; "significant positive effect (p < 0.0001) on both working memory (backward digit span) and intelligence (Raven's Advanced Progressive Matrices)" | supported |
| R22 n=128 young women, 20 g x 5 d, no effect verbal fluency/vigilance, less RT variability | "Young adult females (n 128)"; "20 g of creatine supplement for 5 d"; "did not influence measures of verbal fluency and vigilance"; "decreased the variability in the responses to a choice reaction-time task" | supported |
| R23 n=32 (15+17), 20 g/d 1 week, all tasks except backward number recall | "Group 1 (n = 15) ... 5 g four times a day ... Group 2 (n = 17)"; "significant effect ... on all tasks except backward number recall" | supported |
| R21 24 wk, n=14 x 4 arms, no cognitive change | "24-week, parallel-group, double-blind, randomized, placebo-controlled trial ... (n=14 each)"; "Neither strength training nor creatine supplementation altered any parameter of cognitive performance" | supported |
| R1 6 studies, 1,542, 2 RCT + 4 cross-sectional, 5/6 positive, 1 good/2 fair/3 poor | "Six studies were included, with a total of 1542 participants"; "Two studies were double-blind interventions ... Four studies were cross-sectional"; "Five of the six (83.3%) ... positive"; "one ... 'good', two 'fair', and three 'poor'" | supported |
| R14 73 enrolled, 64 analysed, 45-65 y, 10 g/d, 12 wk, exploratory | "Seventy-three healthy sedentary adults"; "Sixty-four adults aged 45-65 years ... completed the 12-week intervention"; "2 × 5 g/d"; "should be interpreted as exploratory" | supported |
| R13 n=29, 0.2 g/kg, 21 h SD, up to 12% | "Twenty-nine healthy subjects"; "single dose of creatine monohydrate (0.2 g/kg) ... 21 h of sleep deprivation"; "improvement of up to 12%" | supported |
| R24 20 g/d x 7 d, central executive only at 36 h, p<0.05 | "5 g ... four times a day for 7 days"; "better than the placebo group on the central executive task but only at 36 h" (p < 0.05) | supported |
| R2 5 studies, narrative, "positive trend", "sparse" | "five studies met the inclusion criteria"; "synthesized narratively"; "positive trend"; "research is sparse" | supported |
| R26 n=2,178, median 55, 67.8%, 64.4%, McNemar p<.001, OR 0.66 (0.55-0.80) | "2,178 analyzable responses ... median age, 55 years"; "Cognitive performance was the most commonly endorsed goal (67.8%)"; "64.4% ... did not perceive a matched cognitive benefit; McNemar p < .001"; "OR = 0.66; 95% CI 0.55-0.80" | supported |
| R12 n=36, 4 arms, RT 1.2 vs 6.6%, brain Cr 0.9 vs 16.4% | "36 apparently healthy perimenopausal and menopausal women ... one of four groups"; "reaction time (1.2 vs. 6.6%; p < 0.01) ... frontal brain creatine levels (0.9 vs. 16.4%; p < 0.01)" | supported |
| R16 n=14 crossover, 20 g/d 7 d, DCT d=0.77 p=0.013 | "14 physically active men ingested 20 g/day of CrM or placebo (PL) for 7 days"; "DCT (d = 0.77; p = 0.013)" | supported |
| R19 n=12, creatine nitrate, Stroop p=0.04 ES 0.163 with caffeine | "twelve resistance-trained male athletes"; "Creatine nitrate and caffeine that were co-ingested significantly enhanced ... Stroop ... (p = 0.04; effect size = 0.163)" | supported |
| R18 n=40 male adolescents, crossover | "40 male adolescent basketball players (13-14 years old)"; "randomized counterbalanced crossover" | supported |
| R15 n=58, no CrM-only arm, most tests unaffected | "58 healthy and active adults"; arms PLA, GAA+PLA, GAA+CrM; "most cognitive tests were not affected" | supported |
| R11 6 RCTs, 281 | "Six studies (281 individuals)" | supported |
| R28 no RCTs; pilot n=20, 20 g/d 8 wk, +11% brain creatine | "No relevant randomized controlled trials (RCTs) were identified"; "single human pilot trial (n = 20) ... 20 g/day for 8 weeks ... increased brain total creatine by 11%" | supported |
| R28 "one rodent study reported worse spatial memory in males" | Abstract: "one rodent study reported worsening spatial memory" and, separately, "Sex-specific effects were identified in one rodent study, with ... males showing a trend toward harm" | UNSUPPORTED as stated (two findings conflated; abstract does not say the spatial-memory worsening was in males) |
| appraisal.json, memory outcome: "Post-2021 trials not in R7: ... R21 (older women, 24 wk) no change" | R21 is dated 2013 [R21]; R7 searched to September 2021 and reports durations "5 days to 24 weeks" [R7] | UNSUPPORTED (R21 is within R7's window and almost certainly inside the pooled older subgroup; the appraisal treats it as independent of R7) |
| Search counts 60/25, 179/25, 1,929/15, 11,974/20; 19 of 76 relevant; containment 0.348 and 0.457; 11 blocked enrichment fetches | `searches`, `records_used` (19 refs), `overlap_warnings`, `fetch_log_summary.blocked = 11` | supported |

Retracted or flagged records: `retracted_or_flagged` lists R5 (ErratumIn) and R41 (ErratumIn). Neither is used as evidence; R5 is correctly excluded and R41 is off-topic. No record in the pack is marked retracted.

## Outcome

**challenge_outcome: verdict_weakened**

The label `suggests_with_uncertainty` survives, but only for a small working-memory effect of uncertain size, and it should carry **very_low** certainty rather than low. The emphasis on older adults should be demoted: that subgroup is the least reliable part of the evidence, not the strongest, and the sleep-deprivation leg rests on two small trials from groups with prior positive publications. "Mixed" would be defensible; "contradicts" would not, because no human trial in the pack shows harm and the direction of the memory measures is consistently zero-to-positive [R7, R20, R25, R22].

### Three strongest reasons the preliminary conclusion could be wrong (ranked)

1. **Small-study and subgroup fragility (high).** The pooled lower CI bound is 0.04; the headline older-adult subgroup (I2 83%) already contains the null 24-week R21, so it is carried by one or two 1-week trials of ~32 people; the largest trial and the only homogeneous subgroup (I2 0%) put the effect at or below 0.2 [R7, R20, R21, R23].
2. **Unblinding, multiplicity and absent dose-response (moderate).** Side effects were 4.25 times more frequent on creatine [R20]; the positive single trials each report one or two wins among many outcomes with no correction, and R12's only significant arm is the middle dose [R12, R16, R19, R13, R24].
3. **Search incompleteness of unknown direction (moderate).** 154 of 179 trial hits and the observational, Europe PMC, Semantic Scholar and registry searches were never retrieved; the only 2024 meta-analysis is present as an erratum; critiques of R7 and R1 are missing. The missing material could cut either way, which is itself a reason to lower confidence [R5, R7, R1].

### Unsupported claims found

1. appraisal.json (memory outcome, magnitude): R21 listed among "Post-2021 trials not in R7". R21 is a 2013 trial inside R7's search window and duration range.
2. appraisal.json (older-adults outcome, magnitude): "one rodent study reported worse spatial memory in males" conflates two separate statements in R28's abstract.
3. Interpretive overstatement (not a numerical error): "The most consistent signal is under acute sleep deprivation" is stronger than R24 (one task, one time point), R13 (no effect sizes) and R2 ("sparse") support.

Retracted or flagged records used as evidence: none (R5 and R41 are flagged and both excluded).

challenge_outcome: verdict_weakened
