# Where rugbysmiles.co.uk sits against the playbook — audit of 5 Sep 2026

**Method.** Full crawl of every URL in the Yoast sitemap (57) plus 6 probe URLs, from the Higgsfield sandbox (the session's own network cannot reach the site). Title/meta lengths, H1 count, word count with header/footer/nav stripped, images without alt text, contextual body links, structured-data types, redirects and canonicals were recorded for each page. Lighthouse (mobile and desktop) was run on the homepage and the Invisalign page. Tool research is in `TOOLS.md`. Per-page table in Appendix A.

**Verdict in one paragraph.** The site is well ahead of where the video's "beginner" starts: money pages exist for every treatment, prices are published, almost every page carries FAQ and Dentist schema with plain-English direct answers, there is already an `llms.txt`, and there are 505 Google reviews. What is missing is the *system* the video describes: no keyword shortlist driven by Search Console data, no deliberate topic clusters or funnel, no informational content engine (0 blog posts, and the homepage links to a `/blog/` that returns 404), and a long list of mechanical on-page defects (titles and meta descriptions over length on most pages, 116 images without alt text, duplicate URLs left in the sitemap). The single biggest opportunity is to pick one cluster (Invisalign) and run the full blueprint on it.

## Scorecard by playbook chapter

| Ch | Area | Status | One-line evidence |
|----|------|--------|-------------------|
| 1 | Business-goal alignment, crawl/index basics | 🟢 Strong | Sitemap + robots correct; HTTPS and non-www canonicalised; every page indexable; booking CTA everywhere |
| 2 | Search intent | 🟡 Partial | Titles show intent awareness ("£45 New Patient Check-up", "Invisalign vs…") but no recorded SERP checks; 30-second intent tests not yet done |
| 3 | Keywords: Sweet Spot, money pages, clusters | 🟡 Partial | Money pages: yes. Validated keyword list: no. Clusters: partial by accident (Invisalign has 6 related pages) but not interlinked as a funnel |
| 4 | Content that ranks | 🟡 Partial | Average 1,132 words/page; strong human voice and real prices; but no author/reviewer bylines, no cases with data, several thin pages |
| 5 | On-page SEO | 🔴 Gap | 27 titles >60 chars; 38 meta descriptions >160; 7 pages share one description; 5 pages with 0 or 2 H1s; 116 images without alt; sparse body links |
| 6 | Backlinks | 🟡 Unknown/Partial | Not measurable from here (needs Search Console links report or Ahrefs Webmaster Tools). Five quizzes are proto-linkable assets |
| 7 | Technical + local | 🟡 Partial | Technically sound for a WordPress site; three duplicate URLs in sitemap; legacy UA tag; no security headers; Lighthouse below. Google Business Profile not yet reviewed |
| 8 | AI search | 🟢 Strong foundation | FAQ schema on 36 pages, Dentist/MedicalBusiness schema, direct-answer copy, `llms.txt` exists (but lists a stray URL). No AI-visibility baseline yet |
| 9 | 30-day plan | 🔴 Not started | No Search Console data in hand, no shortlist, no chosen cluster; Bing status unknown |

---

## Chapter-by-chapter detail

### Ch1 — Foundations
- 59 pages (Yoast sitemap `page-sitemap.xml` only; there is no `post-sitemap.xml` because there are 0 posts).
- `robots.txt` allows everything and points to the sitemap. No AI crawlers are blocked (good for Ch8).
- `http://` and `www.` both resolve to `https://rugbysmiles.co.uk/` with matching canonicals.
- Homepage HTML is 287 KB, TTFB 0.47 s from the sandbox; median page 181 KB of HTML (Elementor).
- Analytics stack: GA4, GTM, Meta Pixel, Microsoft Clarity, plus a **legacy Universal Analytics tag (UA-100582723-1)** that has been dead since 2024 and should be removed to reduce script weight.

### Ch2 — Intent
- Titles already encode intent well, e.g. transactional (`Emergency Dentist in Rugby | £50 Same-Day Appointments`), commercial (`Dentures vs Implants — Which Is Right?`), informational (`How Invisalign Actually Works | Honest Guide`).
- Nothing recorded about what actually ranks for our targets. **Action (Phase 1, Tim):** run the 30-second intent test on the first five shortlist keywords.

### Ch3 — Keywords, money pages, clusters
- **Money pages present:** `/invisalign/` (1,784 words), `/dental-implants-in-rugby/` (2,627), `/composite-bonding-in-rugby/` (2,505), `/new-patient-check-up/` (1,722), `/emergency-dentist-rugby/` (1,133), `/hygiene-airflow/` (2,119), `/our-pricing/` (1,354), `/dental-plans/` (1,197), plus veneers, whitening, crowns, root canal, fillings, dentures, All-on-4, fixed braces, IV sedation, children's.
- **Invisalign cluster today:** money page + `/how-invisalign-works/` + `/which-invisalign/` + `/invisalign-quiz/` + `/retainers-rugby/` + `/fixed-braces-rugby/` + `/orthodontics/`. This is a real head start; the pages exist but are not built as a funnel (few contextual links between them, no commercial "vs/cost" comparison page targeting UK-wide queries).
- **Conversion paths:** every treatment page has a free-consultation or £45 check-up CTA and the Dentally booking link. Quizzes act as the video's "template download" step. Good.
- **Missing:** a validated shortlist using demand/fit/intent/difficulty. Requires Search Console access (Gate 1).

### Ch4 — Content
- Voice is exactly what the video asks for: honest, specific, priced, patient-objection led ("Three doubts, answered by our Invisalign patients"). Keep it.
- Gaps against the video's human-layer list: no author byline or "clinically reviewed by Dr Tim Bond, GDC no." on treatment pages; no dated case studies with numbers; the before/after gallery has 85 words and 32 of 36 images lack alt text, so its evidence is invisible to Google.
- Thin pages (<400 words): `/testimonials/` (82), `/gallery/` (85), `/contact-us/` (335), `/thanks/`, and the four quizzes (JavaScript-rendered, 13–50 words visible to a crawler). Quizzes are fine as tools but need a crawlable paragraph explaining what they do.
- Homepage copy typos: "RECCOMENDED DENTIST IN RUGBY", "Warwwickshire". Small, but E-E-A-T is partly about care.
- `/contact-us/` meta description still advertises Six Month Smiles and the Inman Aligner, which the site no longer sells.

### Ch5 — On-page checklist (mechanical, Phase 2 batch in Yoast)
| Check | Result | Pages |
|-------|--------|-------|
| Title ≤60 chars | **27 over** (worst: `/orthodontics/` 79, `/childrens-dentist-rugby/` 76, `/general-dentistry/` 76, `/which-invisalign/` 74, `/finance-payment-options/` 73) | see Appendix A |
| One H1 per page | **5 wrong**: 0 H1 on `/surprising-foods…/`, `/testimonials/`, `/gallery/`; 2 H1s on `/finance-payment-options/`, `/orthodontics/` | |
| Meta description 150–160 | **38 over 160** (worst 212 on `/what-is-airflow-teeth-cleaning/`, 206 on `/dental-implants-cost-rugby/`); several under 140 | |
| Unique meta descriptions | **7 pages share** "At Rugby Smiles, we pride ourselves on making you smile brighter…" (`/cosmetic-dentistry/`, `/smile-makeovers/`, `/bleeding-gums…/`, `/for-dentists/`, `/surprising-foods…/`, `/privacy-policy/`, `/transparency…/`) | |
| Image alt text | **116 images missing alt** across 59 pages; `/gallery/` 32, `/meet-the-team/` 8, `/invisalign/` 6 | |
| URL structure | Good: short, keyword-bearing, `-rugby` suffix where local. Legacy oddities: `/pricing-3/`, `/dentist-in-rugby-2/` | |
| Contextual internal links | Body links (nav/footer excluded) range 7–20 per page; the money pages `/invisalign/` (13) and `/emergency-dentist-rugby/` (8) receive few links *from* related content. `/dental-plans/`, `/nervous-patients/`, `/hygiene-airflow/` are the most-linked treatment pages | |
| Image format | Not measured per image; Lighthouse "modern image formats" audit below | |

### Ch6 — Backlinks
- Cannot be measured from this environment. **Action (Phase 1, Tim):** open Search Console → Links, or verify the site in the free Ahrefs Webmaster Tools, and export.
- Existing linkable-asset candidates: five interactive quizzes, the "NHS dentist in Rugby? The honest picture" page, the dental-treatment-abroad aftercare page, the Polish-language page. None are yet built as reference tools (calculators, downloadable guides).

### Ch7 — Technical and local
- **Duplicate URLs kept live and in the sitemap** with canonicals pointing elsewhere: `/sedation/` → `/iv-sedation/`, `/emergency-dentist-in-rugby/` → `/emergency-dentist-rugby/`, `/pricing-3/` → `/our-pricing/`. Canonicals mitigate, but they should be 301 redirects and removed from the sitemap.
- `/blog/` returns 404 while the homepage has a section "Learn more about oral care on our dental blog". Either create the blog (Phase 3 decision) or remove the link.
- `llms.txt` (generated by Yoast 28.1) lists `/dentist-in-rugby-2/` as the first page; that URL is not in the sitemap (status checked in Appendix B). Yoast picks these from "cornerstone"/recent settings, so it is fixable in Yoast.
- No `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `Referrer-Policy` or `Permissions-Policy` headers. Not a ranking factor, but Lighthouse best-practices flags some, and it is a 10-minute nginx change for the host.
- `og:locale` is `en_US` and schema `inLanguage` is `en-US`; the practice is in England. Set `en_GB` in Yoast/WordPress site language.
- Schema `aggregateRating` says 5.0 from 448 reviews while the Trustindex widget on the same page says 505 reviews. Keep the number synced (Trustindex can output the schema itself).
- **Local SEO:** not audited from here. **Action (Phase 4, Tim):** export the Google Business Profile (categories, services, attributes, Q&A, photos, posts, review count and response rate). Given 505 reviews the upside is in completeness and responses.
- **Lighthouse:** see Appendix B (filled from the sandbox run).

### Ch8 — AI search readiness
- Strong: FAQ schema on 36 pages, `Dentist` + `MedicalClinic` schema with CQC credential, languages and opening data, Q&A-style H2s ("Invisalign questions, answered honestly"), and an `llms.txt`.
- Missing: an AI-visibility baseline (which practices ChatGPT/Gemini/Perplexity name for "best dentist in Rugby", "Invisalign Rugby", "emergency dentist Rugby"), Bing indexation confirmation (ChatGPT reads Bing), and presence checks in local "best dentist in Rugby/Warwickshire" roundup articles.

### Ch9 — 30-day plan status
Week 1 items: Search Console ☐ · tools chosen ☐ · 10–15 keywords ☐ · intent tests ☐ · money pages identified ☑ (they exist). Nothing from weeks 2–4 has started. `PROCESS.md` maps the phases.

---

## Priority list (what to do first, and in which phase)

**Phase 1 (foundation, needs Tim ≈30 min):** Search Console access · Bing Webmaster Tools + IndexNow · keyword data route · confirm Invisalign as cluster 1.

**Phase 2 (money page + quick technical wins, mostly Claude then Tim in Yoast):**
1. Rewrite `/invisalign/` per the content blueprint; add reviewer byline and GDC number; alt text on its 6 untagged images.
2. Batch-fix titles >60 and descriptions >160 on the Invisalign cluster pages first, then the rest (Yoast bulk editor).
3. Replace the 7 shared meta descriptions.
4. Fix H1s on the 5 affected pages.
5. 301 the three duplicate URLs and drop them from the sitemap; fix or remove the `/blog/` link; fix `llms.txt` entry; set `en_GB`; remove the UA tag; sync review counts; correct the two homepage typos.

**Phase 3 (funnel):** commercial comparison page (Invisalign vs fixed braces / cost explained), upgrade `/how-invisalign-works/`, Invisalign cost calculator hosted on this repo, contextual links from every orthodontic page into `/invisalign/`.

**Phase 4 (promote/monitor):** Google Business Profile completeness and review responses · Source of Sources · AI-visibility baseline · alt text on the remaining 110 images (gallery first) · security headers.

---

## Appendix A — per-page crawl (status · title length · meta length · H1 count · words · images/without-alt · body links · FAQ schema)

| URL | tlen | dlen | H1 | words | img/noalt | links | FAQ |
|-----|------|------|----|-------|-----------|-------|-----|
| / | 62 | 152 | 1 | 2079 | 20/3 | 20 | Y |
| /invisalign/ | 57 | 180 | 1 | 1784 | 9/6 | 13 | Y |
| /how-invisalign-works/ | 59 | 191 | 1 | 1352 | 4/1 | 14 | Y |
| /which-invisalign/ | 74 | 174 | 1 | 1589 | 4/1 | 9 | - |
| /invisalign-quiz/ | 49 | 150 | 1 | 36 | 3/1 | 10 | - |
| /retainers-rugby/ | 59 | 142 | 1 | 727 | 4/1 | 10 | Y |
| /fixed-braces-rugby/ | 70 | 169 | 1 | 1410 | 6/3 | 11 | Y |
| /orthodontics/ | 79 | 174 | 2 | 1189 | 4/1 | 9 | Y |
| /dental-implants-in-rugby/ | 53 | 161 | 1 | 2627 | 16/1 | 13 | Y |
| /dental-implants-cost-rugby/ | 65 | 206 | 1 | 1036 | 4/1 | 13 | Y |
| /all-on-4-dental-implants-same-day-teeth/ | 55 | 182 | 1 | 1903 | 5/1 | 12 | Y |
| /dentures-vs-implants/ | 53 | 186 | 1 | 832 | 4/1 | 11 | Y |
| /dentures-clinical-dental-technician/ | 54 | 165 | 1 | 1944 | 7/1 | 8 | Y |
| /implant-quiz/ | 54 | 157 | 1 | 13 | 4/1 | 7 | - |
| /composite-bonding-in-rugby/ | 63 | 166 | 1 | 2505 | 10/1 | 11 | Y |
| /bonding-quiz/ | 67 | 185 | 1 | 50 | 4/1 | 10 | - |
| /veneers/ | 58 | 172 | 1 | 1510 | 5/1 | 15 | Y |
| /professional-teeth-whitening/ | 66 | 142 | 1 | 1529 | 4/1 | 10 | Y |
| /cosmetic-dentistry/ | 63 | 139* | 1 | 1980 | 18/1 | 16 | Y |
| /smile-makeovers/ | 60 | 139* | 1 | 419 | 7/4 | 7 | - |
| /facial-aesthetics-rugby/ | 71 | 153 | 1 | 604 | 4/1 | 9 | Y |
| /new-patient-check-up/ | 63 | 196 | 1 | 1722 | 4/1 | 12 | - |
| /general-dentistry/ | 76 | 187 | 1 | 1298 | 4/1 | 18 | Y |
| /hygiene-airflow/ | 65 | 154 | 1 | 2119 | 8/1 | 16 | Y |
| /what-is-airflow-teeth-cleaning/ | 68 | 212 | 1 | 755 | 4/1 | 11 | Y |
| /childrens-dentist-rugby/ | 76 | 200 | 1 | 1280 | 4/1 | 16 | Y |
| /dental-plans/ | 60 | 160 | 1 | 1197 | 4/1 | 10 | - |
| /our-pricing/ | 55 | 164 | 1 | 1354 | 4/1 | 14 | Y |
| /finance-payment-options/ | 73 | 187 | 2 | 915 | 4/1 | 16 | Y |
| /emergency-dentist-rugby/ | 69 | 165 | 1 | 1133 | 4/1 | 8 | Y |
| /tooth-extraction-rugby/ | 68 | 195 | 1 | 1044 | 4/1 | 11 | Y |
| /root-canal-treatment/ | 56 | 178 | 1 | 1528 | 4/1 | 12 | Y |
| /composite-filling/ | 55 | 170 | 1 | 1197 | 4/1 | 13 | Y |
| /dental-crown-dental-bridges/ | 68 | 187 | 1 | 1353 | 4/1 | 13 | Y |
| /gum-disease-treatment-rugby/ | 56 | 190 | 1 | 1340 | 4/1 | 9 | Y |
| /bleeding-gums-whole-body-health/ | 52 | 139* | 1 | 463 | 4/1 | 11 | - |
| /jaw-pain-tmj-treatment-rugby/ | 67 | 150 | 1 | 717 | 4/1 | 11 | Y |
| /sports-mouthguards-rugby/ | 59 | 156 | 1 | 507 | 4/1 | 10 | Y |
| /nervous-patients/ | 67 | 165 | 1 | 2187 | 4/1 | 9 | - |
| /nervous-quiz/ | 56 | 154 | 1 | 754 | 4/1 | 7 | - |
| /iv-sedation/ | 69 | 200 | 1 | 1107 | 4/1 | 11 | Y |
| /nhs-dentist-rugby/ | 55 | 197 | 1 | 1467 | 4/1 | 13 | Y |
| /dental-treatment-abroad-aftercare/ | 62 | 180 | 1 | 777 | 4/1 | 10 | Y |
| /dentysta-rugby/ | 45 | 180 | 1 | 520 | 4/1 | 8 | Y |
| /surprising-foods-that-are-high-in-sugar-how-to-avoid/ | 66 | 139* | 0 | 736 | 7/4 | 8 | - |
| /treatment-quiz/ | 54 | 176 | 1 | 13 | 5/1 | 7 | - |
| /meet-the-team/ | 49 | 123 | 1 | 2252 | 18/8 | 10 | - |
| /about-us/ | 39 | 160 | 1 | 791 | 8/1 | 13 | - |
| /testimonials/ | 49 | 200 | 0 | 82 | 4/1 | 7 | - |
| /gallery/ | 47 | 192 | 0 | 85 | 36/32 | 7 | - |
| /contact-us/ | 46 | 182 | 1 | 335 | 5/1 | 12 | - |
| /for-dentists/ | 53 | 139* | 1 | 532 | 5/0 | 7 | - |
| /thanks/ | 38 | 199 | 1 | 32 | 4/1 | 7 | - |
| /privacy-policy/ | 43 | 139* | 1 | 2077 | 4/1 | 7 | - |
| /transparency-data-and-national-opt-out-policy/ | 62 | 139* | 1 | 451 | 4/1 | 7 | - |
| /sedation/ (canonical → /iv-sedation/) | 69 | 200 | 1 | 1107 | 4/1 | 11 | Y |
| /emergency-dentist-in-rugby/ (canonical → /emergency-dentist-rugby/) | 69 | 165 | 1 | 1133 | 4/1 | 8 | Y |
| /pricing-3/ (canonical → /our-pricing/) | 55 | 164 | 1 | 1354 | 4/1 | 14 | Y |
| /blog/ | 404 | | | | | | |

`*` = the shared boilerplate description. All pages report `dateModified` 2026-09-04, i.e. a site-wide save the day before the crawl.

## Appendix B — Lighthouse and probe results

_Pending: filled in below once the sandbox run completes._
