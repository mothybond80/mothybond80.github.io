"""decide_engine: shared evidence-retrieval and citation-verification logic for the
Evidence-to-Decision Engine.

Design rules (see docs/ARCHITECTURE.md):
  * Deterministic. Given the same cached responses, output is byte-identical.
  * Framing-blind. Searches are built from extracted concepts, never from the
    wording of the user's question.
  * No LLM calls here. Appraisal and decision reasoning happen in isolated
    agent contexts that consume the JSON "evidence pack" this package builds.
  * Standard library only. No third-party imports, so there is nothing to audit
    at install time and nothing that phones home.
"""

__version__ = "0.1.0"
