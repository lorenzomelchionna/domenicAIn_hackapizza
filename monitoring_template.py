DATAPIZZA_OTLP_ENDPOINT = "https://datapizza-monitoring.datapizza.tech/gateway/v1/traces"
 
instrumentor = DatapizzaMonitoringInstrumentor(
    api_key=API_KEY,
    project_id=PROJECT_ID,
    endpoint=DATAPIZZA_OTLP_ENDPOINT,
)
instrumentor.instrument()
tracer = instrumentor.get_tracer(__name__)
 
with tracer.start_as_current_span("trace_name"):
    do_something()