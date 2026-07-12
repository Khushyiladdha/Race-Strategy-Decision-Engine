"""Report generation — structured JSON (Stage 5) and a downloadable PDF (Stage 8)."""
import sys
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.api import schemas, services
from app.api.deps import get_db
from app.api.version import ENGINE_VERSION

router = APIRouter(tags=["report"])


@router.post(
    "/report/generate",
    summary="Generate a strategy report",
    description="Structured report for one circuit: the recommended strategy, its historical "
    "validation, the executive summary, and the confidence note.",
    response_model=schemas.ReportResponse,
    responses={404: {"description": "Unknown circuit"}, 422: {"description": "Circuit cannot generate"}},
)
def generate_report(req: schemas.ReportRequest, session=Depends(get_db)) -> schemas.ReportResponse:
    return services.build_report(session, req)


@router.get(
    "/report/pdf/{circuit_key}",
    summary="Download a strategy report as a PDF",
    description="Renders the one-page briefing (Jinja2 + WeasyPrint) and returns it as a downloadable "
    "PDF. Needs WeasyPrint's native stack (present in the Docker/Linux deploy).",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "The report PDF"},
        404: {"description": "Unknown circuit"},
        422: {"description": "Circuit cannot generate"},
        503: {"description": "PDF rendering unavailable in this environment"},
    },
)
def report_pdf(
    circuit_key: str,
    n_sims: int = Query(default=2000),
    seed: int = Query(default=0),
    session=Depends(get_db),
) -> Response:
    from app.report.renderer import ReportMeta, render_report_pdf

    report = services.build_report(
        session, schemas.ReportRequest(circuit_key=circuit_key, n_sims=n_sims, seed=seed)
    )
    meta = ReportMeta(
        generated=date.today().isoformat(),
        engine_version=ENGINE_VERSION,
        n_sims=n_sims,
        seed=seed,
        ranking="Mean",
    )

    try:
        pdf_bytes = render_report_pdf(report, meta)
    except (ImportError, OSError) as exc:  # WeasyPrint or its native libs unavailable
        return Response(
            content=f"PDF rendering unavailable: {exc}",
            status_code=503,
            media_type="text/plain",
        )

    filename = f"race-strategy-{circuit_key.lower()}-{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
