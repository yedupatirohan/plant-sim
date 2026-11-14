"""Inject labelled anomalies into a COPY of the baseline. Returns series + ground truth."""
import numpy as np

SCENARIOS = ["LEAK", "BLOCKAGE", "PUMP_DEGRADATION", "SENSOR_FAULT"]
ALARM_FOR = {"LEAK": "LEAK", "BLOCKAGE": "BLOCKAGE",
             "PUMP_DEGRADATION": "PUMP_DEGRADATION", "SENSOR_FAULT": "SENSOR_FAULT"}


def _pump_sensors(sensors: list[dict]) -> dict:
    """pump_id -> {'FLOW': sensor_id, 'PRESSURE': sensor_id}"""
    out: dict = {}
    for s in sensors:
        if s["component_type"] == "PUMP":
            out.setdefault(s["component_id"], {})[s["measurement"]] = s["sensor_id"]
    return {k: v for k, v in out.items() if "FLOW" in v and "PRESSURE" in v}


def inject_anomalies(baseline: dict, sensors: list[dict], seed: int,
                     per_type: int = 2, length: int = 60) -> dict:
    steps = len(baseline["timestamps"])
    ts = baseline["timestamps"]
    series = {k: v.copy() for k, v in baseline["series"].items()}  # never mutate baseline
    rng = np.random.default_rng(seed + 2)

    pumps = sorted(_pump_sensors(sensors).items())
    chosen = rng.permutation(len(pumps))  # distinct pumps, so scenarios never overlap
    n_total = per_type * len(SCENARIOS)
    if n_total > len(pumps):
        raise ValueError("not enough pumps for the requested scenario count")

    truth, k = [], 0
    for scen in SCENARIOS:
        for _ in range(per_type):
            pump_id, sens = pumps[int(chosen[k])]
            k += 1
            start = int(rng.integers(100, steps - length - 1))
            end = start + length
            sl = slice(start, end)
            flow, pres = sens["FLOW"], sens["PRESSURE"]

            if scen == "LEAK":
                series[flow][sl] *= 0.75
                series[pres][sl] *= 0.85
                affected, rule = [flow, pres], "flow -25% and pressure -15% together"
            elif scen == "BLOCKAGE":
                series[flow][sl] *= 0.60
                series[pres][sl] *= 1.20
                affected, rule = [flow, pres], "flow -40% while pressure +20%"
            elif scen == "PUMP_DEGRADATION":
                ramp = np.linspace(1.0, 0.70, length)
                series[flow][sl] *= ramp
                series[pres][sl] *= ramp
                affected, rule = [flow, pres], "flow and pressure ramp down to -30%"
            else:  # SENSOR_FAULT: only ONE sensor changes, its partner stays normal
                series[flow][sl] = series[flow][start]  # stuck value
                affected, rule = [flow], "flow sensor stuck; pressure sensor unaffected"

            truth.append({
                "scenario_id": f"SCN-{len(truth) + 1:03d}",
                "issue_type": scen,
                "component_id": pump_id,
                "sensor_ids": ";".join(affected),
                "start_ts": ts[start].isoformat(),
                "end_ts": ts[end - 1].isoformat(),
                "expected_alarm_type": ALARM_FOR[scen],
                "rule_applied": rule,
            })

    return {"series": series, "ground_truth": truth}