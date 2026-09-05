# CLAUDE.md — persistent memory for the Rugby Smiles SEO project

Read this first in every session. Then open `seo-playbook/PROCESS.md`, find the first unticked box, and do only that.

## Who and what

- **Tim Bond** (info@rugbysmiles.co.uk) — principal Invisalign and cosmetic dentist and owner of Rugby Smiles Dental Clinic, 3 Newbold Road, Rugby, Warwickshire. Legal entity "Tim Bond Limited". Practice established 2006, CQC registered (location 1-18626135828). Phone 01788 579 577.
- **The website under optimisation is https://rugbysmiles.co.uk** (WordPress 7.1 + Elementor Pro + Yoast, nginx, 59 pages, 0 blog posts). It is *not* this repository.
- **This repository (mothybond80.github.io)** is Tim's GitHub Pages site. Before this project it only hosted a Tesla Fleet API public key at `.well-known/appspecific/com.tesla.3p.public-key.pem` and a 95-byte `index.html`. Do not remove those. From now on it also holds the SEO playbook (`seo-playbook/`) and will host linkable assets (calculators) to embed in WordPress. It is public: never commit credentials, patient data, or unpublished clinical photos.
- Booking runs through Dentally (rugby-smiles-dental-clinic.portal.dental). Chat widget is LeadConnector (GoHighLevel). Reviews widget is Trustindex (505 Google reviews, "Excellent"); Dentist schema claims 5.0 from 448 reviews (should be kept in sync). Trustpilot: 4.3 from 9 reviews.

## The playbook source

Video: "The Complete SEO & AI SEO Course for 2026 (Full Beginner's Guide)", Surfer Academy (Matt Kenyon), 16 Apr 2026, 50:46, https://youtu.be/7DRO4rEIHDk. Full distillation in `seo-playbook/PLAYBOOK.md`. Ten chapters: what SEO is; search intent; keywords (Sweet Spot = demand, fit, intent, difficulty; money pages first, then one cluster at a time); content (research → structure → write → optimise; human layer is the moat); on-page checklist; backlinks (be the source, Source of Sources, linkable assets); technical (Screaming Frog, Google Business Profile); AI search (same fundamentals, track mentions, "best of" roundups); 30-day plan; next steps.

## Decisions taken

- Documents live in `seo-playbook/`: `PLAYBOOK.md`, `TOOLS.md`, `AUDIT.md`, `PROCESS.md`. Keyword work will go in `seo-playbook/keywords/`. Assets (calculators) will go in `tools/`.
- Default first cluster: **Invisalign**; default first money page: `/invisalign/`. Awaiting Tim's confirmation (Gate 1).
- The raw video transcript is *not* committed (copyright); chapter notes with timestamps are in the playbook.
- Claude can reach rugbysmiles.co.uk and YouTube only through the Higgsfield `sandbox_exec` tool (the session's own network blocks both). Use the sandbox for crawls, Lighthouse, and transcript work.

## Open gates (need Tim)

1. Search Console access: service account or CSV export?
2. Keyword data: Surfer entry tier vs DataForSEO pay-as-you-go vs GSC-only?
3. Bing Webmaster Tools verification + IndexNow in Yoast (10 minutes).
4. Confirm first cluster and money page.

## Audit headline (5 Sep 2026) — details in `seo-playbook/AUDIT.md`

Strong: money pages exist with transparent pricing, FAQ + Dentist schema on almost every page, direct-answer copy, an `llms.txt`, 505 Google reviews, sitemap + robots correct, HTTPS/non-www canonicalised.
Gaps: no blog despite a homepage link to one (`/blog/` is 404); 27 titles over 60 chars; 38 meta descriptions over 160; 7 pages share one meta description; 116 images without alt text; 5 pages with 0 or 2 H1s; three duplicate URLs kept in the sitemap (`/sedation/`, `/emergency-dentist-in-rugby/`, `/pricing-3/`) instead of 301s; thin testimonials/gallery/contact pages; body internal links are sparse on many treatment pages; legacy Universal Analytics tag still firing; `og:locale`/`inLanguage` say en_US; typos on the homepage ("RECCOMENDED", "Warwwickshire"); no security headers.

## Progress log

- 2026-09-05 — Phase 0: video extracted, tools researched, 63-URL crawl done, playbook/tools/process/memory written. Lighthouse pending (see AUDIT.md).
