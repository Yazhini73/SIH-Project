"""Deterministic aggregation of independent parameter statuses."""

STATUS_RANK = {"GOOD": 0, "MODERATE": 1, "BAD": 2}


def calculate_overall(results: dict) -> dict[str, str]:
    valid = {name: item for name, item in results.items() if item.get("status") in STATUS_RANK}
    if len(valid) != 4:
        raise ValueError("Overall quality requires valid pH, ammonia, protein, and moisture results.")
    worst = max(valid.items(), key=lambda item: STATUS_RANK[item[1]["status"]])
    display_name = {"ph": "pH", "ammonia": "Ammonia", "protein": "Protein", "moisture": "Moisture"}[worst[0]]
    return {
        "status": worst[1]["status"],
        "status_color": {"GOOD": "green", "MODERATE": "yellow", "BAD": "red"}[worst[1]["status"]],
        "reason": f"{display_name} requires attention." if worst[1]["status"] != "GOOD" else "All measured parameters are within the configured good ranges.",
    }
