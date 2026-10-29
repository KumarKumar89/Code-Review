# Agentic Code Review Architecture

## Goals

- Fast deterministic first pass; optional local model reasoning.
- Run on a developer laptop or a Google Colab runtime without paid inference APIs.
- Keep target repository code as untrusted data: never import or execute it during review.
- Distinguish deterministic evidence from model-generated hypotheses.
- Prefer one loaded model with sequential specialist roles over loading a fleet of models into constrained VRAM.

## Data flow

    Repository folder or uploaded archive
        -> input/path validation
        -> file inventory and exclusions
        -> Rust parallel scanner (if built) OR Python deterministic scanner
        -> normalized static findings
        -> optional local Ollama model in sequential specialist roles
        -> deduplication and hypothesis labeling
        -> JSON report
        -> human verification, tests, optional future safe patch workflow

## Layers

1. Input boundary: source files are read as text. Archive extraction and path traversal defenses belong in the ingestion layer.
2. Deterministic analysis: Python AST parsing and bounded regex rules are predictable and cheap. The optional Rust scanner uses ignore, rayon, and compiled regexes for parallel file traversal. Pattern hits are leads, not proof.
3. Model reasoning: an Ollama-compatible local endpoint runs one model sequentially with specialist prompts for correctness, security, and reliability. Source snippets are explicitly framed as untrusted input. Responses are bounded by file-count, file-size, and prompt-size limits.
4. Adjudication boundary: duplicate findings are collapsed, but model findings remain model_hypothesis and verified=false. A model must never mark its own finding as verified.
5. Reporting: JSON keeps static findings separate from model hypotheses. UI views can render them without losing provenance.
6. Verification: future patching must create a diff, run tests only in a dedicated isolated environment, inspect the diff, and require explicit approval before applying changes.

## Local model options

- Default Ollama tag: qwen2.5-coder:3b (small local starting point; actual performance depends on quantization and hardware).
- Try qwen2.5-coder:7b on a machine with more memory.
- Other Ollama-compatible coding models can be selected using --model-name or REVIEW_MODEL.
- Colab GPU inference through Transformers is an alternative notebook path; Ollama on Colab is optional and can require extra setup. Free Colab GPU availability is not guaranteed.
- Model license, supported context length, memory requirements, and quality should be checked on each model card. No model is claimed to be universally fastest or most accurate.

## Speed strategy

- Parallel Rust traversal and regex checks; avoid model calls for every file by default.
- One local model loaded at a time; specialist roles run sequentially to reduce VRAM usage.
- Limit candidate files and per-file characters; skip generated directories and large files.
- Keep deterministic scanner and model inference independently switchable.
- Use low-temperature inference and structured JSON; failures are recorded rather than silently converted into findings.

## Accuracy strategy

- Deterministic evidence first; model results are hypotheses.
- Findings should include a path, line, evidence excerpt, impact, and recommendation.
- Suppress speculative style-only feedback.
- Use regression tests, independent review, and a versioned labeled benchmark to measure precision, recall, false positives, and missed defects.
- Do not report accuracy percentages until ground-truth benchmark results exist.

## Safety and privacy

- Do not run code from the repository under review.
- Do not pass secrets, .env files, credentials, binary artifacts, or huge files to the model.
- The source loader excludes common generated folders and caps files/characters, but this is not a full secret scanner or sandbox.
- Local Ollama requests stay on the configured endpoint; hosted Colab is a remote environment and may process uploaded source. Follow source-owner privacy requirements.
- Do not expose an Ollama port to the public internet without authentication and network controls.
