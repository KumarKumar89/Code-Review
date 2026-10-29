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
