# Substrate API requirements

Each API endpoint depends on specific substrate capabilities. A substrate **must** implement the properties and methods below for the endpoints that you want to support.

## Protocol (all substrates)

Every substrate must implement the full `Substrate` protocol in `protocol.py`:

- **id**: str
- **output_type**: `"shader" | "grid" | "image" | "audio"`
- **create_random**(key) → individual
- **mutate**(ind, key) → individual
- **crossover**(a, b, key) → individual
- **evaluate**(ind, inputs, **kwargs) → SubstrateOutput
- **compile_to_shader**(ind) → str | None
- **to_json**(ind) → dict
- **from_json**(data) → individual

---

## Endpoint → substrate requirements

| Endpoint | Required substrate capabilities | Notes |
|----------|---------------------------------|--------|
| **POST /api/random** | create_random, to_json, output_type | All substrates. |
| **POST /api/evaluate** | from_json, evaluate, output_type; compile_to_shader used when present for response | All substrates. |
| **POST /api/evolve** (app) | create_random, mutate, crossover, from_json, to_json, output_type | All substrates. |
| **POST /api/compile** | from_json, **compile_to_shader** (must be implemented and return a GLSL string for thumbnails / shader display) | 501 if compile_to_shader is missing or not callable. dual_cppn gets full stats; others get id, shader, clicks, nodes, connections. |
| **POST /api/save** | **dual_cppn only**: get_compile_stats, compile_to_shader, build_save_assets; response built in web/stateless_api | 501 for other substrates. |
| **POST /api/time-output** | **dual_cppn only**: engine (time CPPN query) | 501 for other substrates. |
| **GET/POST /api/network** | **dual_cppn only**: engine (extract_network_data) | 501 for other substrates. |
| **POST /api/adjust-weight** | **dual_cppn only**: engine | 501 for other substrates. |

---

## Summary

- **Mandatory for all substrates:** full protocol (id, output_type, create_random, mutate, crossover, evaluate, compile_to_shader, to_json, from_json).
- **Required for /api/compile (e.g. genealogy thumbnails):** `compile_to_shader(ind)` must be implemented and return a non-empty GLSL string (or the endpoint returns 501). CA and CPPN substrates satisfy this.
- **Only dual_cppn:** save, time-output, network, adjust-weight. Other substrates return 501 for these.

When adding a new substrate, implement the protocol and ensure `compile_to_shader` returns GLSL if you want compile (and thumbnails) to work.
