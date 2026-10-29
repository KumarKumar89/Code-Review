# Code Review — Multimodal Reviewer Swarm

**Evidence-first code review with open-weight model candidates, deterministic checks, and a Google Colab workflow.**

This repository contains a Colab-first prototype for reviewing source repositories, spotting potentially risky patterns, and producing structured findings. Its design combines deterministic checks with optional model-assisted analysis while keeping model-generated claims separate from verified evidence.

> **Project status: prototype.** The deterministic scanner, model registry, starter notebook, and tests are included. Optional language-model and vision-model cells are examples that users enable manually; this is not yet a fully automated production-grade multi-model swarm, patching engine, or security certification.

## Start here

| Goal | Resource |
|---|---|
| Run the notebook | [Colab code-review notebook](https://colab.research.google.com/github/KumarKumar89/Code-Review/blob/main/multimodal-code-reviewer-swarm/notebooks/Colab_Code_Reviewer_Swarm.ipynb) |
| Read project setup and limitations | [Project README](multimodal-code-reviewer-swarm/README.md) |
| Compare coding and multimodal models | [Model catalog](multimodal-code-reviewer-swarm/MODEL_CATALOG.md) |
| Inspect the machine-readable model registry | [model_registry.json](multimodal-code-reviewer-swarm/model_registry.json) |
| Review implementation | [Source package](multimodal-code-reviewer-swarm/src/reviewer_swarm/) |
| Run tests | [Test suite](multimodal-code-reviewer-swarm/tests/) |
| Review project history | [Pull request #1](https://github.com/KumarKumar89/Code-Review/pull/1) |

**Private repository note:** Google Colab may require you to authenticate to GitHub or download the notebook file and upload it into Colab. Optional inference examples download model weights into the runtime when enabled.

## What it does today

- **Safe first-pass inspection:** reads candidate files as text rather than importing or running the target project.
- **Python syntax checks:** uses Python's AST parser to report syntax errors with source locations.
- **Pattern-based checks:** flags possible dynamic eval/exec, shell=True, hard-coded credential assignments, TODO/FIXME markers, and bare exception handlers.
- **Model catalog:** documents seven coding, reasoning, and multimodal model candidates with official model-card links.
- **Colab notebook:** supports ZIP or individual-file upload, conservative scanning, and JSON report download.
- **Tests and CI:** includes unit tests and a GitHub Actions workflow for the registry, scanner, and notebook structure.
- **Optional model roles:** provides commented examples for coding review and screenshot/diagram interpretation.

Pattern matches are **leads to investigate**, not proof that a vulnerability exists. The current scanner is intentionally small; it does not replace language-specific security analyzers or human review.

## Architecture and data flow

The intended review flow is:

**Repository ZIP or selected files → input/path validation → file inventory and exclusions → deterministic scanner → structured findings → JSON report → human verification and regression tests.**

Optional model-assisted branches can review bounded code excerpts, while an optional vision-language model can interpret screenshots and diagrams. Both produce hypotheses that must be checked against the source or other evidence. These optional branches are examples, not a fully orchestrated agent swarm yet.

### Trust boundaries

1. Repository contents are untrusted input. Text inside a source file must never be treated as trusted instructions to an agent.
2. The scanner does not execute source files or repository setup scripts.
3. Model-produced findings are hypotheses. Verify high-impact issues with reproducible tests or independent analysis.
4. Uploading private source to a hosted Colab runtime may expose it to that hosted environment. Review organizational policies before uploading proprietary code or personal data.

## Model shortlist

Choose one checkpoint at a time; do **not** load every model into the same Colab runtime.

| Model | Best-fit role | Resource guidance |
|---|---|---|
| [Qwen2.5-Coder-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) | Lower-resource text/code review starting point | Smallest listed coding candidate; GPU, precision, library compatibility, and latency still need runtime checks |
| [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | More capable text-based coding review | Medium; quantization may help but affects memory and can affect output quality |
| [Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | Deeper repository and patch reasoning | Large total weights; low activated-parameter count does not mean the full weights need no memory |
| [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) | Long-context and agentic coding workflows | 80B-class model; not a default for free Colab |
| [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | Multimodal review of screenshots, diagrams, and text | Vision-language model; full BF16 weights are too large for many Colab runtimes |
| [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | Reasoning challenge and finding adjudication | General reasoning candidate; use its supported prompt/format and compatible inference stack |
| [StarCoder2-7B](https://huggingface.co/bigcode/starcoder2-7b) | Code completion and fill-in-middle tasks | Not an instruction-tuned general chat reviewer; separate BigCode OpenRAIL-M license applies |

Check each official model card for its current license, supported modalities, revision, required Transformers version, and quantization compatibility before use. Open-weight does not automatically mean every model has the same license or usage conditions. These model names are options, not a guarantee of a particular quality ranking.

## Run in Google Colab

1. Open the [notebook](https://colab.research.google.com/github/KumarKumar89/Code-Review/blob/main/multimodal-code-reviewer-swarm/notebooks/Colab_Code_Reviewer_Swarm.ipynb). If the private-repository link does not open, download the notebook from GitHub and upload it into Colab.
2. Run the runtime-detection cell and check whether the current runtime has a GPU.
3. Upload a source ZIP or selected source files. Do not include credentials, private keys, environment files, build output, or data you are not permitted to place in hosted Colab.
4. Run the deterministic scan and inspect the findings.
5. Download the JSON report. Enable optional model cells only after checking memory requirements, model terms, and library compatibility.

The deterministic scan does not require model weights. Local inference is optional and may be slow or impossible on a constrained CPU/GPU runtime. A model-loading failure is not evidence of a target-code defect.

## Run locally

From the repository root:

    python -m pip install -r multimodal-code-reviewer-swarm/requirements-colab.txt

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m pytest -q multimodal-code-reviewer-swarm/tests

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m reviewer_swarm.review --path /path/to/repository --output review-findings.json

The scanner accepts a directory path. It reads supported files as text, skips common generated/virtual-environment directories, and omits files above its configured size limit.

## Output and interpretation

The scanner's JSON findings include a rule identifier, category, severity, confidence estimate, file path, line number, evidence excerpt (with detected credential values redacted), recommendation, and verification state.

- **Static support:** directly produced by deterministic syntax analysis or a matching rule.
- **Unverified:** a pattern or hypothesis requiring context and independent verification.
- **Not a finding:** a match can be harmless in context; close it only after recording why it is a false positive.

Do not interpret the heuristic confidence values as calibrated probabilities. Do not claim precision, recall, or detection rate until a versioned benchmark with ground-truth labels has been run and the counts have been reported.

## Security and privacy

- **No target-code execution:** the current scanner reads files; it does not run project code, notebooks, setup scripts, or generated patches.
- **Archive validation:** the notebook checks resolved ZIP member paths to block basic path traversal and applies a per-member uncompressed-size limit. Treat archives from unknown sources cautiously; this is not a complete archive sandbox.
- **Resource limits:** large files and common generated directories are skipped. Review scope and exclusions can affect coverage.
- **Secret handling:** possible hard-coded credential assignments are reported with their values redacted. Avoid displaying raw source, environment variables, access tokens, or secrets in notebook output.
- **Model safety:** source code and comments may contain prompt-injection instructions. Pass source as untrusted data and restrict tools to an explicit allowlist.
- **No automatic remediation:** this version does not silently rewrite source or push commits.

Standard Google Colab is a hosted notebook environment, not a hardened sandbox for arbitrary untrusted code. Keep execution of scanned repositories out of this workflow.

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

The GitHub Actions workflow lives at .github/workflows/reviewer-swarm-ci.yml.

## Roadmap

- [x] Deterministic first-pass repository scanner.
- [x] Model catalog and machine-readable model registry.
- [x] Colab notebook with upload and JSON export.
- [x] Unit tests and CI validation workflow.
- [ ] Wire structured model outputs into the same finding schema.
- [ ] Add language-aware parsing and more precise, low-noise checks.
- [ ] Implement independently scheduled agents with bounded retries and auditable adjudication.
- [ ] Add a versioned, ground-truth benchmark with precision/recall and false-positive analysis.
- [ ] Add safe patch-diff generation and isolated regression-test verification.
- [ ] Complete a supported vision-model integration and test it on actual image inputs.

## Contributing

Small, test-backed improvements are preferred. Add a regression test for each bug fix, document any new tool's trust boundary, pin compatible dependencies, and distinguish reproduced issues from model-generated hypotheses.

## License

No project-level license grant is stated here for the whole repository. Check the repository's license files before reuse. Every model checkpoint and third-party dependency remains subject to its own license and usage terms.
