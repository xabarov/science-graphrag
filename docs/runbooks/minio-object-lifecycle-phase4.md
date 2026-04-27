# MinIO / S3 object lifecycle (Phase 4)

Phase 4 writes **S3 object tags** on diagnostic and benchmark full-run uploads (`retention_class`, `written_at`, optional `retention_hint_days`, etc.). You can expire objects using **bucket lifecycle rules** (no app code) and/or the **`scripts/gc_object_storage.py`** helper (list by age, `--dry-run`, optional summary fixup).

## Environment hints

See `.env.example` for:

- `SCIENCE_GRAPHRAG_OBJECT_STORAGE_DIAGNOSTICS_RETENTION_DAYS` — stored as tag/metadata hint for diagnostics (0 = omit).
- `SCIENCE_GRAPHRAG_OBJECT_STORAGE_BENCHMARK_FULL_RETENTION_DAYS` — same for UI benchmark `full.json` in S3.

Defaults in `Settings`: diagnostics **30**, benchmark full **90** (days as operational hints for GC; they do not auto-delete by themselves).

## AWS S3 lifecycle (XML example)

Attach to the bucket that holds `science-diagnostics` and `science-benchmarks` prefixes (often the same `science-raw` bucket). Adjust `<Days>` to your policy.

```xml
<LifecycleConfiguration>
  <Rule>
    <ID>expire-diagnostics</ID>
    <Status>Enabled</Status>
    <Filter>
      <Prefix>science-diagnostics/</Prefix>
    </Filter>
    <Expiration>
      <Days>45</Days>
    </Expiration>
    <NoncurrentVersionExpiration>
      <NoncurrentDays>7</NoncurrentDays>
    </NoncurrentVersionExpiration>
  </Rule>
  <Rule>
    <ID>expire-benchmark-full-json</ID>
    <Status>Enabled</Status>
    <Filter>
      <Prefix>science-benchmarks/</Prefix>
    </Filter>
    <Expiration>
      <Days>120</Days>
    </Expiration>
  </Rule>
</LifecycleConfiguration>
```

Apply with AWS CLI:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket science-raw \
  --lifecycle-configuration file://lifecycle.json
```

(`lifecycle.json` wraps the XML in JSON per [S3 API lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/how-to-set-lifecycle-configuration-intro.html).)

## MinIO

MinIO supports lifecycle configuration on buckets. Use **mc** (MinIO Client) or the MinIO console to set rules equivalent to the prefixes above. Validate against your MinIO version (lifecycle filter semantics can differ slightly from AWS).

## Application GC script

For selective deletes, tagging filters, or clearing `full_run_object_key` in local `*.summary.json` after removing stale benchmark objects, use:

```bash
.venv/bin/python scripts/gc_object_storage.py --help
```

Prefer **`--dry-run`** first.

Exit codes for `scripts/gc_object_storage.py`: **0** success, **1** misconfiguration (object storage off), **2** S3 reported `delete_objects` errors (see stderr JSON `delete_errors`).
