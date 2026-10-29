# Multimodal Code Reviewer Swarm

A Colab-first starter for evidence-led code review using several open-weight coding/reasoning models, deterministic static checks, and optional vision-language review of screenshots or architecture diagrams.

This project currently lives under the multimodal-code-reviewer-swarm folder in the existing KumarKumar89/Code-Review repository. The folder is organized so it can later be copied into a dedicated repository.

## What it does

- Catalogues coding and multimodal model candidates with official model-card links and license notes.
- Separates deterministic checks from model-generated hypotheses.
- Runs Python syntax checks and conservative pattern-based scans without executing the target repository.
- Reuses one locally loaded model across specialist prompts to reduce VRAM pressure.
- Includes a Colab notebook for ZIP-uploaded source code and optional screenshot review.
- Exports machine-readable JSON findings and includes tests for the core registry and scanner.

This is a starter implementation, not an automated security certification or a promise to find every defect.

## Model selection

Do not load all checkpoints simultaneously.

| Role | Model | Intended use | Practical note |
|---|---|---|---|
| Lower-resource coding baseline | [Qwen2.5-Coder-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) | Text/code review prompts | Good starting point when Colab GPU memory is limited; actual fit still depends on runtime and precision |
| Stronger coding specialist | [Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | Repository-level code reasoning | Large total model despite sparse active parameters; generally not a free-Colab default |
| Repository-scale agentic coder | [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) | Long-context coding-agent tasks | 80B total parameters; server-class or carefully quantized deployment |
| Multimodal reviewer | [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | Code reasoning plus screenshot/diagram analysis | Vision-capable, but full BF16 weights are too large for many Colab runtimes |
| Reasoning/adjudication candidate | [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | Challenge findings and assess alternatives | General reasoning model, not a code-specialist or image model |
| Code-completion specialist | [StarCoder2-7B](https://huggingface.co/bigcode/starcoder2-7b) | Completion and fill-in-middle tasks | Not instruction-tuned for chat-style review; BigCode OpenRAIL-M terms apply |
| Additional coding option | [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Text-based review and fixes | Use a compatible quantized checkpoint when required |

Model availability, licenses, architecture support, and model-card claims can change. Recheck the linked official card before downloading or redistributing weights. Benchmark scores are not directly comparable unless benchmark, date, harness, and model revision match.

## Quick start in Google Colab

1. Open notebooks/Colab_Code_Reviewer_Swarm.ipynb in Colab. Because the parent repository is private, download the notebook first or open it after authenticating to GitHub.
2. Run the runtime-information cell.
3. Upload a ZIP containing the target source repository. Do not include secrets, virtual environments, build output, or confidential files that should not be shared with a hosted notebook runtime.
4. Run the deterministic scan and inspect the JSON findings.
5. Only enable local LLM inference if you accept the model download, memory, and runtime costs. The notebook does not call a paid inference API.

For a local checkout:

    python -m pip install -r requirements-colab.txt
    PYTHONPATH=src python -m pytest -q
    PYTHONPATH=src python -m reviewer_swarm.review --path /path/to/repository --output review-findings.json

## Review workflow

1. Inventory source files using allowlisted extensions and excluded directories.
2. Run syntax checks and deterministic heuristics.
3. Optionally ask one locally loaded model to review bounded source chunks using specialist prompts.
4. Treat model findings as hypotheses until source evidence or tests support them.
5. Export JSON findings for human review.

The role prompts are sequential when they share one checkpoint. This is role decomposition, not independent multi-model consensus. True model diversity requires loading different checkpoints sequentially or using separate machines.

## Safety and limitations

- Target files are read as data; this project does not import or execute the target repository.
- ZIP extraction in the notebook checks path traversal before writing files.
- Pattern-based security checks can have false positives and false negatives.
- No generated patch is applied automatically.
- Do not place GitHub tokens, cloud credentials, private keys, customer data, or other secrets in notebook output.
- Standard Colab is not a hardened sandbox for executing untrusted code. This project does not execute target code.
- Model-generated review output is not proof. Validate important findings using reproducible tests, static analysis, and human review.

## Project layout

    model_registry.json
    MODEL_CATALOG.md
    requirements-colab.txt
    src/reviewer_swarm/
      __init__.py
      registry.py
      review.py
    tests/
      test_registry.py
      test_review.py
    notebooks/
      Colab_Code_Reviewer_Swarm.ipynb

## License

The source code in this project folder is provided under the MIT License unless otherwise stated. This license does not change the separate licenses or terms governing model weights, datasets, or third-party dependencies. StarCoder2 has its own BigCode OpenRAIL-M license.
