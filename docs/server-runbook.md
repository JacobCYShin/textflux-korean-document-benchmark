# Server Runbook

This runbook assumes the existing `textflux-offline:2026-08-25` image has already been loaded and the model payload remains separate from the image.

## 1. Place the repository and private inputs

```bash
export BUNDLE=/share/jacob/textflux_offline_bundle
export BENCH_ROOT="$BUNDLE/textflux-korean-document-benchmark"
export INPUT_ROOT="$BUNDLE/private-inputs"

mkdir -p "$INPUT_ROOT/forms" "$INPUT_ROOT/masks" "$INPUT_ROOT/styles"
```

Copy the repository under `$BENCH_ROOT`. Keep approved source documents and masks under `$INPUT_ROOT`; they are ignored by Git.

## 2. Create and validate the private manifest

```bash
cp "$BENCH_ROOT/cases/manifest.example.jsonl" "$BENCH_ROOT/cases/manifest.jsonl"
vi "$BENCH_ROOT/cases/manifest.jsonl"

sudo docker run --rm --network none \
  -v /share:/share \
  --entrypoint python \
  textflux-offline:2026-08-25 \
  "$BENCH_ROOT/scripts/validate_cases.py" \
  --manifest "$BENCH_ROOT/cases/manifest.jsonl" \
  --input-root "$INPUT_ROOT"
```

Validation must finish with `VALIDATION PASSED`. Fix every error before inference.

### Optional: first run with the included generic demo

Use this only to validate the Korean document content path before approved target documents are available:

```bash
cp -a "$BENCH_ROOT/examples/demo-inputs/." "$INPUT_ROOT/"
cp "$BENCH_ROOT/examples/demo-manifest.jsonl" "$BENCH_ROOT/cases/manifest.jsonl"
```

Run the validation command above after copying these files. The demo does not evaluate real-form fidelity or handwriting style.

## 3. Run the fixed-seed baseline suite

```bash
export FONT="$BUNDLE/textflux-korean-font-patch/fonts/NotoSansCJKkr-Regular.otf"

python3 "$BENCH_ROOT/scripts/run_suite.py" \
  --manifest "$BENCH_ROOT/cases/manifest.jsonl" \
  --input-root "$INPUT_ROOT" \
  --bundle "$BUNDLE" \
  --font "$FONT" \
  --suite korean-document-baseline-v1 \
  --checkpoint-id 'yyyyyxie/textflux@<downloaded-revision>' \
  --seeds 42,43 \
  --steps 30
```

Replace `<downloaded-revision>` with the actual repository revision recorded when the checkpoint was downloaded. The script stores this identifier in every `case.json`; do not compare results from different checkpoint revisions without recording the change.

The script always uses `--network none`, mounts `/share`, preserves `outputs_my` under every run directory, saves `result.png`, writes `result.png.sha256`, and removes each stopped container.

Generated paths follow this layout:

```text
$BUNDLE/runs/korean-document-baseline-v1/<case-id>/seed-000042/
  result.png
  result.png.sha256
  run.log
  case.json
  outputs_my/rendered/rendered_0001.png
```

## 4. Review and score

Copy `reviews.template.csv` to a private review file and fill `observed_text` manually after viewing each output.

```bash
mkdir -p "$BENCH_ROOT/reviews"
cp "$BENCH_ROOT/reviews.template.csv" "$BENCH_ROOT/reviews/korean-document-baseline-v1.csv"

python3 "$BENCH_ROOT/scripts/score_reviews.py" \
  --manifest "$BENCH_ROOT/cases/manifest.jsonl" \
  --reviews "$BENCH_ROOT/reviews/korean-document-baseline-v1.csv" \
  --output "$BENCH_ROOT/reviews/korean-document-baseline-v1-summary.json"
```

`reviews/` is ignored by Git. Do not commit generated results or review data.
