# Korean Document TextFlux Baseline Kit

This repository provides a reproducible baseline protocol for evaluating TextFlux on Korean document fields. It is designed for controlled measurement before any domain adaptation or style-conditioning work.

It is an independent evaluation harness and is not an official release of the TextFlux project.

It does not include model weights, Docker images, document scans, masks, handwriting samples, generated outputs, or personal information.

## What this kit measures

The kit keeps two questions separate:

| Track | Question | What is measured |
| --- | --- | --- |
| `content` | Can the current checkpoint place the requested Korean, numeric, and mixed text into a document field? | Exact field match, character error rate, mask leakage, visual review |
| `style` | Can a target handwriting style be reproduced? | Style review, content accuracy, mask leakage |

The current TextFlux runner consumes a scene image, a mask, and text. It does **not** consume the optional `style_reference` field. That field is recorded to prepare a future style-conditioned model; it must not be interpreted as an active conditioning input.

## Repository layout

```text
cases/
  manifest.example.jsonl  Example case manifest; safe to commit
config/
  benchmark.env.example   Closed-network path configuration example
docs/
  input-spec.md           Input, mask, and data-handling requirements
  protocol.md             Test protocol and decision gates
  server-runbook.md       Server execution steps
scripts/
  validate_cases.py       Validate images, masks, and manifest entries
  run_suite.py            Run a case-and-seed suite with the existing Docker image
  score_reviews.py        Aggregate human transcriptions and review scores
```

Private inputs remain outside Git, for example under `/share/jacob/textflux_offline_bundle/private-inputs/`.

## Quick start on the server

```bash
export BUNDLE=/share/jacob/textflux_offline_bundle
export BENCH_ROOT="$BUNDLE/textflux-korean-document-benchmark"
export INPUT_ROOT="$BUNDLE/private-inputs"

cp "$BENCH_ROOT/cases/manifest.example.jsonl" "$BENCH_ROOT/cases/manifest.jsonl"
# Edit manifest.jsonl to reference actual, approved document inputs under $INPUT_ROOT.

sudo docker run --rm --network none \
  -v /share:/share \
  --entrypoint python \
  textflux-offline:2026-08-25 \
  "$BENCH_ROOT/scripts/validate_cases.py" \
  --manifest "$BENCH_ROOT/cases/manifest.jsonl" \
  --input-root "$INPUT_ROOT"
```

After validation passes, run the suite using the existing image and model payload. See [docs/server-runbook.md](docs/server-runbook.md).

## Scope and decision rule

This is an evaluation harness, not a claim that TextFlux can already synthesize Korean handwriting at a required quality level. Do not begin adaptation training until the content track has been run on target-like documents and reviewed.

For field values such as amounts, dates, account identifiers, SWIFT codes, and currency codes, only an exact string match is acceptable. A visually plausible image with an incorrect value is a failure.
