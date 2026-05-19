#!/usr/bin/env python
"""
Reference runner for TAM/SAM/SOM horizon scheduling scenarios.

Mirrors Template 5 from skills/solver-patterns/SKILL.md exactly.
Given a scenario JSON (tam-horizons-N.json), this script:

1. Builds the Z3 Optimize model (scheduling with dependencies).
2. Solves with timeout=15s.
3. Validates the schedule against expected status + dependency ordering.
4. Prints a JSON result object the JS harness consumes.

Usage:
    python run-tam-horizons.py <scenario.json>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

try:
    from z3 import And, Bool, If, Implies, Int, Optimize, Sum, sat
except ImportError:
    print(json.dumps({"error": "z3-solver not installed. Run from mcp-solver venv or pip install z3-solver."}))
    sys.exit(1)


def solve_scenario(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    init_ids: list[str] = inputs["init_ids"]
    values: list[int | float] = inputs["values"]
    effort: list[int | float] = inputs["effort"]
    horizons: list[str] = inputs["horizons"]
    horizon_capacity: list[int | float] = inputs["horizon_capacity"]
    dependencies: list[list[int]] = [list(d) for d in inputs.get("dependencies", [])]
    N = len(init_ids)
    H = len(horizons)

    assigned = [Int(f"horizon_{i}") for i in range(N)]
    scheduled = [Bool(f"scheduled_{i}") for i in range(N)]

    opt = Optimize()
    opt.set("timeout", 15000)

    for i in range(N):
        opt.add(assigned[i] >= -1)
        opt.add(assigned[i] < H)
        opt.add(scheduled[i] == (assigned[i] >= 0))

    for h in range(H):
        opt.add(
            Sum([If(assigned[i] == h, effort[i], 0) for i in range(N)])
            <= horizon_capacity[h]
        )

    for down, up in dependencies:
        opt.add(
            Implies(
                scheduled[down],
                And(scheduled[up], assigned[down] >= assigned[up]),
            )
        )

    opt.maximize(Sum([If(scheduled[i], values[i], 0) for i in range(N)]))

    t0 = time.perf_counter()
    result = opt.check()
    elapsed = (time.perf_counter() - t0) * 1000

    if result != sat:
        return {"status": "timeout", "solveTimeMs": round(elapsed, 2)}

    model = opt.model()

    schedule: dict[str, list[dict]] = {h: [] for h in horizons}
    dropped: list[dict] = []
    total_value = 0

    for i, iid in enumerate(init_ids):
        aval = model[assigned[i]]
        if aval is None:
            h_idx = -1
        else:
            h_idx = aval.as_long()

        if h_idx >= 0:
            schedule[horizons[h_idx]].append({"id": iid, "effort": effort[i], "value": values[i]})
            total_value += values[i]
        else:
            dropped.append({"id": iid, "effort": effort[i], "value": values[i]})

    capacity_used = {}
    for h_name, items in schedule.items():
        capacity_used[h_name] = sum(item["effort"] for item in items)

    dep_map: dict[int, list[int]] = {}
    for down, up in dependencies:
        dep_map.setdefault(down, []).append(up)

    def find_critical_path() -> list[str]:
        memo: dict[int, list[int]] = {}

        def longest(i: int) -> list[int]:
            if i in memo:
                return memo[i]
            best: list[int] = [i]
            for down in range(N):
                if any(up == i for up, _ in [(u, d) for d, u in dependencies if d == down]):
                    continue
            for j in range(N):
                if any(up == i and down == j for down, up in dependencies):
                    candidate = [i] + longest(j)
                    if len(candidate) > len(best):
                        best = candidate
            memo[i] = best
            return best

        all_paths = [longest(i) for i in range(N)]
        if not all_paths:
            return []
        longest_path = max(all_paths, key=len)
        return [init_ids[i] for i in longest_path]

    critical_path = find_critical_path()

    return {
        "status": "optimal",
        "schedule": schedule,
        "dropped": dropped,
        "totalValue": total_value,
        "capacityUsed": capacity_used,
        "criticalPath": critical_path,
        "solveTimeMs": round(elapsed, 2),
    }


def evaluate(scenario_path: Path) -> dict:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    solver_result = solve_scenario(scenario)
    expected_status = scenario.get("expected_solver_status", "optimal")

    out = {
        "scenario": scenario_path.stem,
        "solverStatus": solver_result["status"],
        "solveTimeMs": solver_result.get("solveTimeMs", 0),
        "passes": {},
    }

    out["passes"]["statusMatch"] = (solver_result["status"] == expected_status)

    if solver_result["status"] == "optimal":
        out["schedule"] = solver_result["schedule"]
        out["dropped"] = solver_result["dropped"]
        out["totalValue"] = solver_result["totalValue"]
        out["capacityUsed"] = solver_result["capacityUsed"]
        out["criticalPath"] = solver_result["criticalPath"]

        inputs = scenario["inputs"]
        horizon_capacity = inputs["horizon_capacity"]
        horizons = inputs["horizons"]
        for h_idx, h_name in enumerate(horizons):
            used = solver_result["capacityUsed"].get(h_name, 0)
            if used > horizon_capacity[h_idx]:
                out["passes"][f"capacity_{h_name}"] = False
            else:
                out["passes"][f"capacity_{h_name}"] = True

        deps = [list(d) for d in inputs.get("dependencies", [])]
        init_ids = inputs["init_ids"]
        horizon_of: dict[str, int] = {}
        for h_idx, h_name in enumerate(horizons):
            for item in solver_result["schedule"].get(h_name, []):
                horizon_of[item["id"]] = h_idx
        dep_ok = True
        for down, up in deps:
            down_id = init_ids[down]
            up_id = init_ids[up]
            if down_id in horizon_of and up_id in horizon_of:
                if horizon_of[down_id] < horizon_of[up_id]:
                    dep_ok = False
            elif down_id in horizon_of and up_id not in horizon_of:
                dep_ok = False
        out["passes"]["dependencyOrdering"] = dep_ok

        if scenario.get("expected_all_scheduled"):
            all_scheduled = len(solver_result["dropped"]) == 0
            out["passes"]["allScheduled"] = all_scheduled

        if scenario.get("expected_some_dropped"):
            out["passes"]["someDropped"] = len(solver_result["dropped"]) > 0

    out["allPass"] = all(out["passes"].values())
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: run-tam-horizons.py <scenario.json>"}))
        sys.exit(1)

    scenario_path = Path(sys.argv[1])
    if not scenario_path.exists():
        print(json.dumps({"error": f"Scenario file not found: {scenario_path}"}))
        sys.exit(1)

    try:
        result = evaluate(scenario_path)
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}", "scenario": scenario_path.stem}))
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["allPass"] else 1)


if __name__ == "__main__":
    main()
