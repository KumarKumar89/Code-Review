# Multimodal Code Reviewer Swarm

An evidence-first code-review toolkit for local GPU laptops and Google Colab. The architecture combines a deterministic scanner, an optional parallel Rust scanner, sequential specialist prompts against a single local open-weight model, and structured reports.

This is a reviewer prototype, not a guarantee of perfect defect detection. No model or scanner can promise the fastest runtime or highest accuracy on every repository; benchmark quality against labeled examples before making such claims.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the flow and trust boundaries.

- **Deterministic layer:** Python AST checks and conservative patterns. Does not import or execute the target project.
- **Fast path:** optional Rust scanner using parallel traversal (Rayon), ignore-aware file discovery, and compiled regexes.
- **Agent layer:** optional local Ollama model with sequential correctness, security, and reliability review roles. One model is used at a time to reduce memory pressure.
- **Evidence boundary:** deterministic findings and model hypotheses are separate in JSON; model findings remain unverified.
- **Colab:** the existing notebook runs a non-executing first pass and supports optional model paths; free GPU availability is not guaranteed.
- **Local GPU:** Ollama provides a simple local inference endpoint. No paid inference API key is required.
A Google Colab-first prototype for evidence-led code review that combines deterministic source inspection with optional open-weight coding and vision-language model experiments.

> **Status: early-stage prototype.** The current implementation includes a deterministic scanner, model registry, model catalog, Colab notebook, tests, and CI workflow. The model-inference cells are opt-in examples. A fully orchestrated multi-agent swarm, production-ready image pipeline, automatic patch generation, and benchmark-proven detection performance are not yet implemented.

## Quick links

