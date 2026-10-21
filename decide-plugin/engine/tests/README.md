# Recorded fixtures

`fixtures/cache/` holds real API responses recorded on 21 Oct 2026 through a
web proxy (the cloud sandbox blocked direct access). Files are keyed by the
SHA-256 of the request URL, exactly as `decide_engine.fetch.Fetcher` stores
them. Running `decide-engine --offline --cache-dir tests/fixtures/cache ...`
reproduces the packs byte-for-byte.

Three PubMed `esearch` responses per subject were re-serialised from the live
reply with the `idlist`, `count` and `retmax` fields verbatim and the long
`querytranslation` abbreviated; `efetch` XML and OpenAlex search responses are
stored verbatim; four OpenAlex single-work records were condensed (author list
and inverted abstract removed, `referenced_works` verbatim) to keep the
repository small.

The two small "linked commentary" `efetch` batches (6 comment/letter records)
were reconstructed from the live XML with the fields the parser reads: PMID,
title, abstract where present, authors, journal, year, publication types,
CommentsCorrections links and article ids. Keyword lists, MeSH, grants and
reference lists were dropped.
