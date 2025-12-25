"""Audit and compliance endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from ..core.service import HideXService
from ..schemas.responses import AuditLogResponse, AuditEntryResponse, ComplianceReportResponse

router = APIRouter(prefix="/audit", tags=["audit"])

# Service instance
_service: Optional[HideXService] = None


def get_service() -> HideXService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = HideXService()
    return _service


@router.get("/current", response_model=AuditLogResponse)
async def get_current_audit_log(service: HideXService = Depends(get_service)):
    """Get the current session's audit log."""
    log = service.get_audit_log()
    return AuditLogResponse(
        id=log.id,
        name=log.name,
        started_at=log.started_at,
        ended_at=log.ended_at,
        total_entries=log.total_entries,
        entries=[
            AuditEntryResponse(
                id=e.id,
                timestamp=e.timestamp,
                event_type=e.event_type.value,
                summary=e.summary,
                plan_id=e.plan_id,
                tx_hash=e.tx_hash,
            )
            for e in log.entries
        ],
    )


@router.get("/sessions")
async def list_audit_sessions(service: HideXService = Depends(get_service)):
    """List all available audit sessions."""
    sessions = service.list_audit_sessions()
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}", response_model=AuditLogResponse)
async def get_audit_session(
    session_id: str,
    service: HideXService = Depends(get_service)
):
    """Load and return a previous audit session."""
    log = service.load_audit_session(session_id)
    if not log:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return AuditLogResponse(
        id=log.id,
        name=log.name,
        started_at=log.started_at,
        ended_at=log.ended_at,
        total_entries=log.total_entries,
        entries=[
            AuditEntryResponse(
                id=e.id,
                timestamp=e.timestamp,
                event_type=e.event_type.value,
                summary=e.summary,
                plan_id=e.plan_id,
                tx_hash=e.tx_hash,
            )
            for e in log.entries
        ],
    )


@router.get("/reports/{plan_id}", response_model=ComplianceReportResponse)
async def get_compliance_report(
    plan_id: str,
    session_id: Optional[str] = None,
    service: HideXService = Depends(get_service)
):
    """
    Generate a compliance report for a transaction plan.
    
    Designed for forensic review and regulatory compliance.
    """
    report = service.generate_compliance_report(plan_id)
    
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    
    return ComplianceReportResponse(**report)
