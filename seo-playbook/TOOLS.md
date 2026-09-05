# Tools named in the video, and how we can use each (API status as of 5 Sep 2026)

Legend: **API** = programmatic access Claude can use unattended · **Manual** = Tim operates it in a browser and shares exports/screenshots · **Gate** = needs a decision or access from Tim before use.

## A. Tools the presenter explicitly recommends

| Tool | Where in video | What it does for the playbook | Cost | Automation / API | Our plan |
|------|----------------|-------------------------------|------|------------------|----------|
| **Google Search Console** | Ch3 ideation ("single best source"), Ch9 week 1 & 4 | Real queries that already find the site; impressions, positions, indexing status | Free | **API** — Search Console API is free; OAuth or a service account added as a user on the property; ~50k rows/day per property, 25k rows/request. Community MCP servers exist. | **Gate 1a:** Tim confirms the property exists and adds a service-account email Claude generates, or exports Performance → CSV monthly. |
| **Keyword Surfer** (Chrome extension) | Ch3 ideation, Ch10 | Volume, CPC, related keywords and fan-out questions shown inside Google; also shows ChatGPT fan-out questions | Free (updated Jan 2026) | **Manual** — browser extension only, no API. | Tim installs it and uses it during the 30-second intent tests; screenshots or notes go into `keywords/`. |
| **Surfer** — Keyword Research (clustering) | Ch3 validation & clustering | Paste keywords → volume, difficulty, intent; seed topic → full cluster map | Paid. Sources disagree on current tiers (Essential ~$79–99/mo, Scale/Pro ~$175–182/mo, higher tiers to $999). | **API only on Enterprise** (~$999/mo). Lower tiers are UI + CSV export. | **Gate 1b:** subscribe to the entry tier for 1–2 months during Phases 1–3, or take the DIY route below. |
| **Surfer** — Content Editor (Content Score, AI search score, outline, auto internal links) | Ch4, Ch5, Ch8 | Analyses top-ranking pages, gives a 0–100 coverage score plus AI-search score, generates outlines, inserts internal links | Same subscription | UI; Google Docs / WordPress integrations exist | Same gate. Claude can reproduce the *research* step (read top 5, list table-stakes topics and gaps) but not Surfer's proprietary score. |
| **Surfer AI** (drafting) | Ch4 | Search-informed first draft | Add-on credits | UI | Optional. Claude drafts from research notes instead; Tim adds the human layer either way. |
| **Surfer AI Tracker** + **Mention Gap report** | Ch8 | Tracks brand mentions across ChatGPT, Gemini, Perplexity; shows queries where competitors are cited and we are not | Paid add-on/tier | UI | Optional. DIY equivalent below. |
| **ChatGPT / Claude** (as assistants) | Ch3 (sitemap gap analysis, "30 questions before buying"), Ch4 (outlines) | Ideation, gap analysis, outlining, scaffolding | Free tiers exist | **API** — Claude is already here; this session *is* the AI coding tool the video describes | Use directly, every phase. |
| **Reddit** (subreddits) | Ch3 ideation | Customers' own phrasing of problems | Free | Reddit API needs an app registration; browsing is enough | Manual/occasional. UK dental questions also live on Mumsnet, Facebook groups, and Google's People Also Ask. |
| **"An SEO data API connected to an AI coding tool"** (DIY validation route) | Ch3 validation | Volumes, difficulty, intent classification without Surfer | e.g. **DataForSEO**: pay-as-you-go, $50 minimum deposit, ~$0.0006/request standard queue; Keywords Data API (volume, CPC) and Labs API (difficulty, related, competitor keywords). Google Ads Keyword Planner API is the free alternative but requires an Ads account and developer token. | **API** | **Gate 1b alternative:** Tim opens a DataForSEO account and stores the login/API credentials somewhere Claude can use them (never pasted into a public repo). Claude then runs validation in the sandbox. |
| **Source of Sources** (sourceofsources.com) | Ch6 tactic 2, Ch9 week 4 | Free journalist-query digest by Peter Shankman (HARO founder), up to 3 emails a day; reply directly to the journalist | Free | No API; email only. Gmail connector is attached to this workspace, so Claude can search the inbox for SOS digests and filter dental/health queries. | Phase 4. Tim subscribes with info@rugbysmiles.co.uk; Claude triages. |
| **featured.com** | Ch9 week 4 | Expert-answer platform that places quotes in publications | Free tier + paid | Not verified in this session; treat as **Manual** until checked | Phase 4, secondary to SOS. |
| **Claude Code / Codex** (vibe-coding linkable assets) | Ch6 tactic 3 | Build calculators and free tools that attract links | Included | **This session.** The GitHub Pages repo (mothybond80.github.io) is a free static host for such tools, embeddable into WordPress via iframe. | Phase 3/4: Invisalign cost calculator first. |
| **Screaming Frog SEO Spider** | Ch7 | Crawl the site; broken links, missing titles, duplicates, redirect chains, missing alt text | Free ≤500 URLs (site has 59); £199/yr licence for CLI, scheduling, GSC/PSI integrations, saved crawls | CLI only with licence; a community MCP server exists (bzsasson/screaming-frog-mcp). | Not needed yet: Claude ran an equivalent crawl from the sandbox (see `AUDIT.md`). Tim can run the free GUI quarterly for a second opinion. |
| **Google Business Profile** | Ch7 local SEO | Claim, complete every field, gather and respond to reviews → map pack | Free | **Gated API** — Business Profile APIs start at zero quota; you must apply, profile active 60+ days, website domain matching the email domain, review takes days to weeks. | **Manual first** (Tim), API application later if we want automated review-response drafting. |
| **Bing Webmaster Tools** (implied: "ChatGPT uses Bing's index") | Ch1, Ch8 | Be indexed where ChatGPT and Copilot look; IndexNow pushes new/updated URLs instantly | Free | **API** with key; **IndexNow** is built into Yoast SEO (already installed on the site) | Phase 1: Tim verifies the site (can import from Search Console in one click) and enables IndexNow in Yoast. |
| **Ahrefs** (cited for the 96%-zero-traffic study) | Ch4 | Not recommended as a tool per se | Ahrefs Webmaster Tools is free for a verified own site | — | Optional free backlink/health check. |

