# AWS Official Pack Import Steps

Use this when environment networking is unavailable and assets must be dropped manually.

## 1) Download official package

- Open: https://aws.amazon.com/architecture/icons/
- Download the latest official asset package zip.

## 2) Place files locally

1. Put the zip in: `assets/third-party-icons/aws/raw/`
2. Extract selected SVG subset into: `assets/third-party-icons/aws/processed/`

Suggested subset categories for starter ingestion:
- `compute/`
- `storage/`
- `network/`

## 3) Generate shape manifest

Run:

```bash
npm run shape-pack:manifest -- \
  assets/third-party-icons/aws/processed \
  assets/third-party-icons/aws/processed/aws-starter-pack.manifest.json \
  aws-official-starter-v1 \
  "AWS Official Starter Pack" \
  1.0.0 \
  "Amazon Web Services"
```

## 4) Validate before wiring

Run:

```bash
npx tsc -b --pretty false
npm run test -- --run \
  src/services/shapeLibrary/ingestionPipeline.test.ts \
  src/services/shapeLibrary/manifestValidation.test.ts \
  src/services/templates.selector.test.ts
```
