# Data and benchmarks

Each product owns a data namespace, for example `data/tenderlens/`:

```text
raw/          Original public inputs and provenance metadata
extracted/    Deterministic text/OCR outputs
gold/         Human-reviewed expected structured results
adversarial/  Deliberately difficult and malformed cases
manifests/    Checksums, licences, splits, and dataset versions
```

Never commit credentials, customer documents, or unlicensed content.
