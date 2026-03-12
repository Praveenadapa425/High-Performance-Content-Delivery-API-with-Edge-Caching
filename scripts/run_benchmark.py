import json
import time
from statistics import mean

import requests

BASE_URL = "http://localhost:8000"
ITERATIONS = 20


def main() -> None:
    latencies = []
    errors = 0
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=3)
            if response.status_code != 200:
                errors += 1
        except requests.RequestException:
            errors += 1
        latencies.append((time.perf_counter() - start) * 1000)

    summary = {
        "iterations": ITERATIONS,
        "avg_latency_ms": round(mean(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
        "errors": errors,
        "note": "Phase 1 baseline benchmark against health endpoint.",
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
