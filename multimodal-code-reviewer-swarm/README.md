# Multimodal Code Reviewer Swarm

A Google Colab-first prototype for evidence-led code review using deterministic source inspection and optional open-weight coding and vision-language models.

> **Status: early-stage prototype.** The repository includes a deterministic scanner, model catalog, model registry, starter Colab notebook, tests, and CI workflow. The optional model-inference cells are currently examples that users enable manually. Fully automated independent agents, structured LLM finding adjudication, validated patch generation, and a production-grade multimodal pipeline remain roadmap items.

## At a glance

| Area | Current capability |
|---|---|
| Inputs | ZIP archives or selected source files in the Colab notebook |
| Deterministic analysis | Python syntax checks and conservative pattern-based rules |
| Languages | Multiple text-based source/config formats can be scanned for simple patterns; Python gets AST syntax parsing |
| Model catalog | Seven linked coding, reasoning, and vision-language candidates |
| Model execution | Optional, local inference examples; one model at a time is recommended |
| Image understanding | A commented vision-language example for screenshots/diagrams; not a completed, hardware-tested pipeline |
| Output | Downloadable JSON findings |
| Safety model | Target source is read as data and is not intentionally executed |
| Automatic patches | Not implemented |

## Quick links

- [Repository overview](../README.md)
- [Colab notebook](notebooks/Colab_Code_Reviewer_Swarm.ipynb)
- [Coding and multimodal model catalog](MODEL_CATALOG.md)
- [Validated model registry](model_registry.json)
- [Scanner implementation](src/reviewer_swarm/review.py)
- [Registry implementation](src/reviewer_swarm/registry.py)
- [Unit tests](tests/)

## Architecture

Source ZIP/files → path validation and inventory → deterministic scanner → structured findings → JSON report → human verification and regression tests.

Optional model prompts can be used for code critique or vision-language interpretation. Outputs from a model must remain separate from deterministic observations until they have been checked. Reusing one model across specialist prompts is role decomposition, not independent multi-model consensus.

## Model selection

For a constrained Colab runtime, start with a small text model only if model inference is needed. Do not load every checkpoint simultaneously. First run the deterministic scan, which does not require model weights.

| Model | Suggested role | Colab guidance |
|---|---|---|
| [Qwen2.5-Coder-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) | Lower-resource text/code review | Candidate for initial experiments; check actual runtime resources and model terms |
| [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Higher-capacity text review | Requires more memory; may need a supported quantized build |
| [Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | Deep code reasoning | Large total weights; generally not a free-Colab default |
| [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) | Long-context/agentic coding | 80B-class model; treat as an advanced deployment option |
| [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | Screenshot and diagram understanding plus text | Multimodal, but full BF16 weights exceed the capacity of many Colab runtimes |
| [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | Reasoning challenge/adjudication | Check its required prompt format and compatible inference stack |
| [StarCoder2-7B](https://huggingface.co/bigcode/starcoder2-7b) | Code completion/fill-in-middle | Not an instruction-tuned general chat reviewer; BigCode OpenRAIL-M terms apply |

The model catalog is a shortlist, not a guaranteed ranking. Check the exact official model card for the revision, license, modalities, runtime compatibility, and quantization provenance before download or redistribution. Model licenses are separate from the license of this project's own source code.

## Run in Google Colab

1. Open the notebook linked above. If GitHub-to-Colab access does not work for this private repository, download the notebook file and upload it into Colab.
2. Run the hardware-detection cell. Colab resource availability varies; no specific GPU is assumed.
3. Upload a ZIP of the repository you want to inspect or select individual source files.
4. Run the deterministic scanner and review the output table.
5. Download the JSON report.
6. Enable optional text or vision-model examples only after reviewing model terms, library compatibility, memory requirements, and the sensitivity of the source being uploaded.

Do not upload credentials, private keys, environment files, customer data, or code you are not permitted to put in a hosted notebook runtime.

## Run locally

From the top-level Code-Review repository:

    python -m pip install -r multimodal-code-reviewer-swarm/requirements-colab.txt

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m pytest -q multimodal-code-reviewer-swarm/tests

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m reviewer_swarm.review --path /path/to/repository --output review-findings.json

The registry module validates required model fields, unique IDs, links, and the configured default. The scanner reads supported files as text, skips common generated directories and files above its configured size limit, and reports stable-sorted findings.

## What a finding means

A finding is a review lead, not a verdict. Current rules can detect patterns such as dynamic evaluation, subprocess shell use, possible hard-coded secrets, unresolved TODO/FIXME markers, bare Python exception handlers, and Python syntax errors.

- A pattern match can be a false positive.
- Absence of a finding does not prove the code is safe.
- Confidence values are heuristic, not calibrated probabilities.
- Sensitive matched credential values are redacted from the secret-pattern evidence.
- High-impact findings need contextual review and reproducible tests.

No precision, recall, or detection-rate claim is made until the system is measured against a versioned benchmark with known labels.

## Security boundaries

- The scanner does not import or execute target source, notebook cells, setup scripts, or model-generated code.
- The Colab ZIP handler checks resolved paths against the extraction root and rejects basic path traversal.
- Archive checks and file-size limits are safeguards, not a complete sandbox for malicious archives.
- Source code and comments can contain prompt injection. If model inference is enabled, treat file content strictly as untrusted data.
- Do not put tokens, credentials, or secrets into notebook outputs or generated reports.
- Standard Colab is not a hardened sandbox for running untrusted code. Keep target-code execution out of this workflow.
- No patch is applied, committed, pushed, or merged automatically.

## Project structure

    README.md
    MODEL_CATALOG.md
    model_registry.json
    requirements-colab.txt
    notebooks/Colab_Code_Reviewer_Swarm.ipynb
    src/reviewer_swarm/__init__.py
    src/reviewer_swarm/registry.py
    src/reviewer_swarm/review.py
    tests/test_registry.py
    tests/test_review.py

## Roadmap

- [x] Deterministic first-pass scanner.
- [x] Model catalog and JSON registry.
- [x] Colab notebook, ZIP/source-file upload, and JSON export.
- [x] Unit tests and GitHub Actions validation workflow.
- [ ] Convert model responses into a validated structured finding schema.
- [ ] Add bounded orchestration, retries, agent status, and evidence-based adjudication.
- [ ] Add language-specific AST/parser and security-tool integrations.
- [ ] Complete and test true multimodal inference on available hardware.
- [ ] Add a labeled benchmark with false-positive/false-negative analysis.
- [ ] Generate proposed diffs and verify them in an isolated test workspace.

## License and reuse

No project-level license grant is stated here for the full repository. Check repository license files before reusing or redistributing the source. Each model checkpoint, dependency, and dataset has its own license and terms.
