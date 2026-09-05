# Rugby Smiles SEO & AI-Search Playbook

**Source:** "The Complete SEO & AI SEO Course for 2026 (Full Beginner's Guide)" — Surfer Academy (presented by Matt Kenyon), published 16 Apr 2026, 50:46, https://youtu.be/7DRO4rEIHDk
**Purpose:** A faithful, chapter-by-chapter distillation of the video, followed in each chapter by a clearly-marked *"Rugby Smiles translation"* that adapts the principle to a local private dental practice. Anything under a *translation* heading is our adaptation, not the presenter's words.
**Companion files:** `TOOLS.md` (every tool named, and API status), `AUDIT.md` (where rugbysmiles.co.uk sits today), `PROCESS.md` (how Tim and Claude work through this, one step at a time).

The presenter's one-sentence thesis, repeated at open and close:

> "SEO is not competing with AI search. It's the foundation AI search is built on."

---

## Chapter map (video timestamps)

| # | Chapter | Starts | Core idea |
|---|---------|--------|-----------|
| 1 | What SEO actually is | 00:00 | Show up wherever people search; crawl → index → rank; business goal, not SEO goal |
| 2 | Mastering search intent | 05:33 | Four intents; Google the keyword and read the top 10 |
| 3 | Finding the right keywords | 10:00 | Keyword Sweet Spot; ideation → validation → clustering; money pages first |
| 4 | Creating content that ranks | 23:43 | Research → structure → write → optimise; human layer is the moat |
| 5 | On-page SEO | 30:06 | Title, headers, URL, meta, internal links, images |
| 6 | Backlinks | 35:24 | Be the source; journalist queries; linkable assets |
| 7 | Technical SEO | 39:37 | Screaming Frog; local SEO = Google Business Profile + reviews |
| 8 | AI search | 41:34 | Same fundamentals; track brand mentions; earn "best of" placements |
| 9 | 30-day plan | 48:02 | Foundation → money page → first funnel → promote & monitor |
| 10 | What's next | 50:02 | Fundamentals unchanged; start free |

---

## Chapter 1 — What SEO actually is (00:00–05:33)

**What the video says**

- Framing facts: Google still processes billions of searches a day, search volume grew 20% last year, and Google sends roughly 190× more traffic to websites than ChatGPT. Google is not shrinking; how people find information is changing.
- Two places a business must now show up: traditional search and AI-powered search. The AI assistants are built on top of traditional search infrastructure: ChatGPT uses Bing's index when it searches the web; Perplexity runs its own crawler but leans on Bing's index; all of them crawl the pages that already rank. If you are not in Google or Bing you are probably invisible to AI assistants.
- Definition adopted: "search everywhere optimization" (Ashley Liddell). SEO is getting your website to show up wherever people search for things related to your business or the solutions you provide. Everything else is detail.
- Google works in three steps: **crawl** (bots follow links and read code), **index** (Google stores what it finds; not indexed means cannot rank), **rank** (order by relevance, trustworthiness, usefulness).
- Today's results page: AI Overview at top, sponsored ads, organic results, People Also Ask, video carousels, local map pack when there is a location angle, knowledge panels. Strategy must reflect that it is no longer "ten blue links".
- Do not set an SEO goal. Set a business goal (customers, revenue, leads). SEO reaches people at the exact moment of looking; the difference from social ads is **intent**, not interruption.
- Three worked examples run through the video: PandaDoc (SaaS), Counter Culture Coffee (e-commerce), Huntress (cybersecurity). Principles are the same; decisions change with the business.
- The one question asked before touching any website: *What are people actually searching for, and what do they want when they search it?*

**Rugby Smiles translation**

- Business goal, not SEO goal: new-patient bookings and high-value treatment consultations (Invisalign, implants, bonding). Every SEO task must trace to one of those.
- The local map pack is a first-class result type for us. "dentist rugby", "invisalign rugby", "emergency dentist near me" all trigger it. Chapter 7's local SEO note therefore matters more for us than for the video's three example businesses.
- Being in Bing's index is a prerequisite for ChatGPT visibility. That is a concrete, free action (Bing Webmaster Tools, see `TOOLS.md`).

---

## Chapter 2 — Mastering search intent (05:33–10:00)

**What the video says**

- The single most important concept in SEO. Every search is looking for something specific; the job is to work out what and give it to them.
- Four intents, with the video's examples:
  - **Informational** — "how to train your puppy" — wants to learn.
  - **Commercial** — "best dog training classes" — willing to spend, comparing options.
  - **Transactional** — "dog training class near me sign up" — ready to buy.
  - **Navigational / branded** — "petsmart dog training" — using Google as a taxi to a known brand.
