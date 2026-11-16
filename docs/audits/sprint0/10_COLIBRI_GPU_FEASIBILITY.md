# Colibri and GPU Feasibility

## Project Identification

The name “Colibri” is ambiguous. For this audit it refers to [`JustVugg/colibri`](https://github.com/JustVugg/colibri), a C-based inference engine focused on large mixture-of-experts models using storage/RAM/GPU tiers. No repository or model was cloned or downloaded.

## Audited Host

- Apple-silicon laptop class (M1 generation)
- 8 GB unified memory
- 8 CPU cores
- Local model inventory not verified

## Feasibility Finding

Colibri’s published minimum is 8 GB RAM, with 16 GB or more preferred, and at least 22 GB disk for its smallest supported setup. The audited machine is therefore at the minimum memory boundary. Colibri may start with a supported small/streamed model, but it is not an appropriate default Pardha runtime without direct measurement. Large MoE inference will be strongly constrained by unified memory, SSD bandwidth, thermal limits, prompt length, and concurrent application load.

The project exposes OpenAI-compatible endpoints, so integration could be a provider adapter rather than an architectural rewrite. Its macOS path supports local setup, but its primary differentiation is very-large MoE expert streaming, which does not match Pardha’s immediate need for low-latency structured routing on an 8 GB laptop.

## Runtime Comparison

| Runtime | Apple M1 fit | Pardha integration | Best use | Audit recommendation |
|---|---|---|---|---|
| Ollama | Good operational simplicity | Existing native adapter | Small quantized local models | Keep as current optional local default |
| llama.cpp | Strong; Metal enabled by default | Add OpenAI-compatible/server adapter | Fine-grained GGUF control | Strong alternative for benchmarking |
| MLX-LM | Strong Apple-silicon specialization | New adapter/server process | Apple-specific local inference/fine-tuning | Benchmark for best M1 efficiency |
| Colibri | Possible at minimum RAM; workload mismatch risk | OpenAI-compatible adapter | Very large MoE expert streaming | Experimental only, not default |
| vLLM | Poor fit for this Mac; Linux/GPU-server oriented | Cloud/server adapter | High-throughput production serving | Use on dedicated Linux GPU infrastructure |

Sources: [Colibri repository](https://github.com/JustVugg/colibri), [Colibri docs](https://github.com/JustVugg/colibri/blob/main/docs/index.mdx), [llama.cpp Metal build](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), [MLX-LM](https://github.com/ml-explore/mlx-lm), [vLLM documentation](https://docs.vllm.ai/).

## Safe Evaluation Plan

1. Do not install on the founder laptop until disk headroom and backup are verified.
2. Freeze one small structured-output benchmark corpus from the 10 Sprint 0 scenarios.
3. Compare Ollama, llama.cpp, and MLX-LM first using the same model/quantization where possible.
4. Measure cold start, first-token latency, tokens/second, peak memory, SSD read rate, energy/thermal throttling, JSON validity, and task accuracy.
5. Evaluate Colibri only if a supported MoE model offers a demonstrated quality advantage.
6. Keep every local provider behind the same timeout, cancellation, health, and fallback interface.

## Recommendation

**No-go as Pardha’s default on the current 8 GB M1.** **Go as a time-boxed experimental provider adapter on better hardware or with a specifically justified supported model.** MLX-LM and llama.cpp are higher-priority local benchmarks; Ollama remains the lowest-friction operational choice.

