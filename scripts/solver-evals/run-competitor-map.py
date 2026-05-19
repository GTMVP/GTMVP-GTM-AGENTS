#!/usr/bin/env python
"""
Reference runner for /competitor-map set-cover scenarios.

Mirrors Template 4 from skills/solver-patterns/SKILL.md exactly.
Given a scenario JSON (competitor-map-N.json), this script:

1. Builds the Z3 Optimize model (min-cost set cover).
2. Solves with timeout=10s.
3. Validates all dimensions are covered (or UNSAT).
4. Prints a JSON result object the JS harness consumes.

Usage:
    python run-competitor-map.py <scenario.json>
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
    dim_names: list[str] = inputs["dim_names"]
    coverage: list[list[int]] = inputs["coverage"]
    costs: list[int] = inputs["costs"]
    target_size: int | None = inputs.get("target_size")
    min_coverage_per_dim: int = inputs.get("min_coverage_per_dim", 1)
    N = len(item_ids)
    M = len(dim_names)

    picked = [Bool(f"picked_{i}") for i in range(N)]

    feas = Solver()
    feas.set(unsat_core=True)

    if target_size is not None:
        feas.assert_and_track(
            Sum([If(p, 1, 0) for p in picked]) <= target_size,
            "target_size_cap",
        )

    for dim_idx in range(M):
        covering = [picked[i] for i in range(N) if dim_idx in coverage[i]]
        if covering:
            feas.assert_and_track(
                Sum([If(c, 1, 0) for c in covering]) >= min_coverage_per_dim,
                f"cover_{dim_names[dim_idx]}",
            )
        else:
            feas.assert_and_track(
                Bool(f"impossible_dim_{dim_idx}"),
                f"uncoverable_{dim_names[dim_idx]}",
            )

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

    if target_size is not None:
        opt.add(Sum([If(p, 1, 0) for p in opt_picked]) <= target_size)

    for dim_idx in range(M):
        covering = [opt_picked[i] for i in range(N) if dim_idx in coverage[i]]
        if covering:
            opt.add(Sum([If(c, 1, 0) for c in covering]) >= min_coverage_per_dim)

    opt.minimize(Sum([If(opt_picked[i], costs[i], 0) for i in range(N)]))

    t0_opt = time.perf_counter()
    result = opt.check()
    elapsed_opt = (time.perf_counter() - t0_opt) * 1000

    if result != sat:
        return {"status": "timeout", "solveTimeMs": round(elapsed_feas + elapsed_opt, 2)}

    model = opt.model()
    selected = []
    for i, iid in enumerate(item_ids):
        val = model[opt_picked[i]]
        if val is not None and bool(val):
            selected.append(iid)

    coverage_map: dict[str, list[str]] = {}
    for i, iid in enumerate(item_ids):
        if iid in selected:
            for dim_idx in coverage[i]:
                dim_name = dim_names[dim_idx]
                coverage_map.setdefault(dim_name, []).append(iid)

    single_cover_risks = [dim for dim, covers in coverage_map.items() if len(covers) == 1]
    uncovered = [dim_names[d] for d in range(M) if dim_names[d] not in coverage_map]

    return {
        "status": "optimal",
        "selectedCompetitors": selected,
        "coverageMap": coverage_map,
        "singleCoverRisks": single_cover_risks,
        "uncoveredDimensions": uncovered,
        "totalCost": sum(costs[item_ids.index(s)] for s in selected),
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
        out["selectedCompetitors"] = solver_result["selectedCompetitors"]
        out["coverageMap"] = solver_result["coverageMap"]
        out["singleCoverRisks"] = solver_result["singleCoverRisks"]
        out["uncoveredDimensions"] = solver_result["uncoveredDimensions"]
        out["totalCost"] = solver_result["totalCost"]

        expected_covered = scenario.get("expected_all_dims_covered", True)
        all_covered = len(solver_result["uncoveredDimensions"]) == 0
        out["passes"]["coverageComplete"] = (all_covered == expected_covered)

        target = scenario["inputs"].get("target_size")
        if target is not None:
            out["passes"]["withinTargetSize"] = len(solver_result["selectedCompetitors"]) <= target

    elif solver_result["status"] == "infeasible":
        out["unsatCore"] = solver_result.get("unsatCore", [])
        out["passes"]["hasUnsatCore"] = bool(out["unsatCore"])

    out["allPass"] = all(out["passes"].values())
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: run-competitor-map.py <scenario.json>"}))
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
