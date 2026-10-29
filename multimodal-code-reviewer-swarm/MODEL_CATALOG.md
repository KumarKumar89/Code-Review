# Coding and Multimodal Model Catalog

Catalog checked on 29 October 2026. Use this as a maintained shortlist, not a permanent ranking.

## 1. Qwen3.8-27B — combined code and visual-review candidate

- Model card: https://huggingface.co/Qwen/Qwen3.8-27B
- License shown on model card: Apache-2.0
- Modality: text and image input.
- Best role: code reasoning, interpreting UI screenshots, stack-trace images, and architecture diagrams.
- Resource class: large. The published repository is around 55.6 GB for the full BF16 artifact; many Colab runtimes cannot load it at full precision.
- Deployment advice: use a compatible quantized artifact only after checking provenance, license, quality, and runtime requirements.

## 2. Qwen3-Coder-30B-A3B-Instruct — code specialist

- Model card: https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- Intended role: repository-scale coding, code explanations, bug hypotheses, and repair suggestions.
- Model card reports 30.5B total parameters and 3.3B activated parameters.
- Resource class: large. Sparse activation reduces compute per token but does not remove the full model-weight memory requirement.

## 3. Qwen3-Coder-Next — agentic and long-context coding

- Model card: https://huggingface.co/Qwen/Qwen3-Coder-Next
- License shown on model card: Apache-2.0.
- Intended role: multi-step coding tasks, tool-oriented workflows, error recovery, and large-context repository analysis.
- Model card reports 80B total parameters, 3B activated parameters, and 256K native context.
- Resource class: server/advanced quantized deployment, not the default for free Colab.

## 4. Qwen2.5-Coder-3B-Instruct — lower-resource baseline

- Model card: https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct
- License family: Apache-2.0; verify the specific checkpoint card before deployment.
- Intended role: lower-resource coding critique, bug hypotheses, and initial repair suggestions.
- Resource class: small-to-medium depending on precision and runtime. A GPU is not guaranteed by Colab, and CPU inference may be slow.

## 5. Qwen2.5-Coder-7B-Instruct — higher-capacity text coding reviewer

- Model card: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
- License shown on model card: Apache-2.0.
- Intended role: code review, code repair, and cross-function reasoning within a bounded context.
- Resource class: medium; quantization can reduce memory needs but may alter quality.

## 6. gpt-oss-20b — reasoning challenger/adjudicator candidate

- Model card: https://huggingface.co/openai/gpt-oss-20b
- License shown on model card: Apache-2.0.
- Intended role: challenge initial findings, look for counterexamples, compare repair alternatives, and draft verification plans.
- Use as a text reasoning model in this project; do not rely on it for image analysis.
- Compatibility: its architecture and output format may require a recent compatible Transformers release. Verify before use.

## 7. StarCoder2-7B — code-completion specialist

- Model card: https://huggingface.co/bigcode/starcoder2-7b
- License: BigCode OpenRAIL-M v1, not Apache-2.0.
- Intended role: completion-oriented tasks and selected code-generation checks.
- Important limitation: the official card says it is not an instruction model. Do not make it the primary chat-style reviewer without an appropriate wrapper or fine-tuning.

## Suggested role assignment

| Review role | First choice | Alternative |
|---|---|---|
| Lower-resource source review | Qwen2.5-Coder-3B-Instruct | Qwen2.5-Coder-7B-Instruct |
| Deep code analysis | Qwen3-Coder-30B-A3B-Instruct | Qwen3-Coder-Next |
| Screenshot / diagram review | Qwen3.8-27B | Another documented vision-language model compatible with the runtime |
| Adversarial challenge | gpt-oss-20b | A Qwen Coder model with a different prompt |
| Static security verification | Deterministic scanners | Language-specific analyzers |
| Code completion | StarCoder2-7B | Qwen Coder models |

## Colab hardware policy

At runtime, inspect GPU type, free VRAM, RAM, disk, and installed library versions. Select one checkpoint only. Do not infer available memory from the account tier. Use quantization only when the exact artifact and loading path are documented. Fall back to the deterministic scanner if inference cannot safely start.

## License note

Model weights, inference libraries, datasets, and this repository's own source code have separate terms. Review the exact model card and license file for the exact revision you use. This catalog is not legal advice, and open-weight should not automatically be read as fully open-source.