- How to determine intent: Google the keyword and look at what ranks. The top 10 results are Google telling you what the searcher wants. Match that intent and do it better. (SERP = search engine results page; every keyword has one and they change.)
- Rule of thumb: the shorter the keyword, the more competitive, higher volume and less useful ("coffee" ≈ 650k US searches/month; the SERP is a mess). Longer, specific phrases (**long-tail**) have lower volume, clear intent, manageable competition, and add up. Newer sites start on the long tail and work up.
- Exercise set by the presenter: Google your main keyword, note what type of content ranks (blog posts, product pages, tools, videos). That is the intent. Keep the note for later.
- AI era: AI Overviews now appear on commercial and transactional searches, not just informational. Buying decisions can happen with zero clicks. Content must go deeper than the summary to earn the click; surface-level content will not cut it.

**Rugby Smiles translation**

- Our intent map:
  - Transactional: "dentist rugby", "emergency dentist rugby", "invisalign rugby", "book dentist rugby", "hygienist rugby".
  - Commercial: "invisalign cost uk", "invisalign vs fixed braces", "composite bonding vs veneers", "best dentist in rugby", "dental implants cost".
  - Informational: "how does invisalign work", "is airflow cleaning worth it", "bleeding gums causes", "what to do about a chipped tooth".
  - Branded: "rugby smiles", "rugby smiles reviews", "tim bond dentist".
- The 30-second intent test (Google it, read the top 10) is Tim's job in a normal browser; Claude cannot reach Google's results page from this environment. Results are recorded in `AUDIT.md` / `CLAUDE.md`.

---

## Chapter 3 — Finding the right keywords (10:00–23:43)

**What the video says**

- A keyword is whatever someone types; length is irrelevant.
- **Keyword Sweet Spot** — four attributes that make a keyword worth targeting:
  1. **Demand** — are people actually searching it?
  2. **Fit** — where does it sit in your funnel; is it relevant to what you sell and who you reach?
  3. **Intent** — what does the searcher want, and can you satisfy it (if the SERP is YouTube videos, you need a video)?
  4. **Difficulty** — can you realistically rank given current authority? A new site will not beat Amazon for "running shoes" but might for "best running shoes for flat feet in winter".
  Keywords scoring on all four are unicorns; prioritise them when found.
- Funnel examples: PandaDoc ranks for "contract template" (~300k/month, top of funnel) and converts via template download → email capture → nurture → signup. Counter Culture ranks for "pour over coffee" (~34k), "pour over coffee ratio", "cold brew ratio", "coffee brewing methods" with educational brew guides, building authority so sales follow. **A keyword without a conversion path is wasted traffic; a keyword with one is an automated pipeline.**
- Keyword research in three disciplines:
  1. **Ideation** (rapid-fire techniques): Google Search Console (the single best source: real queries that already find your site); Google autocomplete; People Also Ask (click one, more appear); "People also search for" at the bottom of results; subreddits where customers describe problems in their own words; paste your sitemap into ChatGPT and ask for content gaps; paste a competitor's sitemap and ask what they cover that you do not; ask an AI for "30 questions someone would ask before buying [category]"; the free **Keyword Surfer** Chrome extension for volume, CPC and related ideas inside Google.
  2. **Validation**: assess volume, difficulty, business fit and intent to decide what to target first. Two routes: DIY (connect an SEO data API to an AI coding tool and have it pull volumes, difficulty and intent) or Surfer's keyword validation screen (paste keywords in, get the data).
  3. **Clustering**: group keywords that are topically related or that Google treats as the same meaning. Surfer Keyword Research maps clusters from a seed topic.
- **Prioritisation framework** (bottom of funnel upward):
  1. **Money pages first** — pages that directly convert: product, service, pricing, feature pages; transactional/commercial keywords. Go *wide* here: a foundation across all topics. Most brands go wrong by writing ten blog posts first and wondering why nobody buys.
  2. **Pick one topical cluster connected to a money page and build the full funnel** — money page (transactional) → comparison/"best" content (commercial) linking to it → educational content (informational) feeding down. Everything internally linked. This is a topic cluster.
  3. **Repeat cluster by cluster; finish one before starting the next.** Spreading across many clusters prolongs results. Google evaluates whether the site covers the whole journey ("how to prevent ransomware" is checked against "what is ransomware", "signs your network is compromised", "incident response checklist"). Comprehensive coverage = **topical authority**, which makes every keyword in the cluster easier, including the competitive ones.

