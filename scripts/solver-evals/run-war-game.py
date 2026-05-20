#!/usr/bin/env python
"""
Reference runner for /war-game feature-coverage-moat scenarios (Template 8 / Phase E1).

Mirrors the manual-skolemization Z3 pattern from skills/solver-patterns/SKILL.md.
Given a scenario JSON (war-game-N.json), this script:

1. Builds the Z3 Boolean model with PbEq move-selection and per-combo lead-margin
   assertions (one assertion per Cartesian product of competitor responses).
2. Performs the durability sweep: for each candidate move, force-pick it and check
   whether the inequality holds across ALL competitor response combos. SAT = durable;
   UNSAT = killed (and the unsat core surfaces the breaking combo).
3. Validates the result against expected status (sat|unsat), the expected list of
   durable moves, and the expected kill count.
4. Prints a JSON result object the JS harness consumes.

UNSAT scenarios are treated as PASS when expected.status == "unsat", mirroring
content-calendar-3 / channel-score-3 / swot-priorities-3.

Usage:
    python run-war-game.py <scenario.json>

Exit code 0 = passing. Exit code 1 = failing or solver error.
"""
from __future__ import annotations

import json
import sys
import time
from itertools import product
from pathlib import Path

try:
    from z3 import Bool, If, PbEq, Solver, Sum, is_true, sat
except ImportError:
    print(
        json.dumps(
            {
                "error": "z3-solver not installed. Run from mcp-solver venv "
                "(C:\\Users\\User\\Projects\\mcp-solver\\.venv) or pip install z3-solver."
            }
        )
    )
    sys.exit(1)


def build_and_solve(
    scenario_name: str,
    my_moves: list[str],
    my_baseline: list[int],
    my_move_deltas: list[list[int]],
    their_baseline: list[list[int]],
    their_response_deltas: list[list[list[int]]],
    dim_weights: list[int],
    lead_margin: int,
) -> dict:
    """Lifted verbatim from e1-smoke.py — Template 8 feature-coverage moat."""
    N_my_moves = len(my_moves)
    N_dims = len(dim_weights)
    N_competitors = len(their_baseline)
    N_responses = len(their_response_deltas[0])

    solver = Solver()
    solver.set(unsat_core=True)

    move_vars = [Bool(f"choose_{m}") for m in my_moves]
    solver.add(PbEq([(m, 1) for m in move_vars], 1))

    score = 0
    for d in range(N_dims):
        if my_baseline[d] == 1:
            score = score + dim_weights[d]
        else:
            covered = Sum(
                [If(move_vars[m], my_move_deltas[m][d], 0) for m in range(N_my_moves)]
            )
            score = score + dim_weights[d] * covered
    my_score = score

    combos = list(product(range(N_responses), repeat=N_competitors))

    for combo_idx, combo in enumerate(combos):
        their_scores = []
        for k in range(N_competitors):
            cov = [
                1
                if (
                    their_baseline[k][d] == 1
                    or their_response_deltas[k][combo[k]][d] == 1
                )
                else 0
                for d in range(N_dims)
            ]
            their_scores.append(
                sum(dim_weights[d] * cov[d] for d in range(N_dims))
            )
        their_max = max(their_scores)

        label = (
            f"combo_{combo_idx}_resp_{'_'.join(str(c) for c in combo)}"
            f"_their_max_{their_max}"
        )
        solver.assert_and_track(my_score >= their_max + lead_margin, label)

    result = solver.check()
    if result == sat:
        durable: list[str] = []
        kill: dict[str, str] = {}
        for i, name in enumerate(my_moves):
            s2 = Solver()
            s2.set(unsat_core=True)
            s2.add(move_vars[i])
            s2.add(PbEq([(m, 1) for m in move_vars], 1))
            for combo_idx, combo in enumerate(combos):
                their_max = max(
                    sum(
                        dim_weights[d]
                        * (
                            1
                            if (
                                their_baseline[k][d] == 1
                                or their_response_deltas[k][combo[k]][d] == 1
                            )
                            else 0
                        )
                        for d in range(N_dims)
                    )
                    for k in range(N_competitors)
                )
                lbl = f"c{combo_idx}"
                s2.assert_and_track(my_score >= their_max + lead_margin, lbl)
            if s2.check() == sat:
                durable.append(name)
            else:
                core = list(s2.unsat_core())
                kill[name] = str(core[0]) if core else "no core"
        return {"status": "sat", "all_durable": durable, "kill": kill}

    core = solver.unsat_core()
    return {
        "status": "unsat",
        "core_size": len(core),
        "first_blockers": [str(c) for c in list(core)[:3]],
    }


def solve_scenario(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    t0 = time.perf_counter()
    result = build_and_solve(
        scenario_name=inputs.get("scenario_name", "war-game"),
        my_moves=inputs["my_moves"],
        my_baseline=inputs["my_baseline"],
        my_move_deltas=inputs["my_move_deltas"],
        their_baseline=inputs["their_baseline"],
        their_response_deltas=inputs["their_response_deltas"],
        dim_weights=inputs["dim_weights"],
        lead_margin=int(inputs["lead_margin"]),
    )
    elapsed = (time.perf_counter() - t0) * 1000
    result["solveTimeMs"] = round(elapsed, 2)
    return result


def evaluate(scenario_path: Path) -> dict:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    expected = scenario.get("expected", {})
    expected_status: str = expected.get("status", "sat")
    expected_durable: list[str] = expected.get("all_durable", [])
    expected_kill_count: int = int(expected.get("kill_count_expected", 0))

    solver_result = solve_scenario(scenario)

    out: dict = {
        "scenario": scenario_path.stem,
        "solverStatus": solver_result["status"],
        "expectedStatus": expected_status,
        "solveTimeMs": solver_result.get("solveTimeMs", 0),
        "passes": {},
    }

    out["passes"]["statusMatch"] = solver_result["status"] == expected_status

    if solver_result["status"] == "sat":
        actual_durable = solver_result.get("all_durable", [])
        actual_kill = solver_result.get("kill", {})
        out["allDurable"] = actual_durable
        out["expectedDurable"] = expected_durable
        out["killCount"] = len(actual_kill)
        out["expectedKillCount"] = expected_kill_count

        out["passes"]["durableMatch"] = sorted(actual_durable) == sorted(expected_durable)
        out["passes"]["killCountMatch"] = len(actual_kill) == expected_kill_count
    else:
        out["unsat"] = True
        out["coreSize"] = solver_result.get("core_size", 0)
        out["firstBlockers"] = solver_result.get("first_blockers", [])

    out["allPass"] = all(out["passes"].values())
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: run-war-game.py <scenario.json>"}))
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
