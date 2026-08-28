# Generic Demo Inputs

`demo-inputs/` contains a generic Korean form and four matching binary masks. They are safe to copy into a closed-network environment and are included only to validate the content path:

- Hangul glyph condition;
- target-field mask alignment;
- date and amount punctuation; and
- result retention and review flow.

They do **not** validate a real foreign-exchange workflow or handwriting-style transfer. Replace them with approved target documents after the smoke test.

## Use on the server

```bash
cp -a "$BENCH_ROOT/examples/demo-inputs/." "$INPUT_ROOT/"
cp "$BENCH_ROOT/examples/demo-manifest.jsonl" "$BENCH_ROOT/cases/manifest.jsonl"
```

Then follow the validation and suite commands in `docs/server-runbook.md`.