**Rugby Smiles translation**

- Our money pages already exist (see `AUDIT.md`): Invisalign, dental implants, composite bonding, new-patient check-up, emergency dentist, hygiene/Airflow, pricing, dental plan. Step 1 is therefore *optimise* wide, not *create*.
- First cluster candidate: **Invisalign** (Tim is the practice's Invisalign lead, it is the highest-value elective treatment, and supporting pages already exist: how-invisalign-works, which-invisalign, invisalign-quiz, retainers, fixed-braces). Decision confirmed or changed at the Phase 1 gate in `PROCESS.md`.
- Conversion path for every page: free consultation / £45 check-up / 60-second quiz → Dentally online booking or phone. Informational pages must carry that path or they are vanity traffic.
- Claude is the "AI coding tool connected to an SEO data API" in the DIY route. The API decision (Surfer vs DataForSEO vs GSC-only) is Gate 1 in `PROCESS.md`.

---

## Chapter 4 — Creating content that ranks (23:43–30:06)

**What the video says**

- Four phases: **research → structure → write → optimise**.
- **Research**: open the top five results for the target keyword and read all of them. Look for (1) topics they all cover — table stakes you must cover too; (2) what they missed — your opportunity; (3) average length — a benchmark, not a rule, but 500 words against 3,000-word guides is not comprehensive; (4) unique angles — where to differentiate. Do this manually for your first few pieces so you understand what you later automate. Surfer's Content Editor automates it (topics, terms, required depth) in about 60 seconds.
- **Structure**: build an outline before writing; do not skip. Feed research notes to Claude or ChatGPT for a draft outline, or generate a search-optimised outline in Surfer.
- **Write**: AI writes well now. Let it handle scaffolding, basic definitions, research and sentence flow (Surfer AI starts from a search-informed draft). Then add what AI cannot:
  - your **experience** (what actually happened when you tried the thing),
  - your **opinion** (overrated, underrated, wrong),
  - **original data** (results, case studies, customer conversations),
  - **expert insights** (interviews, quotes; may be sourced from podcasts, books, journals),
  - **specific examples** (real businesses, numbers, outcomes).
- **Optimise**: Surfer's real-time Content Score (0–100) tracks topic coverage, terms and depth for both traditional and AI search. Aim to beat the highest score shown on the dashboard; Surfer's data says pages clearing that threshold rank better.
- Why the human layer matters: Ahrefs' study of 14 billion pages found over 96% get zero Google traffic. Most content fails because it is the same as everything else. The bar is at least five times better than what exists for that search. Every business has unique knowledge in its people; if not, interview experts, read books and journals, go where AI content mills cannot. That is the content moat.

**Rugby Smiles translation**

- Our human layer is unusually strong: a working dentist writing about treatments he performs, real before/after cases (with consent), real prices, real patient objections (the Invisalign page already uses "three doubts, answered by our patients"). This is exactly the differentiation the video calls for; the playbook is to systematise it.
- Health content carries E-E-A-T expectations: author byline (Dr Tim Bond, GDC number), reviewed date, sources. The video's "expert insights" step is mandatory for us, not optional.
- Division of labour: Claude does research, outline, first draft and on-page checklist; Tim adds clinical experience, opinion, cases and signs off. Never publish a page Tim has not read.

---

## Chapter 5 — On-page SEO (30:06–35:24)

**What the video says** (demonstrated on Huntress' ransomware recovery guide and managed EDR product page: same checklist, different execution)

1. **Title tag** — include the target keyword, keep under 60 characters, make it compelling to click. Educational page: front-load the keyword ("Ransomware Recovery Guide for Businesses"). Money page: keyword-rich but benefit-driven because it sells.
2. **Header tags** — one H1 per page, ideally mirroring the title tag. H2s for main sections, H3s for subsections, keywords used naturally. Google and LLMs read the hierarchy; humans use it to skim.
3. **URL** — short, descriptive, includes the keyword (e.g. `/cybersecurity-101/ransomware-recovery-guide`, `/platform/managed-edr`). Never random strings.
4. **Meta description** — 150–160 characters, not a direct ranking factor but affects clicks. Action-oriented, includes the keyword, says what they will get. Write it like ad copy.
5. **Internal linking** — contextual links in the body to related pages and to money pages; this is how clusters connect and how Google discovers and relates pages. "One of the best effort-to-value ratios of any SEO tactic. I beg you, do not skip this step." Surfer's auto internal links feature can do it.
6. **Image optimisation** — descriptive file names, alt text that describes the image as if to someone who cannot see it (screen-reader users depend on it), compressed files, WebP preferred. Even well-optimised sites repeat generic alt text and leave this on the table.

**Rugby Smiles translation**

- This is a checklist we can run mechanically across all 59 pages using the crawl in `AUDIT.md`: title length, one H1, meta length, alt text, and contextual body links (not just menu links) to the money pages.
- Elementor pages tend to produce menu-heavy but body-link-light HTML; the crawl measures body links with header/footer/nav stripped for that reason.

---

## Chapter 6 — Backlinks (35:24–39:37)

**What the video says**

- Backlinks are votes of confidence from other sites. Quality matters far more than quantity (an industry publication beats a random directory). It is the hardest part of SEO, it is outside your control, and there are no shortcuts that do not eventually get penalised.
- The presenter's belief: genuinely great content (original data, unique insight, practical tools) earns links more naturally than people think; outreach is fine but the best links came from making something worth linking to.
- Three practical tactics:
  1. **Be the source** — original data, analysis or resources journalists and bloggers cite (Counter Culture's brew guide is linked by WikiHow, Gear Patrol, Breville; Huntress research is cited by Google Cloud threat intelligence and Wikipedia).
  2. **Journalist query platforms** — sign up to **Source of Sources** (free, by the founder of HARO). Journalists post queries; you reply with quotes; when published you get a link. Most accessible tactic for beginners; ~15 minutes a day; a numbers game (maybe 1 in 100). Week 4 of the plan also names **featured.com**.
  3. **Linkable assets** — free tools, calculators, templates, definitive guides that become reference material. With Claude Code or Codex a non-technical marketer can build a browser-based tool in minutes (the presenter built an inventory calculator in ~10 minutes). Example: "coffee to water ratio calculator" has ~500 searches/month at difficulty 8 and would earn links from every blog citing the ratio guides.
- If you are starting out, do not obsess over links yet. Publish 10–15 great pieces first, then start with journalist queries. Links compound.

**Rugby Smiles translation**

- Linkable assets are our best lever, and this GitHub Pages repository is a ready host for them. Candidates: Invisalign cost calculator, dental plan vs pay-as-you-go calculator, "is my tooth an emergency?" triage guide, sugar-in-drinks checker. The five existing quizzes are proto-assets already.
- Local link sources the video's examples do not have: Rugby Borough Council business listings, local press (Rugby Advertiser, Rugby Observer), rugby clubs (sports mouthguards page), schools, CQC listing, Invisalign doctor locator, professional bodies.
- Source of Sources arrives by email; the Gmail connector attached to this workspace can be used to surface health/dental queries for Tim to answer. That is a Phase 4 task in `PROCESS.md`.

---

## Chapter 7 — Technical SEO (39:37–41:34)

**What the video says**

- Can be a mess on enterprise sites, but a small or medium business on WordPress, Webflow or Shopify is "probably 90% of the way there already".
- One instruction instead of a long list: download **Screaming Frog SEO Spider** (free up to 500 URLs), point it at the site, get a prioritised list of technical issues: broken links, missing title tags, duplicate content, redirect chains, images without alt text.
- **Local SEO** (for any physical location): a huge separate topic, but the most important thing is to claim your **Google Business Profile**, fill out every field, get as many reviews as possible, and respond to every review. That alone can put you in the map results for "[category] near me".
- Technical is not what holds beginners back; not having published anything is.

**Rugby Smiles translation**

- We are WordPress + Elementor + Yoast: the "90% there" case. The equivalent of the Screaming Frog run has been done (59 pages, results in `AUDIT.md`); a licensed Screaming Frog is only needed if we want scheduled crawls.
- Google Business Profile is arguably our single highest-leverage item: 505 Google reviews already exist, so the task is completeness of the profile, review velocity, review responses, and consistency of name/address/phone with the site's schema.

---

## Chapter 8 — AI search, the new frontier (41:34–48:02)

**What the video says**

- Google handles over 5 trillion searches a year, but there is now a second set of search engines: ChatGPT, Gemini, Perplexity, Copilot, Claude, Grok, Google AI Mode. People ask them for recommendations ("best CRM for small business") and they answer conversationally, recommending specific brands.
- Exercise: in an incognito window, ask ChatGPT a question your target audience asks during their buying journey, one likely to trigger brand names. Whatever appears is your AI competition. (Incognito matters because ChatGPT personalises.)
- AI assistants synthesise and cite; they choose sources by **authority, relevance, and how clearly the content answers the question**. The same things that rank in Google (authoritative content, clear structure, schema markup, being cited by other sites) drive AI visibility.
- Measurement gap: Google Search Console cannot see traffic from ChatGPT or Perplexity, and nobody outside OpenAI/Perplexity has the query data. What you *can* do is monitor whether your brand appears in AI answers. Surfer's **AI Tracker** runs queries across ChatGPT, Gemini and Perplexity and tracks which brands are recommended, how it shifts, and where competitors appear and you do not.
- Four actions:
  1. Comprehensive, authoritative content with clear subheadings and **direct answers to specific questions** (LLMs pull from what they can parse). Surfer's Content Editor now shows an **AI search score** beside the content score.
  2. Build topical authority through clusters (definition, how-to, comparison, deep dive) so models recognise you as the authority.
  3. Earn citations from authoritative sources. AI assistants especially favour **"best of" roundup articles**: get placed in them, or write them yourself. Surfer's **mention gap report** shows queries where competitors are cited and you are not; filter for gaps to get an outreach list.
  4. Check AI visibility regularly (manually or with a tracker). Recommendations shift a lot over time.
- Conclusion: AI search optimisation is not a separate discipline. It is the fundamentals done well.

**Rugby Smiles translation**

- Our AI test questions: "best dentist in Rugby", "where can I get Invisalign in Rugby Warwickshire", "how much does Invisalign cost in the UK", "emergency dentist near Rugby", "is composite bonding worth it". Tim runs these incognito; Claude can also run them through model APIs on a schedule (see `TOOLS.md`).
- Our FAQ schema, Dentist schema and plain-English Q&A sections are exactly the "direct answers" format. Extend them to every treatment page.
- "Best dentist in Rugby" roundups: identify who publishes them (local directories, news sites, "top 10 dentists in Warwickshire" listicles) and make sure we are present and accurate.

---

## Chapter 9 — The 30-day plan (48:02–50:02)

**What the video says** (verbatim structure)

**Week 1 — Foundation**
- Set up Google Search Console (free, essential).
- Set up Surfer or choose your tools; do keyword research.
- Find 10–15 target keywords using the Keyword Sweet Spot framework.
- Analyse search intent for the top 5 (the 30-second intent test).
- Identify your money pages: which pages directly convert? Do they exist yet?

**Week 2 — Your most important money page**
- Write and publish your single most important money page, or optimise the existing one.
- Follow the content blueprint: research, structure, write, optimise.
- Apply the on-page checklist: title, meta, headers, internal links, images.
- Everything else you build will link back to this page. Additional money pages are an ongoing priority, not a one-week sprint.

**Week 3 — Your first funnel**
- Pick one topical cluster connected to the money page.
- Publish a mid-funnel or top-of-funnel piece that supports it; internally link it to the money page and related pages.
- If you already have content, updating a page ranking on page 2–3 is often faster than writing new.

**Week 4 — Promote and monitor**
- Respond to journalist queries on Source of Sources or featured.com, 15 minutes a day.
- Check AI visibility (manually or with a tracker).
- Review Search Console for early signals: impressions rising even if clicks are not, new keywords appearing, positions moving from page 5 to page 3.
- Plan your next cluster, not your next random topic.

You will not see results in 30 days, but you will have the foundation, the right keywords, optimised content, and a system for creating more.

**Rugby Smiles translation** — this becomes the phase structure in `PROCESS.md`, adjusted for the fact that our money pages and 505 reviews already exist.

---

## Chapter 10 — What's next (50:02–50:46)

- Find what people search for. Create the best content for that search. Earn trust. The fundamentals have not changed in 20 years; what has changed is that the same work now makes you visible in Google, AI Overviews, ChatGPT and Perplexity.
- Start with the free Keyword Surfer extension and go from there.

---

## The playbook in one page (our operating rules, derived from the above)

1. Every task traces to bookings or consultations. No vanity keywords.
2. Money pages first, then one cluster at a time, finished before the next.
3. Intent is decided by reading the actual results page, not by guessing.
4. Research → outline → draft → human layer → optimise → on-page checklist → internal links. No page skips a step.
5. Tim's clinical experience, cases and opinions are the moat. Claude never fabricates them.
6. Direct answers under clear headings, with FAQ and Dentist schema, on every treatment page.
7. Google Business Profile completeness and review responses are treated as SEO work.
8. Build linkable assets (calculators, guides) rather than buying links. Answer journalist queries 15 minutes a day once 10–15 strong pages exist.
9. Be indexed in Bing as well as Google, because ChatGPT reads Bing.
10. Measure in Search Console (impressions, new queries, position shifts) and by periodic AI-answer checks. Expect months, not weeks.
