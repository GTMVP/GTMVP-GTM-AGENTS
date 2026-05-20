#!/usr/bin/env python
"""
Reference runner for /content-calendar assignment-with-diversity scenarios.

Mirrors Template 7 from skills/solver-patterns/SKILL.md exactly.
Given a scenario JSON (content-calendar-N.json), this script:

1. Builds the MiniZinc model with scenario-specific data via Model.add_string.
2. Solves with Gecode and a 30s timeout (matches the MCP server's hard cap).
3. Validates the result against expected status (satisfied|unsatisfiable) +
   constraint compliance (cadence, fit, diversity, pillar coverage).
4. Prints a JSON result object the JS harness consumes.

UNSAT scenarios are treated as PASS when expected_solver_status == "unsatisfiable",
mirroring channel-score-3 / swot-priorities-3.

Usage:
    python run-content-calendar.py <scenario.json>

Exit code 0 = passing. Exit code 1 = failing or solver error.
"""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

try:
    from minizinc import Instance, Model, Solver
    from minizinc.result import Status
except ImportError:
    print(
        json.dumps(
            {
                "error": "minizinc package not installed. Run from mcp-solver venv "
                "(C:\\Users\\User\\Projects\\mcp-solver\\.venv) or pip install minizinc."
            }
        )
    )
    sys.exit(1)


# Statuses that indicate a feasible solution was found.
_FEASIBLE_STATUSES = {Status.SATISFIED, Status.OPTIMAL_SOLUTION, Status.ALL_SOLUTIONS}


def _flatten_pillar_fit(pillar_fit: list[list[int]]) -> list[int]:
    """Flatten K+1 row x P col matrix into MiniZinc-friendly row-major list."""
    flat: list[int] = []
    for row in pillar_fit:
        flat.extend(row)
    return flat


def _build_model_string(inputs: dict) -> str:
    """Render Template 7 MiniZinc source with scenario-specific data."""
    D = int(inputs["D"])
    P = int(inputs["P"])
    K = int(inputs["K"])

    platform_names = inputs["platform_names"]
    pillar_names = inputs["pillar_names"]
    cadence = inputs["cadence"]
    pillar_fit = inputs["pillar_fit"]
    pillar_min = inputs["pillar_min"]
    pillar_max = inputs["pillar_max"]
    min_gap = inputs["min_gap"]
    pillar_weight = inputs["pillar_weight"]

    if len(platform_names) != P:
        raise ValueError(f"platform_names length {len(platform_names)} != P={P}")
    if len(pillar_names) != K:
        raise ValueError(f"pillar_names length {len(pillar_names)} != K={K}")
    if len(cadence) != P:
        raise ValueError(f"cadence length {len(cadence)} != P={P}")
    if len(pillar_fit) != K + 1:
        raise ValueError(
            f"pillar_fit rows {len(pillar_fit)} != K+1={K + 1} (sentinel row 0 required)"
        )
    for row_idx, row in enumerate(pillar_fit):
        if len(row) != P:
            raise ValueError(
                f"pillar_fit row {row_idx} length {len(row)} != P={P}"
            )
    if pillar_fit[0] != [1] * P:
        raise ValueError("pillar_fit row 0 must be all 1s (no-post sentinel)")

    def _arr(name: str, vals: list[int]) -> str:
        return f"array[1..{len(vals)}] of int: {name} = {list(vals)};"

    def _str_arr(name: str, vals: list[str], length: int) -> str:
        quoted = ", ".join(f'"{v}"' for v in vals)
        return f"array[1..{length}] of string: {name} = [{quoted}];"

    flat_fit = _flatten_pillar_fit(pillar_fit)

    model = []
    model.append('include "globals.mzn";')
    model.append(f"int: D = {D};")
    model.append(f"int: P = {P};")
    model.append(f"int: K = {K};")
    model.append(_str_arr("platform_names", platform_names, P))
    model.append(_str_arr("pillar_names", pillar_names, K))
    model.append(_arr("cadence", cadence))
    model.append(
        "array[0..K, 1..P] of 0..1: pillar_fit = array2d(0..K, 1..P, "
        + str(flat_fit)
        + ");"
    )
    model.append(_arr("pillar_min", pillar_min))
    model.append(_arr("pillar_max", pillar_max))
    model.append(_arr("min_gap", min_gap))
    model.append(_arr("pillar_weight", pillar_weight))
    model.append("array[1..D, 1..P] of var 0..K: x;")
    model.append(
        "constraint forall(p in 1..P)("
        "sum(d in 1..D)(bool2int(x[d,p] != 0)) = cadence[p]);"
    )
    model.append(
        "constraint forall(d in 1..D, p in 1..P)(pillar_fit[x[d,p], p] = 1);"
    )
    model.append(
        "constraint forall(p in 1..P, d1 in 1..D-1, "
        "d2 in d1+1..min(D, d1+min_gap[p]-1))("
        "x[d1,p] = 0 \\/ x[d2,p] = 0 \\/ x[d1,p] != x[d2,p]);"
    )
    model.append(
        "constraint forall(k in 1..K)("
        "pillar_min[k] <= sum(d in 1..D, p in 1..P)(bool2int(x[d,p] = k)));"
    )
    model.append(
        "constraint forall(k in 1..K)("
        "sum(d in 1..D, p in 1..P)(bool2int(x[d,p] = k)) <= pillar_max[k]);"
    )
    model.append(
        "solve maximize sum(d in 1..D, p in 1..P, k in 1..K)("
        "bool2int(x[d,p] = k) * pillar_weight[k]);"
    )
    return "\n".join(model)


