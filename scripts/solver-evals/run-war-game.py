#!/usr/bin/env python
"""
Reference runner for /war-game scenarios (Template 8 / Phase E1).

Dispatches on the scenario's top-level "predicate" field:

  - "4b" → feature-coverage moat (lead-margin over competitor responses)
  - "4a" → market-share defensibility (share floor under competitor responses)
  - "4c" → channel-economics resilience (CAC ceiling under competitor responses)

All three predicates share the same manual-skolemization Z3 pattern from
skills/solver-patterns/SKILL.md: PbEq move-selection + per-combo assertion
over the Cartesian product of competitor responses. The durability sweep
forces each candidate move in turn and checks SAT under every response combo.

Output JSON contract (consumed by validate-plugin.mjs):

  {
    "scenario": "<stem>",
    "solverStatus": "sat" | "unsat",
    "expectedStatus": "sat" | "unsat",
    "solveTimeMs": <float>,
    "passes": { ... },
    "allPass": <bool>,
    ...
  }

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
    from z3 import Bool, If, PbEq, Real, Solver, Sum, is_true, sat
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


# ============================================================
# Predicate 4b — Feature-coverage moat
# ============================================================
def solve_4b(
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


# ============================================================
# Predicate 4a — Market-share defensibility
# ============================================================
def solve_4a(
    scenario_name: str,
    my_moves: list[str],
    my_share_after_move: list[float],
    their_response_impact: list[list[float]],
    floor_threshold: float,
) -> dict:
    """Lifted verbatim from e1-4ac-smoke.py — predicate 4a share floor."""
    N_my_moves = len(my_moves)
    N_competitors = len(their_response_impact)
    N_responses = len(their_response_impact[0])

    solver = Solver()
    solver.set(unsat_core=True)

    move_vars = [Bool(f"choose_{m}") for m in my_moves]
    solver.add(PbEq([(m, 1) for m in move_vars], 1))

    my_share = Sum(
        [If(move_vars[i], my_share_after_move[i], 0.0) for i in range(N_my_moves)]
    )

    combos = list(product(range(N_responses), repeat=N_competitors))

    for combo_idx, combo in enumerate(combos):
        total_impact = sum(
            their_response_impact[k][combo[k]] for k in range(N_competitors)
        )
        label = (
            f"4a_combo_{combo_idx}_resp_{'_'.join(str(c) for c in combo)}"
            f"_impact_{total_impact:.3f}"
        )
        solver.assert_and_track(my_share - total_impact >= floor_threshold, label)

    result = solver.check()
    if result == sat:
        durable: list[str] = []
        for i, name in enumerate(my_moves):
            s2 = Solver()
            s2.set(unsat_core=True)
            s2.add(move_vars[i])
            s2.add(PbEq([(m, 1) for m in move_vars], 1))
            for combo_idx, combo in enumerate(combos):
                ti = sum(
                    their_response_impact[k][combo[k]] for k in range(N_competitors)
                )
                s2.assert_and_track(my_share - ti >= floor_threshold, f"c{combo_idx}")
            if s2.check() == sat:
                durable.append(name)
        return {"status": "sat", "all_durable": durable}

    core = solver.unsat_core()
    return {
        "status": "unsat",
        "core_size": len(core),
        "first_blockers": [str(c) for c in list(core)[:3]],
    }


# ============================================================
# Predicate 4c — Channel-economics resilience
# ============================================================
def solve_4c(
    scenario_name: str,
    my_moves: list[str],
    my_cac_after_move: list[float],
    competitor_counter_impact: list[list[list[float]]],
    target_cac: float,
) -> dict:
    """Lifted verbatim from e1-4ac-smoke.py — predicate 4c CAC ceiling."""
    N_my_moves = len(my_moves)
    N_competitors = len(competitor_counter_impact[0])
    N_responses = len(competitor_counter_impact[0][0])

    solver = Solver()
    solver.set(unsat_core=True)

    move_vars = [Bool(f"choose_{m}") for m in my_moves]
    solver.add(PbEq([(m, 1) for m in move_vars], 1))

    combos = list(product(range(N_responses), repeat=N_competitors))

    for combo_idx, combo in enumerate(combos):
        my_cac_for_combo = Sum(
            [
                If(
                    move_vars[i],
                    my_cac_after_move[i]
                    + sum(
                        competitor_counter_impact[i][k][combo[k]]
                        for k in range(N_competitors)
                    ),
                    0.0,
                )
                for i in range(N_my_moves)
            ]
        )
        worst_lift = max(
            sum(
                competitor_counter_impact[i][k][combo[k]]
                for k in range(N_competitors)
            )
            for i in range(N_my_moves)
        )
        label = (
            f"4c_combo_{combo_idx}_resp_{'_'.join(str(c) for c in combo)}"
            f"_worst_lift_{worst_lift:.2f}"
        )
        solver.assert_and_track(my_cac_for_combo <= target_cac, label)

    result = solver.check()
    if result == sat:
        durable: list[str] = []
        for i, name in enumerate(my_moves):
            s2 = Solver()
            s2.set(unsat_core=True)
            s2.add(move_vars[i])
            s2.add(PbEq([(m, 1) for m in move_vars], 1))
            for combo_idx, combo in enumerate(combos):
                cac_combo = Sum(
                    [
                        If(
                            move_vars[j],
                            my_cac_after_move[j]
                            + sum(
                                competitor_counter_impact[j][k][combo[k]]
                                for k in range(N_competitors)
                            ),
                            0.0,
                        )
                        for j in range(N_my_moves)
                    ]
                )
                s2.assert_and_track(cac_combo <= target_cac, f"c{combo_idx}")
            if s2.check() == sat:
                durable.append(name)
        return {"status": "sat", "all_durable": durable}

    core = solver.unsat_core()
    return {
        "status": "unsat",
        "core_size": len(core),
        "first_blockers": [str(c) for c in list(core)[:3]],
    }


# ============================================================
# Dispatch
# ============================================================
def solve_scenario(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    predicate = scenario.get("predicate", "4b")
    t0 = time.perf_counter()
    if predicate == "4b":
        result = solve_4b(
            scenario_name=inputs.get("scenario_name", "war-game"),
            my_moves=inputs["my_moves"],
            my_baseline=inputs["my_baseline"],
            my_move_deltas=inputs["my_move_deltas"],
            their_baseline=inputs["their_baseline"],
            their_response_deltas=inputs["their_response_deltas"],
            dim_weights=inputs["dim_weights"],
            lead_margin=int(inputs["lead_margin"]),
        )
    elif predicate == "4a":
        result = solve_4a(
            scenario_name=inputs.get("scenario_name", "war-game"),
            my_moves=inputs["my_moves"],
            my_share_after_move=inputs["my_share_after_move"],
            their_response_impact=inputs["their_response_impact"],
            floor_threshold=float(inputs["floor_threshold"]),
        )
    elif predicate == "4c":
        result = solve_4c(
            scenario_name=inputs.get("scenario_name", "war-game"),
            my_moves=inputs["my_moves"],
            my_cac_after_move=inputs["my_cac_after_move"],
            competitor_counter_impact=inputs["competitor_counter_impact"],
            target_cac=float(inputs["target_cac"]),
        )
    else:
        raise ValueError(f"Unknown predicate: {predicate!r}")
    elapsed = (time.perf_counter() - t0) * 1000
    result["solveTimeMs"] = round(elapsed, 2)
    result["predicate"] = predicate
    return result


def evaluate(scenario_path: Path) -> dict:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    expected = scenario.get("expected", {})
    expected_status: str = expected.get("status", "sat")
    expected_durable: list[str] = expected.get("all_durable", [])
    expected_kill_count: int = int(expected.get("kill_count_expected", 0))

    solver_result = solve_scenario(scenario)
    predicate = solver_result.get("predicate", "4b")

    out: dict = {
        "scenario": scenario_path.stem,
        "predicate": predicate,
        "solverStatus": solver_result["status"],
        "expectedStatus": expected_status,
        "solveTimeMs": solver_result.get("solveTimeMs", 0),
        "passes": {},
    }

    out["passes"]["statusMatch"] = solver_result["status"] == expected_status

    if solver_result["status"] == "sat":
        actual_durable = solver_result.get("all_durable", [])
        out["allDurable"] = actual_durable
        out["expectedDurable"] = expected_durable
        out["passes"]["durableMatch"] = sorted(actual_durable) == sorted(expected_durable)

        # killCount is only meaningful for predicate 4b (which tracks per-move kills).
        # 4a/4c durability sweeps don't build a kill map; skip that pass.
        if predicate == "4b":
            actual_kill = solver_result.get("kill", {})
            out["killCount"] = len(actual_kill)
            out["expectedKillCount"] = expected_kill_count
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
