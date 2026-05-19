#!/usr/bin/env python
"""
Reference runner for /positioning-pass max-min-distance scenarios.

Mirrors Template 3 from skills/solver-patterns/SKILL.md exactly.
Given a scenario JSON (positioning-pass-N.json), this script:

1. Builds the Z3 Optimize model (Manhattan max-min-distance).
2. Solves with timeout=10s.
3. Validates the min_dist against expected bounds.
4. Prints a JSON result object the JS harness consumes.

Usage:
    python run-positioning-pass.py <scenario.json>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

try:
    from z3 import And, If, Optimize, Real, Sum, sat
except ImportError:
    print(json.dumps({"error": "z3-solver not installed. Run from mcp-solver venv or pip install z3-solver."}))
    sys.exit(1)


def solve_scenario(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    dim_names: list[str] = inputs["dim_names"]
    competitor_points: list[list[float]] = inputs["competitor_points"]
    envelope_lows: list[float] = inputs["envelope_lows"]
    envelope_highs: list[float] = inputs["envelope_highs"]
    dim_weights: list[float] = inputs.get("dim_weights", [1.0] * len(dim_names))
    D = len(dim_names)
    M = len(competitor_points)

    pos = [Real(f"pos_{dim_names[d]}") for d in range(D)]
    min_dist = Real("min_dist")

    opt = Optimize()
    opt.set("timeout", 10000)

    for d in range(D):
        opt.add(pos[d] >= envelope_lows[d])
        opt.add(pos[d] <= envelope_highs[d])

    for j, comp in enumerate(competitor_points):
        dist_expr = Sum([
            dim_weights[d] * If(pos[d] >= comp[d], pos[d] - comp[d], comp[d] - pos[d])
            for d in range(D)
        ])
        opt.add(min_dist <= dist_expr)

    opt.maximize(min_dist)

    t0 = time.perf_counter()
    result = opt.check()
    elapsed = (time.perf_counter() - t0) * 1000

    if result != sat:
        return {"status": "timeout", "solveTimeMs": elapsed}

    model = opt.model()

    def extract_real(var: object) -> float:
        val = model[var]
        if val is None:
            return 0.0
        try:
            return float(val.as_decimal(6).rstrip("?"))
        except Exception:
            num = val.numerator_as_long()
            den = val.denominator_as_long()
            return num / den if den else 0.0

    pos_solution = {dim_names[d]: extract_real(pos[d]) for d in range(D)}
    min_dist_val = extract_real(min_dist)

    per_competitor = []
    for j, comp in enumerate(competitor_points):
        dist = sum(
            dim_weights[d] * abs(pos_solution[dim_names[d]] - comp[d])
            for d in range(D)
        )
        separating = sorted(
            range(D),
            key=lambda d: dim_weights[d] * abs(pos_solution[dim_names[d]] - comp[d]),
            reverse=True,
        )
        per_competitor.append({
            "index": j,
            "distance": round(dist, 4),
            "topSeparatingDims": [dim_names[d] for d in separating[:2]],
        })

    per_competitor.sort(key=lambda x: x["distance"])

    return {
        "status": "optimal",
        "optimalVector": {k: round(v, 4) for k, v in pos_solution.items()},
        "minDist": round(min_dist_val, 4),
        "nearestCompetitors": per_competitor[:3],
        "solveTimeMs": round(elapsed, 2),
    }


def evaluate(scenario_path: Path) -> dict:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    solver_result = solve_scenario(scenario)

    out = {
        "scenario": scenario_path.stem,
        "solverStatus": solver_result["status"],
        "solveTimeMs": solver_result.get("solveTimeMs", 0),
        "passes": {},
    }

    if solver_result["status"] == "optimal":
        out["optimalVector"] = solver_result["optimalVector"]
        out["minDist"] = solver_result["minDist"]
        out["nearestCompetitors"] = solver_result["nearestCompetitors"]

        expected_status = scenario.get("expected_solver_status", "optimal")
        out["passes"]["statusMatch"] = (solver_result["status"] == expected_status)

        if "expected_min_dist_lower_bound" in scenario:
            lb = float(scenario["expected_min_dist_lower_bound"])
            out["passes"]["minDistLowerBound"] = solver_result["minDist"] >= lb
            out["expectedLowerBound"] = lb

        if "expected_min_dist_upper_bound" in scenario:
            ub = float(scenario["expected_min_dist_upper_bound"])
            out["passes"]["minDistUpperBound"] = solver_result["minDist"] <= ub
            out["expectedUpperBound"] = ub
    else:
        out["passes"]["statusMatch"] = (solver_result["status"] == scenario.get("expected_solver_status", "optimal"))

    out["allPass"] = all(out["passes"].values())
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: run-positioning-pass.py <scenario.json>"}))
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