def solve_scenario(scenario: dict) -> dict:
    inputs = scenario["inputs"]

    model = Model()
    model.add_string(_build_model_string(inputs))
    solver = Solver.lookup("gecode")
    instance = Instance(solver, model)

    t0 = time.perf_counter()
    result = instance.solve(timeout=datetime.timedelta(seconds=30))
    elapsed = (time.perf_counter() - t0) * 1000

    status_name = result.status.name if result.status else "UNKNOWN"

    if result.status == Status.UNSATISFIABLE:
        return {
            "status": "unsatisfiable",
            "rawStatus": status_name,
            "solveTimeMs": round(elapsed, 2),
        }

    if result.status not in _FEASIBLE_STATUSES:
        return {
            "status": "timeout",
            "rawStatus": status_name,
            "solveTimeMs": round(elapsed, 2),
        }

    x_matrix = result["x"]
    objective = result.objective

    return {
        "status": "satisfied",
        "rawStatus": status_name,
        "x": x_matrix,
        "objective": objective,
        "optimal": result.status == Status.OPTIMAL_SOLUTION,
        "solveTimeMs": round(elapsed, 2),
    }


def _validate_constraints(
    inputs: dict, x_matrix: list[list[int]]
) -> dict[str, bool]:
    """Re-check all Template 7 constraints against the returned schedule."""
    D = int(inputs["D"])
    P = int(inputs["P"])
    K = int(inputs["K"])
    cadence = inputs["cadence"]
    pillar_fit = inputs["pillar_fit"]
    pillar_min = inputs["pillar_min"]
    pillar_max = inputs["pillar_max"]
    min_gap = inputs["min_gap"]

    passes: dict[str, bool] = {}

    # Cadence: column sum of non-zero entries equals cadence[p]
    cadence_ok = True
    for p in range(P):
        count = sum(1 for d in range(D) if x_matrix[d][p] != 0)
        if count != cadence[p]:
            cadence_ok = False
            break
    passes["cadenceMatch"] = cadence_ok

    # Fit: pillar_fit[k, p] == 1 for every assigned slot
    fit_ok = True
    for d in range(D):
        for p in range(P):
            k = x_matrix[d][p]
            if pillar_fit[k][p] != 1:
                fit_ok = False
                break
    passes["fitRespected"] = fit_ok

    # Diversity: no same non-zero pillar within (min_gap[p]-1) days on same platform
    diversity_ok = True
    for p in range(P):
        gap = min_gap[p]
        for d1 in range(D):
            if x_matrix[d1][p] == 0:
                continue
            for d2 in range(d1 + 1, min(D, d1 + gap)):
                if x_matrix[d2][p] != 0 and x_matrix[d1][p] == x_matrix[d2][p]:
                    diversity_ok = False
                    break
            if not diversity_ok:
                break
        if not diversity_ok:
            break
    passes["diversityRespected"] = diversity_ok

    # Pillar coverage bounds
    coverage_ok = True
    for k in range(1, K + 1):
        count = sum(1 for d in range(D) for p in range(P) if x_matrix[d][p] == k)
        if count < pillar_min[k - 1] or count > pillar_max[k - 1]:
            coverage_ok = False
            break
    passes["pillarCoverage"] = coverage_ok

    return passes


def evaluate(scenario_path: Path) -> dict:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    expected_status = scenario.get("expected_solver_status", "satisfied")

    solver_result = solve_scenario(scenario)

    out: dict = {
        "scenario": scenario_path.stem,
        "solverStatus": solver_result["status"],
        "expectedStatus": expected_status,
        "solveTimeMs": solver_result.get("solveTimeMs", 0),
        "passes": {},
    }

    out["passes"]["statusMatch"] = solver_result["status"] == expected_status

    if solver_result["status"] == "satisfied":
        out["solverObjective"] = solver_result["objective"]
        out["optimal"] = solver_result["optimal"]

        if "expected_objective" in scenario:
            expected_obj = float(scenario["expected_objective"])
            actual_obj = float(solver_result["objective"])
            # Tight tolerance — the model is deterministic for these scenarios.
            out["passes"]["objectiveMatch"] = abs(actual_obj - expected_obj) <= 0.5
            out["expectedObjective"] = expected_obj

        constraint_passes = _validate_constraints(scenario["inputs"], solver_result["x"])
        out["passes"].update(constraint_passes)

    elif solver_result["status"] == "unsatisfiable":
        # Negative test: UNSAT is the expected outcome. statusMatch alone is the gate.
        out["unsat"] = True

    out["allPass"] = all(out["passes"].values())
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: run-content-calendar.py <scenario.json>"}))
        sys.exit(1)

    scenario_path = Path(sys.argv[1])
    if not scenario_path.exists():
        print(json.dumps({"error": f"Scenario file not found: {scenario_path}"}))
        sys.exit(1)

    try:
        result = evaluate(scenario_path)
    except Exception as e:
        print(
            json.dumps(
                {
                    "error": f"{type(e).__name__}: {e}",
                    "scenario": scenario_path.stem,
                }
            )
        )
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["allPass"] else 1)


if __name__ == "__main__":
    main()
