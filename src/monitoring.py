"""Datapizza Monitoring (OTLP tracing) for Hackapizza multi-agent system.

Optional: set DATAPIZZA_MONITORING_API_KEY and DATAPIZZA_PROJECT_ID in .env
to enable tracing. Exports `tracer` (or None if disabled).
"""
from src.config import (
    DATAPIZZA_MONITORING_API_KEY,
    DATAPIZZA_PROJECT_ID,
    DATAPIZZA_OTLP_ENDPOINT,
)

tracer = None
if DATAPIZZA_MONITORING_API_KEY and DATAPIZZA_PROJECT_ID:
    try:
        from datapizza.tracing import DatapizzaMonitoringInstrumentor

        instrumentor = DatapizzaMonitoringInstrumentor(
            api_key=DATAPIZZA_MONITORING_API_KEY,
            project_id=DATAPIZZA_PROJECT_ID,
            endpoint=DATAPIZZA_OTLP_ENDPOINT,
        )
        instrumentor.instrument()
        tracer = instrumentor.get_tracer(__name__)
    except ImportError:
        pass
