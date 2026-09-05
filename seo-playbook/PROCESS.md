# How Tim and Claude work through the playbook — one step at a time

## Ground rules (to stop us getting distracted)

1. **One phase open at a time.** We do not start Phase N+1 until Phase N's definition of done is ticked.
2. **One cluster at a time** (video, Chapter 3, step 3). Ideas for other clusters go in the Parking Lot at the bottom, not into the work.
3. **Every session starts the same way.** Claude reads `CLAUDE.md` → finds the first unticked box below → does that, nothing else → updates the boxes and `CLAUDE.md` → commits.
4. **Tim's time is the scarce resource.** Anything marked **Tim** is batched into a short list per phase; Claude prepares everything so each Tim item takes minutes.
5. **Nothing is published without Tim reading it.** Claude drafts; Tim adds clinical experience and approves.
6. **No secrets in this repository.** It is a public GitHub Pages repo.

## Roles

| | Claude | Tim |
|---|---|---|
| Research, crawling, drafting, checklists, building calculators, tracking | ✅ | reviews |
| Google/ChatGPT checks that need a real browser (intent tests, incognito AI tests, GBP) | prepares the exact list | ✅ runs them, pastes results |
| Clinical content: experience, opinion, cases, photos, consent | never invents | ✅ |
| WordPress edits (Elementor/Yoast) | writes the exact copy and settings | ✅ applies them (or grants an editor login later) |
| Accounts, payments, credentials | recommends | ✅ decides and holds |

---

## Phase 0 — Learn and audit (this session)  ✅ mostly done

- [x] Extract the full video (transcript, chapters, tools) → `PLAYBOOK.md`
- [x] Check API availability of every tool → `TOOLS.md`
- [x] Crawl all 59 pages and run Lighthouse → `AUDIT.md`
- [x] Write memory (`CLAUDE.md`) and this process
- [ ] **Tim:** read `PLAYBOOK.md` (15 min) and `AUDIT.md` (10 min); answer the four Gate-1 questions at the end of `TOOLS.md`

**Done when:** Tim has answered Gate 1.

---

## Phase 1 — Foundation (video week 1)

Claude:
- [ ] Set up whichever keyword-data route Tim chose (Surfer export folder, or DataForSEO in the sandbox)
- [ ] Pull Search Console data (API or Tim's CSV): top 200 queries, pages, positions, last 12 months
- [ ] Ideation sweep for the chosen cluster: GSC queries + autocomplete/PAA list for Tim to verify + "30 questions before Invisalign" + sitemap gap analysis vs 3 local competitors
- [ ] Validate against the Keyword Sweet Spot (demand / fit / intent / difficulty) → shortlist of 10–15 keywords with intent labels → `keywords/shortlist.md`
- [ ] Map each keyword to an existing money page or a page to create

Tim (≈30 min total):
- [ ] Confirm Search Console property and grant access (or export CSV)
- [ ] Verify site in Bing Webmaster Tools (import from GSC) and switch on IndexNow in Yoast
- [ ] Install Keyword Surfer; run the 30-second intent test on the top 5 keywords Claude lists; paste back what type of results rank
- [ ] Confirm the first cluster (default: **Invisalign**) and the single most important money page (default: `/invisalign/`)

**Done when:** `keywords/shortlist.md` exists with 10–15 validated keywords, intents confirmed by Tim, and the money page and cluster are named in `CLAUDE.md`.

---

## Phase 2 — The most important money page (video week 2)

- [ ] Claude: research the top 5 UK results for the money-page keyword; list table-stakes topics, gaps, length benchmark, unique angles
- [ ] Claude: outline → draft revisions to `/invisalign/` (structure, direct-answer Q&A, schema additions, internal links out and in)
- [ ] Tim: add the human layer (cases, opinion, what patients actually say, photos with consent); approve
- [ ] Claude: on-page checklist (title <60, one H1 mirroring title, meta 150–160, URL, alt text, WebP, contextual internal links from every related page) → exact Elementor/Yoast instructions
- [ ] Tim: apply in WordPress; Claude re-crawls to verify
- [ ] Fix the site-wide technical items from `AUDIT.md` marked *Phase 2* (they are quick and affect this page too)

**Done when:** the page is live, re-crawled clean, and indexed in GSC and Bing.

---

## Phase 3 — First funnel (video week 3)

- [ ] Choose 2–3 supporting pieces for the cluster: one commercial ("Invisalign vs fixed braces in Rugby: honest comparison", "Invisalign cost UK 2026 explained"), one informational (existing `/how-invisalign-works/` upgraded rather than new, per the video's "update page-2/3 content first" advice)
- [ ] Same blueprint per piece: research → outline → draft → Tim layer → optimise → on-page → internal links to the money page and siblings
- [ ] Build the first linkable asset: **Invisalign cost calculator** hosted on this GitHub Pages repo, embedded on the money page
- [ ] Decide where informational content lives (WordPress posts vs pages); currently there are 0 posts and a homepage link to a blog that does not exist

**Done when:** money page + 2–3 cluster pages are live and interlinked, calculator embedded, all indexed.

---

## Phase 4 — Promote and monitor (video week 4, then ongoing)

- [ ] Tim: subscribe to Source of Sources with the practice email; Claude filters dental/health queries from Gmail and drafts replies for Tim to send
- [ ] Google Business Profile: Tim exports current profile state; Claude produces the completeness checklist and a review-response routine
- [ ] AI-visibility baseline: Tim runs the 10 incognito questions; Claude logs results and repeats via APIs monthly
- [ ] Monthly GSC review: impressions ↑, new queries, position moves; written into `CLAUDE.md` under *Progress log*
- [ ] Plan the **next** cluster (not a random topic) — candidates in the Parking Lot

**Done when:** first month's report is written and the next cluster is chosen. Then loop: Phase 2 (next money page) → Phase 3 (its funnel) → Phase 4.

---

## Parking Lot (ideas we deliberately are not doing yet)

- Dental implants cluster (money page exists; second cluster candidate)
- Composite bonding cluster (third)
- Nervous patients / sedation cluster (strong differentiator, lower volume)
- Emergency dentist (high intent; check duplicate pages first, see `AUDIT.md`)
- Polish-language page (`/dentysta-rugby/`) — keep, but not a priority
- Video SEO for the Vimeo content already on the site (YouTube versions, VideoObject schema)
- Security headers and performance work beyond what Lighthouse flags as critical
- Google Business Profile API application (only if manual review handling becomes a burden)
