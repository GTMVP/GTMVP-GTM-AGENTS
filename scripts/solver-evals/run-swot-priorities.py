#!/usr/bin/env python
"""
Reference runner for SWOT priorities knapsack scenarios.

Mirrors Template 2 from skills/solver-patterns/SKILL.md exactly.
Given a scenario JSON (swot-priorities-N.json), this script:

1. Builds the Z3 Optimize model (0/1 knapsack with category coverage).
2. Solves with timeout=10s.
3. Validates selection against expected status.
4. Prints a JSON result object the JS harness consumes.

Usage:
    python run-swot-priorities.py <scenario.json>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

try:
    from z3 import Bool, If, Optimize, Or, Solver, Sum, sat, unsat
except ImportError:
    print(json.dumps({"error": "z3-solver not installed. Run from mcp-solver venv or pip install z3-solver."}))
    sys.exit(1)


def solve_scenario(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    item_ids: list[str] = inputs["item_ids"]
    values: list[int | float] = inputs["values"]
    costs: list[int | float] = inputs["costs"]
    total_capacity: float = float(inputs["total_capacity"])
    categories: list[list[str]] = inputs["categories"]
    must_cover: list[str] = inputs.get("must_cover_categories", [])
    max_concurrent: int | None = inputs.get("max_concurrent")
    N = len(item_ids)

    picked = [Bool(f"picked_{i}") for i in range(N)]

    feas = Solver()
    feas.set(unsat_core=True)

    feas.assert_and_track(
        Sum([If(picked[i], costs[i], 0) for i in range(N)]) <= total_capacity,
        "capacity_cap",
    )

    if max_concurrent is not None:
        feas.assert_and_track(
            Sum([If(p, 1, 0) for p in picked]) <= max_concurrent,
            "max_concurrent",
        )

    for cat in must_cover:
        covering = [picked[i] for i in range(N) if cat in categories[i]]
        if covering:
            feas.assert_and_track(Or(covering), f"cover_{cat}")
        else:
            feas.assert_and_track(Bool(f"impossible_{cat}"), f"uncoverable_{cat}")

    t0 = time.perf_counter()
    feas_result = feas.check()
    elapsed_feas = (time.perf_counter() - t0) * 1000

    if feas_result == unsat:
        core = [str(c) for c in feas.unsat_core()]
        return {
            "status": "infeasible",
            "unsatCore": core,
            "solveTimeMs": round(elapsed_feas, 2),
        }

    opt = Optimize()
    opt.set("timeout", 10000)

    opt_picked = [Bool(f"picked_{i}") for i in range(N)]

    opt.add(Sum([If(opt_picked[i], costs[i], 0) for i in range(N)]) <= total_capacity)

    if max_concurrent is not None:
        opt.add(Sum([If(p, 1, 0) for p in opt_picked]) <= max_concurrent)

    for cat in must_cover:
        covering = [opt_picked[i] for i in range(N) if cat in categories[i]]
        if covering:
            opt.add(Or(covering))

    opt.maximize(Sum([If(opt_picked[i], values[i], 0) for i in range(N)]))

    t0_opt = time.perf_counter()
    result = opt.check()
    elapsed_opt = (time.perf_counter() - t0_opt) * 1000

    if result != sat:
        return {"status": "timeout", "solveTimeMs": round(elapsed_feas + elapsed_opt, 2)}

    model = opt.model()
    selected = []
    dropped = []
    for i, iid in enumerate(item_ids):
        val = model[opt_picked[i]]
        if val is not None and bool(val):
            selected.append(iid)
        else:
            dropped.append({"id": iid, "freedHours": costs[i]})

    total_value = sum(values[i] for i in range(N) if item_ids[i] in selected)
    total_hours = sum(costs[i] for i in range(N) if item_ids[i] in selected)

    covered_cats = set()
    for i in range(N):
        if item_ids[i] in selected:
            covered_cats.update(categories[i])
    uncovered_threats = [cat for cat in must_cover if cat not in covered_cats]

    return {
        "status": "optimal",
        "selectedPriorities": selected,
        "droppedPriorities": dropped,
        "totalValue": total_value,
        "totalHoursAllocated": total_hours,
        "remainingCapacity": total_capacity - total_hours,
        "uncoveredThreats": uncovered_threats,
        "solveTimeMs": round(elapsed_feas + elapsed_opt, 2),
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
        out["selectedPriorities"] = solver_result["selectedPriorities"]
        out["droppedPriorities"] = solver_result["droppedPriorities"]
        out["totalValue"] = solver_result["totalValue"]
        out["totalHoursAllocated"] = solver_result["totalHoursAllocated"]
        out["remainingCapacity"] = solver_result["remainingCapacity"]
        out["uncoveredThreats"] = solver_result["uncoveredThreats"]

        max_concurrent = scenario["inputs"].get("max_concurrent")
        if max_concurrent is not None:
            out["passes"]["withinConcurrentLimit"] = len(solver_result["selectedPriorities"]) <= max_concurrent

        out["passes"]["withinCapacity"] = solver_result["totalHoursAllocated"] <= float(scenario["inputs"]["total_capacity"])
        out["passes"]["threatsAddressed"] = len(solver_result["uncoveredThreats"]) == 0

    elif solver_result["status"] == "infeasible":
        out["unsatCore"] = solver_result.get("unsatCore", [])
        out["passes"]["hasUnsatCore"] = bool(out["unsatCore"])

    out["allPass"] = all(out["passes"].values())
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: run-swot-priorities.py <scenario.json>"}))
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
