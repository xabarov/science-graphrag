# ingest-corpus runbook

`science-graphrag ingest-corpus` now supports per-file timeout and resume checkpointing.

## Recommended command

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --per-file-timeout-s 900 \
  --progress-file eval/results/ingest-progress-wave5.jsonl
```

## Flags

- `--per-file-timeout-s` — hard wall timeout per file in seconds; `0` disables timeout.
- `--resume` — skip files that already have `status=ok` in progress JSONL.
- `--progress-file` — path to JSONL checkpoint file.

## Progress JSONL format

Each processed file appends one JSON line:

```json
{"path":"/abs/file.pdf","status":"ok|fail|timeout|skip","document_id":"...","work_id":"...","started_at":"...","finished_at":"...","error":null}
```

Use the same `--progress-file` path with `--resume` after interruption:

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --resume \
  --progress-file eval/results/ingest-progress-wave5.jsonl
```

## Live log streaming

If you tee logs, force line buffering so progress is visible in real time:

```bash
stdbuf -oL .venv/bin/science-graphrag ingest-corpus /path/to/corpus | tee ingest.log
```

or:

```bash
unbuffer .venv/bin/science-graphrag ingest-corpus /path/to/corpus | tee ingest.log
```
