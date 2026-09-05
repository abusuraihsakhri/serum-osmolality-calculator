# Serum Osmolality Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** CAP / CLSI / ISO Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

Serum Osmolality Calculator is a clinical decision support tool that computes:

- **Calculated serum osmolality** and **osmolar gap**
- **MELD-Na** (Model for End-Stage Liver Disease with sodium)
- **QTc** (corrected QT interval, Bazett's formula)
- **BMI** (body mass index)
- **HbA1c ↔ eAG** conversion (estimated average glucose)
- **APRI / FIB-4** liver fibrosis indices

It also provides a multi-agent audit pipeline with PHI outbound protection and a tamper-evident HMAC-SHA256 audit trail.

---

## Key Capabilities & Algorithmic Modules

### Clinical Calculation Functions

| Function | Description | Required Inputs |
|:---------|:------------|:----------------|
| `calculate_meld_na()` | MELD-Na score for liver disease severity | bilirubin, creatinine, inr, sodium |
| `calculate_qtc()` | QTc via Bazett's formula | qt_ms/qt + (rr_ms or hr_bpm) |
| `calculate_bmi_z()` | Body mass index | weight_kg, height_cm |
| `convert_hba1c()` | HbA1c ↔ estimated average glucose | hba1c_percent or eag_mgdl |
| `calculate_apri_fib4()` | APRI and FIB-4 liver fibrosis indices | ast_u_l, platelets_109 |
| `calculate_score()` | Generic weighted-score fallback | any numeric inputs |

### Routing

`assess_row(row)` inspects a dictionary of lab values and automatically routes to the appropriate calculator based on the keys present.

---

## Quickstart

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
pip install -e ".[dev]"
```

### Environment Configuration

Copy `.env.example` to `.env` and set a strong audit key:

```bash
cp .env.example .env
# Edit .env and set AUDIT_SECRET_KEY to a random value:
#   python -c "import secrets; print(secrets.token_hex(32))"
```

### CLI Usage

**Single calculation (JSON input):**
```bash
python cli.py single --json '{"bilirubin": 2.0, "creatinine": 1.5, "inr": 1.2, "sodium": 135}'
```

**Single calculation (named args):**
```bash
python cli.py single --bili 2.0 --creat 1.5 --inr 1.2 --na 135
```

**Batch CSV processing:**
```bash
python cli.py batch --input sample.csv --output results.csv
```

**Interactive agent audit:**
```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
```

**Verify audit trail integrity:**
```bash
python cli.py verify-audit
```

**Launch REST API server:**
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API Endpoints

| Method | Path | Description |
|:-------|:-----|:------------|
| GET | `/health` | Health and metadata |
| GET | `/metrics` | Operational metrics |
| POST | `/api/audit` | Submit task payload for multi-agent evaluation |
| POST | `/api/chat` | Supervisory conversational query |
| GET | `/api/audit/logs` | Retrieve and verify HMAC audit trail |

---

## Testing

Run the full test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest -v --cov=. --cov-report=term-missing
```

---

## Container Deployment

### Docker

```bash
docker build -t serum-osmolality-calculator .
docker run -p 8000:8000 --env-file .env serum-osmolality-calculator
```

### Docker Compose

```bash
docker compose up --build
```

---

## Security

- **Zero-PHI Outbound Interceptor:** AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers.
- **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation.
- **Path Traversal Protection:** All file I/O validates paths against traversal sequences and unsafe characters.
- **Configurable Audit Key:** The HMAC signing key is read from the `AUDIT_SECRET_KEY` environment variable — never hardcoded.

---

## Project Structure

```
serum-osmolality-calculator/
├── agents/                  # Multi-agent audit pipeline
│   ├── base.py              # PHI guard, HMAC audit trail
│   ├── models.py            # Pydantic schemas
│   ├── supervisor.py        # Orchestrator
│   ├── workers.py           # Specialized evaluation workers
│   ├── api.py               # FastAPI REST server
│   ├── metrics.py           # Prometheus metrics
│   ├── learning.py          # Bayesian calibration engine
│   ├── llm_factory.py       # LLM provider abstraction
│   └── streamer.py          # WebSocket telemetry
├── tests/                   # Pytest test suite
├── web/index.html           # Operations console UI
├── cli.py                   # CLI entry point
├── osmolality.py            # Core clinical calculations
├── enrichment.py            # Enrichment feature engines
├── simulator.py             # High-throughput stress simulator
├── pyproject.toml           # Project metadata and dependencies
├── Dockerfile               # Container build
├── docker-compose.yml       # Compose orchestration
└── .env.example             # Environment template
```

---

## License

MIT License — see [LICENSE](LICENSE).
