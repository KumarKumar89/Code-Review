# Code Review — Multimodal Reviewer Swarm

[![CI](https://github.com/KumarKumar89/Code-Review/actions/workflows/reviewer-swarm-ci.yml/badge.svg)](https://github.com/KumarKumar89/Code-Review/actions/workflows/reviewer-swarm-ci.yml)
[![Open Colab notebook](https://img.shields.io/badge/Google%20Colab-Open%20Notebook-F9AB00?logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/KumarKumar89/Code-Review/blob/main/multimodal-code-reviewer-swarm/notebooks/Colab_Code_Reviewer_Swarm.ipynb)

**Evidence-first code review with deterministic analysis, open-weight model options, and a Colab-first workflow.**

This repository hosts an early-stage code-review prototype that combines reproducible source checks with optional local-model assistance. The goal is to make review findings traceable to source evidence and verification steps, not to produce confident-sounding but unverified AI output.

> **Honest status:** the repository includes a deterministic scanner, model catalog, JSON model registry, Colab starter notebook, unit tests, and a GitHub Actions workflow. The notebook's LLM and vision examples are opt-in examples; a fully orchestrated multi-agent swarm, production-ready multimodal inference, automated patch application, and benchmark-proven detection performance are not yet implemented.

## Start here

| I want to… | Go to |
|---|---|
| Run the starter notebook | [Open in Google Colab](https://colab.research.google.com/github/KumarKumar89/Code-Review/blob/main/multimodal-code-reviewer-swarm/notebooks/Colab_Code_Reviewer_Swarm.ipynb) |
| Understand setup and current limitations | [Project README](multimodal-code-reviewer-swarm/README.md) |
| Compare the coding and vision-language candidates | [Model catalog](multimodal-code-reviewer-swarm/MODEL_CATALOG.md) |
| Inspect model metadata | [Model registry](multimodal-code-reviewer-swarm/model_registry.json) |
| Read the scanner source | [review.py](multimodal-code-reviewer-swarm/src/reviewer_swarm/review.py) |
| Read the registry validator | [registry.py](multimodal-code-reviewer-swarm/src/reviewer_swarm/registry.py) |
| Inspect the automated tests | [Tests](multimodal-code-reviewer-swarm/tests/) |
| Inspect CI configuration | [GitHub Actions workflow](.github/workflows/reviewer-swarm-ci.yml) |

## What is implemented

- **Deterministic first-pass review:** reads supported files as text, reports Python syntax errors, and flags selected suspicious patterns.
- **Evidence-oriented output:** findings include a rule identifier, source path, line, severity, evidence excerpt, and recommendation. Suspected credential values are redacted from the scanner's secret-pattern evidence.
- **Model catalog:** tracks seven candidate coding, reasoning, and multimodal checkpoints with official model-card links and resource guidance.
- **Colab notebook:** uploads a ZIP or selected files, runs a lightweight scan, displays findings, and exports JSON.
- **Tests and CI:** includes tests for the scanner and model registry, plus checks for the registry JSON and notebook structure.

The current scanner is a useful baseline, not a complete static analyzer. It will miss bugs that require deeper program analysis and can flag harmless code that resembles a risky pattern.

## Architecture

**Source archive or selected files → path checks and file inventory → deterministic scan → structured findings → JSON report → human review and regression tests.**

Optional model-assisted branches can critique bounded source excerpts. An optional vision-language model can be used to explore screenshot or diagram review when the model and runtime support it. Model outputs are hypotheses until independently verified.

Using several prompts with one checkpoint is role-based prompting, **not independent multi-model consensus**. True model diversity needs distinct checkpoints, separate inference sessions, and explicit handling of disagreements.

## Model strategy

Pick a model for the actual task and available hardware; do not load all checkpoints into the same runtime.

| Model candidate | Intended role | Resource guidance |
|---|---|---|
| [Qwen2.5-Coder-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) | Lower-resource text/code review experiments | Sensible starting candidate for optional local inference; actual fit depends on runtime, precision, and libraries |
| [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Higher-capacity text review | Needs more memory; supported quantization may help |
| [Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | Deeper code reasoning | Large total weights despite sparse active parameters; not a default for free Colab |
| [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) | Long-context and agentic coding tasks | 80B total parameters and 256K native context per model card; advanced deployment option |
| [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | Screenshot, diagram, and text interpretation | Vision-language candidate; full-precision weights exceed many hosted notebook GPU budgets |
| [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | Reasoning challenge and adjudication | General reasoning model; check supported runtime and output format |
| [StarCoder2-7B](https://huggingface.co/bigcode/starcoder2-7b) | Completion and fill-in-middle tasks | Not instruction-tuned for ordinary chat-style review; BigCode OpenRAIL-M terms apply |

These are candidates, not a universal performance ranking. Verify the exact checkpoint revision, license, supported modalities, inference API, and quantization provenance before use. Model weights, datasets, and dependencies have separate terms.

Colab resources are not guaranteed: GPU access, available memory, and runtime duration vary. The deterministic scan does not need model weights, so run that first. See the [official Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Run in Google Colab

1. Open the [notebook](https://colab.research.google.com/github/KumarKumar89/Code-Review/blob/main/multimodal-code-reviewer-swarm/notebooks/Colab_Code_Reviewer_Swarm.ipynb).
2. Run the hardware-detection cell and inspect the actual runtime.
3. Upload a repository ZIP or selected source files.
4. Run the deterministic scan and review the table.
5. Download the JSON report. Enable optional model cells only after reviewing model terms, runtime compatibility, and memory requirements.

If the Colab link cannot access the repository, download the notebook from GitHub and upload it to Colab. Do not upload code, customer information, credentials, or other data unless you are authorized to place it in a hosted notebook environment.

## Run locally

From the repository root, install the small test dependency set:

    python -m pip install -r multimodal-code-reviewer-swarm/requirements-colab.txt

Run the test suite:

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m pytest -q multimodal-code-reviewer-swarm/tests

Run the deterministic scanner against a directory:

    PYTHONPATH=multimodal-code-reviewer-swarm/src python -m reviewer_swarm.review --path /path/to/repository --output review-findings.json

The scanner reads supported files as text, skips common generated directories and files above its configured size limit, and sorts results deterministically.

## Interpreting findings

- **A pattern match is not proof.** Review surrounding code and data flow before calling a finding a defect.
- **No result does not mean safe.** The rule set is intentionally small and may miss complex or language-specific vulnerabilities.
- **Confidence values are heuristics.** They are not calibrated probabilities and should not be treated as benchmark scores.
- **Verification status matters.** Separate syntax findings, pattern matches, reproduced failures, and unresolved hypotheses.
- **Patches require tests.** This version does not apply generated repairs automatically.

Do not report precision, recall, or a detection rate unless a versioned benchmark with known labels has actually been run and the counts can be reproduced.

## Security and privacy boundaries

- Target source is treated as data; the current scanner does not import or execute it.
- The notebook performs basic ZIP path checks and enforces a per-entry uncompressed-size limit. These safeguards do not make arbitrary archives fully safe; archive-wide resource limits and hostile-file analysis remain future hardening work.
- Avoid sharing secrets, API tokens, private keys, environment files, or proprietary data with a hosted runtime or model.
- Treat source comments and other repository content as untrusted input if model inference is enabled; never turn source text into trusted tool instructions.
- Standard Colab is not a hardened sandbox for running unknown repository code. Keep target-code execution out of this workflow.
- No patches are silently applied, committed, pushed, or merged.

## Roadmap

- [x] Deterministic scanner and model-registry validation.
- [x] Colab starter notebook and JSON export.
- [x] Unit tests and CI validation workflow.
- [ ] Use a single structured finding schema for deterministic and model-generated results.
- [ ] Implement real bounded agent orchestration, retries, timeout handling, and auditable adjudication.
- [ ] Add language-specific parsers and low-noise security-tool integrations.
- [ ] Complete and test the image/screenshot inference path on supported hardware.
- [ ] Add a labeled, versioned benchmark with false-positive and false-negative analysis.
- [ ] Generate proposed patch diffs and verify them with regression tests in an isolated workspace.

## Contributing

Prefer small, test-backed changes. Include a regression test for bug fixes, document the trust boundary of new tools, avoid exposing secrets in fixtures, and label unverified AI hypotheses honestly. Run the project tests before opening a pull request.

## License

No repository-wide license grant is stated in this README. Check the repository's license files before reusing or redistributing project source. Every model checkpoint, dataset, and third-party dependency remains governed by its own license and usage terms.
