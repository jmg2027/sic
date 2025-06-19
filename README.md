# SIC — Semantic Instruction Catalogue

**Goal**: One source of truth for architecturally complete,
latency‑free RISC‑V instruction semantics.

* `sic-core` – instruction data + DSL
* `sic-gen`  – exporters (YAML) and code‑gens
* `docs/`    – rendered YAML and design notes

## Quick start

```bash
# format and compile
sbt fmt check

# export catalogue to YAML
sbt "sicGen/runMain sicgen.YamlExport"
# output written to generated/sic.yaml
```
