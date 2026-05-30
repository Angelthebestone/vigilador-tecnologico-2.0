from prometheus_client import Counter, Gauge, make_asgi_app

llm_calls_total = Counter(
    "vigilador_llm_calls_total", "Total LLM API calls", ["provider", "model", "status"]
)

tool_invocations_total = Counter(
    "vigilador_tool_invocations_total", "Total tool invocations", ["tool", "status"]
)

tool_health_status = Gauge(
    "vigilador_tool_health_status", "Current tool health status (1=UP, 0=DOWN)", ["name", "domain"]
)

pi_quarantined_total = Counter(
    "vigilador_pi_quarantined_total",
    "Total inputs quarantined by PI detector",
    ["source", "severity"],
)

metrics_app = make_asgi_app()