## B. Manual checks the presenter asks the viewer to do (no tool)

- **30-second intent test**: Google the keyword, read what ranks (Ch2). Tim, normal browser.
- **AI competition test**: incognito ChatGPT, ask a buying-journey question that triggers brand names (Ch8). Tim, incognito browser. Claude can supplement with model APIs (below).
- **Read the top 5 results in full** before writing (Ch4). Claude does this from the sandbox; Tim spot-checks.

## C. Useful additions not in the video (kept minimal, all free)

| Tool | Why | Access |
|------|-----|--------|
| **PageSpeed Insights / Lighthouse** | Core Web Vitals; the technical side Screaming Frog does not cover | Free API with a Google Cloud key (keyless quota was exhausted today); Lighthouse also runs from the sandbox |
| **Model APIs for AI-visibility checks** (OpenAI with web search, Gemini with grounding, Perplexity, Anthropic) | DIY version of Surfer's AI Tracker: run our 10 test questions weekly and log which practices are named | Pay-per-use; keys held by Tim, never in the repo |
| **Yoast SEO** (already installed) | Sitemaps, IndexNow, schema, titles/meta; the on-page checklist can be executed here | Already on site |

## D. What is already on rugbysmiles.co.uk (found in the audit)

WordPress 7.1 · Elementor 4.1.2 + Elementor Pro · custom theme "rugbysmiles" · Yoast SEO · Contact Form 7 · Qi Addons · Qode Essential Addons · Max Mega Menu · Safe SVG · WP-Optimize · nginx · GA4 (G-V357CZKBB1) · Google Tag Manager (GTM-5B6T5JNZ) · a legacy Universal Analytics tag (UA-100582723-1, dead since 2024, should be removed) · Meta Pixel · Microsoft Clarity · Trustindex Google-reviews widget (505 reviews) · LeadConnector chat widget (GoHighLevel) · Dentally online booking (rugby-smiles-dental-clinic.portal.dental) · WhatsApp link · Vimeo embeds.

## E. Decision summary for Tim (Gate 1, before Phase 1 ends)

1. **Search Console access:** service account (Claude pulls data itself) or monthly CSV export?
2. **Keyword data:** Surfer entry tier for 1–2 months, or DataForSEO pay-as-you-go (~£40 deposit covers our scale for months), or GSC-only for now?
3. **Bing Webmaster Tools:** approve Tim spending 10 minutes to verify and switch on IndexNow.
4. **Credentials policy:** nothing secret is ever committed to this public repository. Keys live with Tim or in a private store.