- [Open the Colab notebook](https://colab.research.google.com/github/KumarKumar89/Code-Review/blob/main/multimodal-code-reviewer-swarm/notebooks/Colab_Code_Reviewer_Swarm.ipynb)
- [Repository landing page](../README.md)
- [Model catalog and license notes](MODEL_CATALOG.md)
- [Machine-readable model registry](model_registry.json)
- [Deterministic scanner](src/reviewer_swarm/review.py)
- [Model registry validation](src/reviewer_swarm/registry.py)
- [Unit tests](tests/)
- [GitHub Actions workflow](../.github/workflows/reviewer-swarm-ci.yml)

## What is implemented

| Component | Current behavior |
|---|---|
| File inspection | Reads supported text files and skips common generated/virtual-environment folders |
| Python correctness | Uses Python AST parsing to report syntax errors with a source line |
| Pattern checks | Flags selected dynamic-evaluation, shell, possible credential, TODO/FIXME, and bare-exception patterns |
| Model registry | Validates required fields, unique IDs, links, modalities, and the configured default |
| Colab notebook | Uploads a ZIP or selected files, runs a notebook-local scanner, displays findings, and exports JSON |
| Model inference | Commented, opt-in text and image inference examples; not automatically invoked |
| Tests | Unit tests cover the registry and deterministic scanner |
| CI | Runs tests and validates registry JSON and notebook JSON/Python-cell syntax |

The package scanner and the notebook-local scanner have overlapping but not identical rules. The notebook does not currently call the package scanner as a shared library. The notebook's model examples are not integrated into a unified finding schema or an autonomous agent orchestrator.

## Architecture

**Input ZIP/files → basic path validation → file inventory → deterministic scan → findings table → JSON export → human verification.**

Optional branches can send bounded source excerpts to a local text model or a screenshot to a compatible vision-language model. These models may propose issues and explanations, but the output must remain labelled as model-generated until independently verified.

Role prompts that share a single checkpoint are a convenient way to structure a review; they are not independent reviewers and must not be reported as independent consensus.

## Quick start — deterministic Python scanner

From this folder:

    python -m pip install -r requirements-colab.txt
    PYTHONPATH=src python -m pytest -q
    PYTHONPATH=src python -m reviewer_swarm.review --path /path/to/repository --output review-findings.json

This first pass requires no model download.

## Fast Rust scanner (optional)

Install Rust using the official rustup installer, then build the scanner:

    cargo build --release --manifest-path rust-scanner/Cargo.toml

Run it directly:

    ./rust-scanner/target/release/review-scan /path/to/repository review-findings.json

Windows builds use the corresponding .exe path. The scanner respects common ignore rules, skips generated directories and files larger than 1 MB, and emits JSON. It does not execute scanned files. The Python AST scanner remains useful for Python syntax errors that the Rust regex pass does not detect.

## Unified pipeline

Set the source path in the command. The optional Rust executable is used when provided; otherwise the pipeline falls back to the Python scanner.

    PYTHONPATH=src python -m reviewer_swarm.pipeline --path /path/to/repository --output review-report.json

To use local model agents, first install [Ollama](https://ollama.com), start its local service, and download a model:

    ollama pull qwen2.5-coder:3b

Then run:

    OLLAMA_HOST=http://127.0.0.1:11434 PYTHONPATH=src python -m reviewer_swarm.pipeline --path /path/to/repository --model --output review-report.json

For a stronger model on a suitable machine, try qwen2.5-coder:7b. The actual latency and quality depend on GPU/CPU, RAM/VRAM, quantization, context size, repository size, and model version. The small default is a resource-conscious starting point, not a universal quality winner.

Optional Rust + local model:

    REVIEW_RUST_BINARY=/absolute/path/to/review-scan PYTHONPATH=src python -m reviewer_swarm.pipeline --path /path/to/repository --model

On Windows PowerShell, set environment variables with $env:OLLAMA_HOST and $env:REVIEW_RUST_BINARY syntax.

## Google Colab

Open [Colab_Code_Reviewer_Swarm.ipynb](notebooks/Colab_Code_Reviewer_Swarm.ipynb). The notebook supports uploading source archives and running the deterministic scan without installing a model. It detects whether a GPU is available, but free Colab hardware and session duration vary.

For optional inference in Colab, use only one supported model at a time and check the model card, license, runtime memory and Transformers compatibility first. Ollama's local-laptop path and Colab's Transformers path are separate options; Ollama on Colab is not required. Do not upload secrets or source code that policy does not permit in a hosted runtime.

## Test

    PYTHONPATH=src python -m pytest -q

CI also compiles the Rust crate and validates the model registry and notebook syntax. A passing unit test does not prove model quality, GPU compatibility or full end-to-end runtime success.

## Model options and licenses

The existing [model catalog](MODEL_CATALOG.md) and [model registry](model_registry.json) describe candidates. Verify official model cards and licensing before downloading or commercial use. Open weights do not imply identical license terms.

## Accuracy and safety rules

1. Findings need a file path, line, and evidence; model output is a hypothesis, not proof.
2. Verify high-impact findings through source tracing, reproduction, independent review, or regression tests.
3. Never treat a model-generated confidence value as a calibrated probability.
4. Do not execute the repository under review, run generated patches, or automatically push changes.
5. Review reports for sensitive information before sharing them. The local model source loader caps context and redacts some likely secret patterns, but this is not a complete secret scanner.
6. Keep Ollama bound to localhost unless you have intentionally secured the endpoint.

## Performance roadmap

- Use Rust for file discovery and parallel rule scanning.
- Keep static checks cheap and always available.
- Reuse one local model sequentially across specialist roles to conserve VRAM.
- Add language-specific parsers and security analyzers where justified.
- Establish a versioned, ground-truth benchmark and measure precision, recall, false-positive rate, false negatives, latency, memory use and file coverage.
- Add optional patch suggestions only after diff validation and isolated regression tests; require human approval before applying changes.

## License

Check the repository-level license and each model/dependency's license before reuse. No claim is made that this tool detects all defects or is suitable as a sole security control.
Select the checkpoint based on the actual Colab runtime and task. Start with the deterministic scan, which does not require downloading model weights. Load one model at a time.

| Model | Suggested role | Resource guidance |
|---|---|---|
| [Qwen2.5-Coder-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) | Lower-resource text/code review | Optional initial candidate; verify compatible inference dependencies and available memory |
| [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Larger text-based review | Higher memory requirement; a compatible quantized artifact may help |
| [Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | Deep code and patch reasoning | Large total weights; not a safe default for free Colab |
| [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) | Long-context, agent-oriented coding | 80B total parameters and 256K native context per model card; advanced hardware category |
| [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | Screenshot and diagram understanding | Vision-language candidate; full-precision weights will exceed many hosted notebook GPU budgets |
| [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | Reasoning challenge and adjudication | General reasoning candidate; check the supported model format and inference library |
| [StarCoder2-7B](https://huggingface.co/bigcode/starcoder2-7b) | Code completion/fill-in-middle | Not instruction-tuned for standard chat review; BigCode OpenRAIL-M terms apply |

Treat these as options, not a definitive global ranking. Verify the exact checkpoint license, revision, modality support, processor/API, quantization provenance, and hardware needs before downloading or redistributing model files. Open-weight does not imply identical terms for all checkpoints.

Colab does not guarantee a GPU or a fixed memory capacity. See the [official Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Use the Colab notebook

1. Open the [notebook](https://colab.research.google.com/github/KumarKumar89/Code-Review/blob/main/multimodal-code-reviewer-swarm/notebooks/Colab_Code_Reviewer_Swarm.ipynb). If access does not work, download the notebook from GitHub and upload it into Colab.
2. Run the environment-detection cell.
3. Upload a source ZIP or a selection of source files.
4. Run the deterministic scan.
5. Inspect findings and download the JSON report.
6. Enable optional model cells only after checking runtime resources, package compatibility, model terms, and the sensitivity of the source you are uploading.

The notebook does not need a paid inference API for the default deterministic flow. Optional model inference downloads weights into the current runtime and may run slowly or fail if the model does not fit.

## Run locally

From the top level of the Code-Review repository, install the test dependency:

    python -m pip install -r multimodal-code-reviewer-swarm/requirements-colab.txt

Run the tests:

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m pytest -q multimodal-code-reviewer-swarm/tests

Run the deterministic scanner:

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m reviewer_swarm.review --path /path/to/repository --output review-findings.json

The CLI reads source files as data. It does not import or execute the target project. It produces a JSON array of findings with file path, line, rule, evidence, recommendation, confidence heuristic, severity, and verification status.

## Understanding results

- **Python syntax findings:** supported by the AST parser; check the reported line and full interpreter context.
- **Pattern-based findings:** possible issue indicators; inspect surrounding code and input flow to judge relevance.
- **Unverified hypotheses:** do not present these as reproduced bugs or confirmed vulnerabilities.
- **Confidence values:** rule-specific heuristics, not statistically calibrated probabilities.
- **No findings:** not proof of safety or correctness.

Avoid reporting accuracy, precision, recall, or detection rates without a versioned ground-truth test set and reproducible evaluation counts.

## Security and privacy

- **Do not execute untrusted repositories.** The current workflow reads candidate files as text and does not run target code, notebooks, setup scripts, or generated code.
- **Use trusted archives only.** The notebook checks resolved ZIP paths and applies a per-entry size limit, but does not yet impose archive-wide member-count or aggregate-size limits. These checks are not a complete defence against hostile archives.
- **Protect sensitive source.** Do not upload secrets, access tokens, private keys, customer records, or proprietary code unless organizational policy permits the hosted runtime.
- **Treat source as untrusted instructions.** Comments and documents may contain prompt-injection content. Never allow such text to expand tool permissions.
- **No automatic remediation.** This version does not apply generated fixes or push changes.
- **Hosted runtime caveat.** Standard Colab is not a hardened sandbox for arbitrary untrusted code.

## Project layout

    multimodal-code-reviewer-swarm/
    ├── README.md
    ├── MODEL_CATALOG.md
    ├── model_registry.json
    ├── requirements-colab.txt
    ├── notebooks/
    │   └── Colab_Code_Reviewer_Swarm.ipynb
    ├── src/reviewer_swarm/
    │   ├── __init__.py
    │   ├── registry.py
    │   └── review.py
    └── tests/
        ├── test_registry.py
        └── test_review.py

## Roadmap

- [x] Deterministic first-pass scanner.
- [x] Model catalog and validated registry.
- [x] Colab notebook with upload and JSON export.
- [x] Unit tests and GitHub Actions validation workflow.
- [ ] Add a shared structured finding schema for static and model-generated results.
- [ ] Implement bounded, observable agent orchestration with timeouts, retries, and explicit adjudication.
- [ ] Add language-aware parsers and trusted static-analysis integrations.
- [ ] Complete and test multimodal inference with actual screenshot/diagram inputs.
- [ ] Build a labelled benchmark with false-positive and false-negative reporting.
- [ ] Generate minimal patch diffs and validate them through regression tests in a separate working copy.

## Contributing

Prefer focused changes with tests. Add a regression test for each fixed defect, document new dependencies and trust boundaries, redact secrets from fixtures, and distinguish measured results from assumptions. Run the local test command before submitting a pull request.

## License

This folder does not claim to relicense model weights or third-party dependencies. Check the repository's license files before reusing project code; each model checkpoint remains subject to its own license and usage terms.
