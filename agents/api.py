"""
FastAPI REST API Server for Serum Osmolality Calculator.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from serum import calculate_osmolality
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Serum Osmolality Calculator API",
    description="Serum laboratory osmolality estimates; legacy audit endpoints are demonstrations",
    version="3.1.0",
)


class OsmolalityRequest(BaseModel):
    sodium: float = Field(gt=0)
    glucose: float = Field(ge=0)
    bun: float | None = Field(default=None, ge=0)
    urea: float | None = Field(default=None, ge=0)
    measured_osmolality: float | None = Field(default=None, ge=0)
    unit_system: str = "conventional"

    @field_validator("sodium", "glucose", "bun", "urea", "measured_osmolality")
    @classmethod
    def finite_values(cls, value):
        import math
        if value is not None and not math.isfinite(value):
            raise ValueError("Inputs must be finite")
        return value


@app.post("/api/osmolality")
def api_osmolality(payload: OsmolalityRequest):
    try:
        return calculate_osmolality(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class ChatRequest(BaseModel):
    query: str


@app.get("/")
def index():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


@app.get("/app.js")
def app_js():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "app.js", media_type="text/javascript")


@app.get("/calculator.js")
def calculator_js():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "calculator.js", media_type="text/javascript")


@app.get("/health")
def health():
    return {"status": "running", "service": "serum-osmolality-calculator", "version": "3.1.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "service_status": "running"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_blocks_total": len(AuditLogger.get_trail()), "verified": AuditLogger.verify_integrity()}
