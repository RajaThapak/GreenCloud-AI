"""Suggested minimum requirements per workload type (the 'Suggested requirements' panel)."""

PRESETS = {
    "ML training": {"vcpu": 8, "memory_gb": 32, "gpus": 1},
    "Batch / ETL": {"vcpu": 4, "memory_gb": 16, "gpus": 0},
    "Rendering": {"vcpu": 8, "memory_gb": 32, "gpus": 1},
    "Simulation": {"vcpu": 16, "memory_gb": 64, "gpus": 0},
}


def suggest(workload_type: str, needs_gpu: bool) -> dict:
    p = dict(PRESETS[workload_type])
    p["gpus"] = max(p["gpus"], 1) if needs_gpu else 0
    p["note"] = "Based on typical jobs of this type, with some headroom. Change them if you know your job needs more."
    return p
