# Representation API requirements

Each API endpoint depends on specific representation capabilities. A representation **must** implement the properties and methods below for the endpoints that you want to support.

## Protocol (all representations)

Every representation must implement the full `Representation` protocol in `protocol.py`:

- **id**: str
- **output_type**: `"shader" | "grid" | "image" | "audio"`
- **create_random**(key) → individual
- **mutate**(ind, key) → individual
- **crossover**(a, b, key) → individual
- **express**(ind, inputs, **kwargs) → RepresentationOutput
- **compile_to_shader**(ind) → str | None
- **to_json**(ind) → dict
- **from_json**(data) → individual

---

## Endpoint → representation requirements

| Endpoint | Required representation capabilities | Notes |
|----------|---------------------------------|--------|
| **POST /api/random** | create_random, to_json, output_type | All representations. |
| **POST /api/evaluate** | from_json, express, output_type; compile_to_shader used when present for response | All representations. |
| **POST /api/evolve** (app) | create_random, mutate, crossover, from_json, to_json, output_type | All representations. |
| **POST /api/compile** | from_json, **compile_to_shader** (must be implemented and return a GLSL string for thumbnails / shader display) | 501 if compile_to_shader is missing or not callable. dual_cppn gets full stats; others get id, shader, clicks, nodes, connections. |
| **POST /api/save** | **dual_cppn only**: get_compile_stats, compile_to_shader, build_save_assets; response built in web/stateless_api | 501 for other representations. |
| **POST /api/time-output** | **dual_cppn only**: engine (time CPPN query) | 501 for other representations. |
| **GET/POST /api/network** | **dual_cppn only**: engine (extract_network_data) | 501 for other representations. |
| **POST /api/adjust-weight** | **dual_cppn only**: engine | 501 for other representations. |

---

## Summary

- **Mandatory for all representations:** full protocol (id, output_type, create_random, mutate, crossover, express, compile_to_shader, to_json, from_json).
- **Required for /api/compile (e.g. genealogy thumbnails):** `compile_to_shader(ind)` must be implemented and return a non-empty GLSL string (or the endpoint returns 501). CA and CPPN representations satisfy this.
- **Only dual_cppn:** save, time-output, network, adjust-weight. Other representations return 501 for these.

When adding a new representation, implement the protocol and ensure `compile_to_shader` returns GLSL if you want compile (and thumbnails) to work.
