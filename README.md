# Serum Osmolality Calculator

Calculate an **estimated serum osmolality**, **effective osmolality (tonicity)**, and—when a measured laboratory value is available—the **osmolal gap**. A static browser calculator, Python functions, CLI, and FastAPI endpoint are provided.

## Calculation

| Quantity | Conventional laboratory units | SI units |
| --- | --- | --- |
| Estimated osmolality | `2 × Na + glucose/18 + BUN/2.8` | `2 × Na + glucose + urea` |
| Effective osmolality | `2 × Na + glucose/18` | `2 × Na + glucose` |
| Osmolal gap | `measured osmolality − estimated osmolality` | Same |

- Sodium is in mmol/L in both systems; glucose and BUN are **mg/dL** in conventional units. SI glucose and **urea** are in mmol/L (do not substitute BUN for urea).
- Reported outputs are approximate mOsm/kg. Calculated osmolality is **not** an osmometer measurement. The basic formula does not include ethanol or other unmeasured osmoles.
- Example: sodium 140 mmol/L, glucose 90 mg/dL, BUN 14 mg/dL → estimated **290 mOsm/kg**, effective **285 mOsm/kg**. A measured 300 mOsm/kg produces a **+10 mOsm/kg** gap.
- The choice of equation affects the osmolal gap. Interpret results using the laboratory's methods, reference intervals, and clinical context.

Sources: [Serum osmolal gap (UpToDate)](https://www.uptodate.com/contents/serum-osmolal-gap) and [University of Iowa Healthcare: osmolality gap](https://www.healthcare.uiowa.edu/path_handbook/appendix/chem/osmo_gap.html) (describes an alternative formula).

## Browser app

Open `web/index.html` in a modern browser, or serve the `web/` directory through any static file server. The form supports conventional and SI units, validation, numerical contribution breakdown, and optional measured osmolality. The browser application requires **no backend, Pyodide, build step, third-party JavaScript, or remote font**.

All values entered in the browser are processed in memory only. The static page does not submit laboratory values, use browser storage, or make API requests. Avoid patient identifiers.

## Python and CLI

Requires Python 3.10+. From the project root:

```bash
python -m pip install -e ".[dev]"
serum-osmolality calculate --sodium 140 --glucose 90 --bun 14 --measured-osmolality 300
serum-osmolality calculate --si --sodium 140 --glucose 5 --urea 5
serum-osmolality osm-batch --input sample.csv --output results.csv
```

Python usage:

```python
from serum import calculate_osmolality
result = calculate_osmolality(sodium=140, glucose=90, bun=14, measured_osmolality=300)
# {'calculated_osmolality': 290.0, 'effective_osmolality': 285.0, 'osmolal_gap': 10.0}
```

Input validation rejects missing, negative, or non-finite concentrations and mismatched units. Batch input CSV rows use `sodium,glucose,bun` (conventional) or `sodium,glucose,urea,unit_system` (SI), with optional `measured_osmolality`.

## API and local service

```bash
serum-osmolality serve --host 127.0.0.1 --port 8000
```

The live service serves the same browser UI at `/`. POST JSON to `/api/osmolality`:

```json
{"sodium": 140, "glucose": 90, "bun": 14, "measured_osmolality": 300}
```

The response includes `calculated_osmolality`, `effective_osmolality`, and `osmolal_gap`. API documentation is at `/docs`.

Existing `audit`, `batch`, `chat`, and `verify-audit` CLI commands and the legacy agent endpoints remain available for compatibility. Their agent thresholds, mock provider, and enrichment features are **illustrative implementations**, not clinically validated monitoring, risk stratification, EHR integration, or AI analysis. The API has no authentication; do not expose it publicly for patient data.

For the optional in-memory HMAC audit trail, configure `AUDIT_SECRET_KEY` with a strong random value. When unset, an ephemeral random key is used. The identifier-pattern guard is not a reliable PHI de-identification service; do not process identifiable patient data. Audit records are not persisted across restarts.

## Tests and development

```bash
python -m pytest -q
node --test tests/*.test.cjs  # Node.js 20+; no npm dependencies
```

GitHub Actions tests Python 3.10–3.12 and browser calculations. A separate workflow deploys `web/` to GitHub Pages after a push to `master`. The static calculator works in current Chromium, Firefox, and Safari-compatible browsers; browser/device-specific compatibility has not been exhaustively validated.

## License

MIT — see [LICENSE](LICENSE).

**Scope:** Educational and research use. Not a medical device or a replacement for measured laboratory osmolality, toxicology workup, or clinical judgment.
