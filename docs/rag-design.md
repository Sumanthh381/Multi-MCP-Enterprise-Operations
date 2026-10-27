# Document retrieval design

## Sources and ingestion

The committed corpus is three synthetic UTF-8 Markdown documents: pump troubleshooting, alarm philosophy, and rotating-equipment guidance. Each front matter header requires `id`, `title`, `asset_type`, and `revision`. Extraction strips the header and keeps paragraph boundaries. `python -m enterprise.rag` rebuilds `.runtime/rag-index.json`; startup also rebuilds the index. Changes become visible after rebuild/restart. No unsafe pickle or remote document execution is used.

Paragraphs are split into at most 160 words, moving 130 words at a time for a 30-word overlap on long paragraphs. Metadata captures filename, paragraph, offset-derived chunk ID, revision, asset type and SHA-256 of the source. The current sample produces eight chunks. The JSON index persists chunks; the sparse TF-IDF matrix is reconstructed in memory using unigrams/bigrams with English stop words.

## Ranking and grounding

Query text combines the user's request and observed alarm names, so the same MCP observations drive retrieval. Hybrid score is `0.85 * cosine_similarity + 0.15 * query_term_coverage`. No paid embedding model is required; TF-IDF supplies equivalent sparse vector retrieval. Asset-type filters allow the relevant type plus `all`. Up to three chunks with score >=0.09 are returned. Threshold is heuristic and documented, not a calibrated probability.

Citations look like `[SOP-PUMP-101:2:0]`: document ID, paragraph, word offset. The GUI shows title, revision, score, filename, paragraph and verbatim passage. The response also includes content hashes. Example chunks are in [retrieval-example.json](evidence/retrieval-example.json). The composer presents measured counts separately from maintenance hypotheses and retrieved guidance. It never claims correlation proves cause.

No hits or low scores produce an explicit warning and no recommended actions. Empty alarm windows are not described as recurrent. Conflicting field evidence and documents must be investigated by an operator; the system does not rank a text passage above live observations or establish causality. It does not currently perform automated contradiction detection.

## Document trust and injection

Retrieved documents are untrusted evidence. The pipeline quarantines paragraphs matching instruction-like markers (`ignore previous instructions`, secret disclosure, system-prompt or command execution phrases). Retrieval rechecks chunks to defend against a modified index. This heuristic is additional defense, not a complete detector. The primary boundary is architectural: no LLM receives executable instructions, the planner only reads the user's message, citations are rendered with `textContent`, and retrieved content cannot select tools or approve writes. Unsupported query intents and uncertain retrieval are surfaced rather than filled with invented facts.

## Validation

`tests/unit/test_rag.py` covers metadata extraction, chunk overlap, relevant ranking, asset filtering, citation construction, no results, low confidence, empty index and adversarial document content. Integration tests verify that missing RAG evidence withholds actions. End-to-end tests verify real MCP observations and cited RAG evidence occur within one request.
