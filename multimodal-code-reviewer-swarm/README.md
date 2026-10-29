# Multimodal Code Reviewer Swarm

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

## Model selection

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
