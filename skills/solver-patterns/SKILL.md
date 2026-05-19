---
name: solver-patterns
description: Reusable constraint-solver templates for GTMVP agents that produce provably-optimal recommendations. Six templates — five Z3 (linear-allocation, knapsack, max-min-distance, set-cover, scheduling-with-deps) for solver-z3, plus one PySAT MaxSAT template (maxsat-claim-synthesis) for solver-maxsat used in /gtm-audit D1. Mandates labeling, fresh-model, timeout, UNSAT-explanation, and piecewise-linear conventions.
---

# Solver Patterns

This skill is the contract every solver-using agent and command consults before building a Z3 model. The goal is to keep model construction **template-driven, not prose-driven**, so encodings are reproducible across runs and across agents.

The `solver-z3` MCP server takes **Python z3 code** as items (`add_item`, `replace_item`, `delete_item`), not raw SMT-LIB. Every model ends with `export_solution(solver=..., variables=...)`. The templates below are copy-paste skeletons — fill the brand-specific slots, never re-author the structure.

## Required imports (item 0 of every model)

```python
from z3 import *
from mcp_solver.z3 import export_solution
```

Always put this as `add_item(0, ...)`. Every other item assumes these are in scope.

## Universal conventions (these apply to every template)

1. **Fresh model.** Begin every solver invocation with `clear_model` so prior session state doesn't contaminate. End with `clear_model` unless the same agent is mid-conversation re-solving incrementally.
2. **Labeled assertions for UNSAT explainability.** Use `solver.assert_and_track(constraint_expr, "label_string")` instead of `solver.add(...)` whenever the constraint might cause infeasibility. Labels become the user-facing reason a recommendation can't be made. Use `solver.set(unsat_core=True)` once before any `assert_and_track` call. Reserve plain `solver.add(...)` for constraints that are tautologically satisfiable (domain bounds, sum identities).
3. **Timeout = 10 seconds default.** Call `mcp__solver-z3__solve_model` with `timeout=10000`. Treat timeout as "constraints too tight" and surface the active constraints as relaxation candidates.
4. **Piecewise-linear approximation for sqrt/log objectives.** Z3 has no native `sqrt` or `log`. For diminishing-returns objectives, use 5 breakpoints with logarithmic spacing — pattern below.
5. **One agent at a time.** The MCP solver server holds shared session state. NEVER let two parallel `Task` sub-agents simultaneously invoke `solver-z3`. Either serialize solver-using stages, or restrict solver use to the final synthesis stage.
6. **Always export.** Even on UNSAT, call `export_solution(satisfiable=False, variables=variables_dict)`. Without this call, the solver result is invisible to the command flow.

## Template 1: Linear allocation

**Use cases.** A1 channel-mix optimization. Any "split budget B across N options each with a score and a min-spend threshold" problem.

**Slots to fill.**
- `N` — number of options (e.g. 28 channels)
- `option_ids` — stable string IDs from a taxonomy (e.g. `agent_seo_onpage_001`)
- `scores[i]` — per-option quality score (1–10 typical)
- `min_viable[i]` — minimum spend below which the option is considered inactive
- `max_useful[i]` — upper bound on useful spend per option
- `total_budget` — founder-supplied cap
- `max_concentration_pct` — single-option cap as % of total
- `dependencies` — list of `(child_idx, parent_idx)` pairs; child can be active only if parent is
- `compounding_indices` — option indices marked as compounding
- `fast_feedback_indices` — option indices marked as fast-feedback
- `team_size` — operators available; each runs ≤ 3 active options

**Template code (split across `add_item` calls — typically 6–8 items).**

```python
# Item 1: brand data (slots filled here from the agent flow)
option_ids = [...]          # e.g. ["agent_seo_onpage_001", ...]
scores = [...]              # 1–10 per option
min_viable = [...]          # dollar floor per option
max_useful = [...]          # dollar ceiling per option
total_budget = 50000.0
max_concentration_pct = 0.40
dependencies = [(7, 0), (12, 3)]       # (child_idx, parent_idx)
compounding_indices = [0, 3, 9, 15]
fast_feedback_indices = [11, 19, 22]
team_size = 1
N = len(option_ids)

# Item 2: variables
spend = [Real(f"spend_{i}") for i in range(N)]
active = [Bool(f"active_{i}") for i in range(N)]

opt = Optimize()
opt.set("timeout", 10000)

# Item 3: domain + activation linkage (untracked — tautologically OK)
for i in range(N):
    opt.add(spend[i] >= 0)
    opt.add(spend[i] <= max_useful[i])
    opt.add(active[i] == (spend[i] >= min_viable[i]))

# Item 4: labeled hard constraints — these are the ones whose UNSAT reasons surface to the user
# (Optimize() doesn't expose unsat_core directly; use a parallel Solver() for the feasibility precheck.
#  Here we use plain add() because Optimize will return inf-objective on infeasibility — the
#  feasibility precheck Solver below catches UNSAT and labels it.)
opt.add(Sum(spend) <= total_budget)
for i in range(N):
    opt.add(spend[i] <= max_concentration_pct * total_budget)
for child, parent in dependencies:
    opt.add(Implies(active[child], active[parent]))
opt.add(Sum([If(a, 1, 0) for a in active]) <= team_size * 3)
opt.add(Sum([If(active[i], 1, 0) for i in compounding_indices]) >= 1)
opt.add(Sum([If(active[i], 1, 0) for i in fast_feedback_indices]) >= 1)

# Item 5: piecewise-linear sqrt of spend (diminishing returns)
# 5 breakpoints log-spaced from min_viable to max_useful per channel.
# Encoded as Real auxiliary var per channel with piecewise linear constraints.
def pwl_sqrt(spend_var, low, high):
    # 5 breakpoints; aux is a Real that equals sqrt(spend_var) at each breakpoint
    # and linearly interpolates between them.
    bps = [low * (high / low) ** (k / 4) for k in range(5)] if low > 0 else \
          [k * high / 4 for k in range(5)]
    sqrts = [b ** 0.5 for b in bps]
    aux = Real(f"sqrt_{spend_var}")
    # Below first breakpoint: clamp to sqrts[0]
    opt.add(Implies(spend_var <= bps[0], aux == sqrts[0]))
    # Between breakpoints: linear
    for k in range(4):
        slope = (sqrts[k+1] - sqrts[k]) / (bps[k+1] - bps[k]) if bps[k+1] != bps[k] else 0
        opt.add(Implies(And(spend_var > bps[k], spend_var <= bps[k+1]),
                        aux == sqrts[k] + slope * (spend_var - bps[k])))
    # Above last breakpoint: clamp to sqrts[-1] (no further useful spend)
    opt.add(Implies(spend_var > bps[-1], aux == sqrts[-1]))
    return aux

returns = [pwl_sqrt(spend[i], max(min_viable[i], 1.0), max_useful[i]) for i in range(N)]

# Item 6: objective + solve
opt.maximize(Sum([scores[i] * returns[i] for i in range(N)]))

variables = {}
for i, oid in enumerate(option_ids):
    variables[f"spend_{oid}"] = spend[i]
    variables[f"active_{oid}"] = active[i]

# Item 7: feasibility precheck with labeled constraints (separate Solver for unsat-core support)
feas = Solver()
feas.set(unsat_core=True)
# Re-add only the hard structural constraints (skip objective and pwl)
feas.add(spend[i] >= 0 for i in range(N))  # domain
feas.assert_and_track(Sum(spend) <= total_budget, "budget_cap")
for child, parent in dependencies:
    feas.assert_and_track(Implies(active[child], active[parent]),
                           f"dep_{option_ids[child]}_needs_{option_ids[parent]}")
feas.assert_and_track(Sum([If(a, 1, 0) for a in active]) <= team_size * 3, "team_capacity")
feas.assert_and_track(Sum([If(active[i], 1, 0) for i in compounding_indices]) >= 1, "min_compounding")
feas.assert_and_track(Sum([If(active[i], 1, 0) for i in fast_feedback_indices]) >= 1, "min_fast_feedback")

if feas.check() == unsat:
    core = feas.unsat_core()
    print(f"Infeasible: {[str(c) for c in core]}")
    export_solution(satisfiable=False, variables=variables)
else:
    result = opt.check()
    if result == sat:
        export_solution(solver=opt, variables=variables, objective=opt.objectives()[0])
    else:
        export_solution(satisfiable=False, variables=variables)
```

**Output parsing.** Each `spend_<option_id>` in the solution is a Real-valued dollar amount; threshold against `min_viable[i]` to determine `active_<option_id>` truth (or read it directly). Total allocation = `Σ spend[i]` (≤ budget). Sensitivity is computed by re-solving with `total_budget += delta` and diffing the active set.

**Common pitfalls.**
- Forgetting `opt.set("timeout", 10000)` — hard problems can hang.
- Using `solver.add(...)` instead of `assert_and_track` on constraints that might be infeasible — UNSAT then returns opaque "unsat" with no labels.
- Putting the pwl logic inline instead of in the `pwl_sqrt` function — breakpoint policy then drifts across runs.

---

## Template 2: Knapsack (pick K of N maximizing value under capacity)

**Use cases.** B1 SWOT priorities under founder hours/week. Any "pick a subset maximizing total weighted score subject to a single capacity constraint + categorical coverage requirements."

**Slots to fill.**
- `N` — number of items
- `item_ids` — stable identifiers
- `values[i]` — score per item (any non-negative scalar)
- `costs[i]` — capacity cost per item (hours, dollars, slots)
- `total_capacity` — founder-supplied budget
- `categories[i]` — list of category tags per item
- `must_cover_categories` — categories that need at least one selected item
- `max_concurrent` — optional cap on total items (k_max)

**Template code.**

```python
# Item 1: data
item_ids = [...]            # e.g. SWOT priority IDs
values = [...]              # weighted SWOT-coverage scores
costs = [...]               # hours/week per priority
total_capacity = 20.0       # founder hours/week
categories = [[...], ...]   # per item, list of tag strings
must_cover_categories = ["critical_threat_1", "critical_threat_2"]
max_concurrent = 3
N = len(item_ids)

# Item 2: variables + solver
picked = [Bool(f"picked_{i}") for i in range(N)]
opt = Optimize()
opt.set("timeout", 10000)

# Item 3: capacity + count
opt.add(Sum([If(picked[i], costs[i], 0) for i in range(N)]) <= total_capacity)
if max_concurrent is not None:
    opt.add(Sum([If(p, 1, 0) for p in picked]) <= max_concurrent)

# Item 4: category coverage (separate feasibility-checked block in a real run)
for cat in must_cover_categories:
    covering = [picked[i] for i in range(N) if cat in categories[i]]
    if covering:
        opt.add(Or(covering))   # at least one selected item carries this tag

# Item 5: objective + export
opt.maximize(Sum([If(picked[i], values[i], 0) for i in range(N)]))

variables = {f"picked_{iid}": picked[i] for i, iid in enumerate(item_ids)}

if opt.check() == sat:
    export_solution(solver=opt, variables=variables, objective=opt.objectives()[0])
else:
    export_solution(satisfiable=False, variables=variables)
```

**Output parsing.** Each `picked_<item_id>` is Bool — true means selected. Total cost = `Σ costs[i] for picked[i]`. Total value = objective.

---

## Template 3: Max-min distance (geometric whitespace)

**Use cases.** A2 positioning whitespace verification. Find a point in N-dimensional space that maximizes its minimum distance to any of M competitor points, subject to per-dimension envelope constraints.

**Slots to fill.**
- `D` — number of positioning dimensions (typically 4–6)
- `dim_names` — labels (e.g. `["price_tier", "audience_sophistication", "feature_depth", "channel_fit", "defensibility_commitment"]`)
- `competitor_points` — list of D-tuples (one per competitor)
- `envelope_lows[d]`, `envelope_highs[d]` — founder defensibility envelope per dimension
- Optional: `dim_weights[d]` — relative importance per dimension (default 1.0)

**Template code.**

```python
# Item 1: data
dim_names = [...]                # length D
competitor_points = [...]        # list of D-tuples
envelope_lows = [...]            # per dim
envelope_highs = [...]           # per dim
dim_weights = [1.0] * len(dim_names)
D = len(dim_names)
M = len(competitor_points)

# Item 2: variables — the proposed positioning vector
pos = [Real(f"pos_{dim_names[d]}") for d in range(D)]
min_dist = Real("min_dist")     # auxiliary: minimum distance to any competitor

opt = Optimize()
opt.set("timeout", 10000)

# Item 3: envelope constraints
for d in range(D):
    opt.add(pos[d] >= envelope_lows[d])
    opt.add(pos[d] <= envelope_highs[d])

# Item 4: distance lower bound per competitor (Manhattan distance — sum of |pos[d] - comp[d]|)
# Z3 handles abs via If; sum is exact.
def manhattan(a_vec, b_vec):
    return Sum([dim_weights[d] * If(a_vec[d] >= b_vec[d],
                                    a_vec[d] - b_vec[d],
                                    b_vec[d] - a_vec[d])
                for d in range(D)])

for j, comp in enumerate(competitor_points):
    opt.add(min_dist <= manhattan(pos, comp))

# Item 5: objective + export
opt.maximize(min_dist)

variables = {f"pos_{dim_names[d]}": pos[d] for d in range(D)}
variables["min_dist"] = min_dist

if opt.check() == sat:
    export_solution(solver=opt, variables=variables, objective=opt.objectives()[0])
else:
    export_solution(satisfiable=False, variables=variables)
```

**Output parsing.** Position vector = `pos_<dim>` values. `min_dist` is the guaranteed separation from any competitor. Per-competitor distances are computed post-hoc by evaluating `manhattan(pos_solution, comp)` in Python after extracting the model.

**Why Manhattan, not Euclidean.** Z3 doesn't natively handle non-linear arithmetic well for Real. Manhattan stays linear, solves fast, and is interpretable ("you differ from competitor X by 1.5 on price and 0.8 on audience"). For Euclidean, use Z3's `nlsat` tactic but expect 10x slower solves.

---

## Template 4: Set cover (min-cost variant)

**Use cases.** A3 competitor-map cluster cover (pick K representatives covering all feature dimensions). C1 Porter's response packaging (cheapest set of strategic responses addressing all forces above threshold).

**Slots to fill.**
- `N` — number of candidate items (competitors, responses)
- `M` — number of dimensions/forces to cover
- `coverage[i]` — list of dimension indices that item i covers
- `costs[i]` — cost of selecting item i (uniform = 1 if just counting items)
- `target_size` — if "pick exactly K", set this; else None
- `min_coverage_per_dim` — usually 1 (each dim must be covered by ≥ 1 selected item)

**Template code.**

```python
# Item 1: data
item_ids = [...]            # competitor or response IDs
dim_names = [...]
coverage = [[...], ...]     # per item: list of dim indices it covers
costs = [1] * len(item_ids) # uniform cost = picking K of N
target_size = 5             # set to None for unconstrained pick
min_coverage_per_dim = 1
N = len(item_ids)
M = len(dim_names)

# Item 2: variables + solver
selected = [Bool(f"sel_{i}") for i in range(N)]
opt = Optimize()
opt.set("timeout", 10000)

# Item 3: coverage constraints — each dim must be hit ≥ min_coverage_per_dim times
for d in range(M):
    covers_d = [selected[i] for i in range(N) if d in coverage[i]]
    if covers_d:
        opt.add(Sum([If(c, 1, 0) for c in covers_d]) >= min_coverage_per_dim)
    # else: dim has no coverers — infeasible by data; surface as warning before solving

# Item 4: optional size target
if target_size is not None:
    opt.add(Sum([If(s, 1, 0) for s in selected]) == target_size)

# Item 5: minimize cost
opt.minimize(Sum([If(selected[i], costs[i], 0) for i in range(N)]))

variables = {f"sel_{iid}": selected[i] for i, iid in enumerate(item_ids)}

if opt.check() == sat:
    export_solution(solver=opt, variables=variables, objective=opt.objectives()[0])
else:
    export_solution(satisfiable=False, variables=variables)
```

**Output parsing.** Selected items = those whose `sel_<id>` is true. Coverage map = post-hoc compute "which selected items cover which dim" by intersecting `coverage[i]` with selected indices.

---

## Template 5: Scheduling with dependencies

**Use cases.** C2 TAM/SAM/SOM horizon planning with prerequisite DAG.

**Slots to fill.**
- `N` — number of initiatives
- `init_ids` — stable identifiers
- `values[i]` — strategic value of initiative i (revenue, positioning impact)
- `effort[i]` — capacity cost (FTE-months, hours, dollars)
- `horizons` — list of horizon names (e.g. `["0_3mo", "3_12mo", "12mo_plus"]`)
- `horizon_capacity[h]` — capacity available in each horizon
- `dependencies` — list of `(downstream_idx, upstream_idx)` pairs; downstream's horizon must be ≥ upstream's

**Template code.**

```python
# Item 1: data
init_ids = [...]
values = [...]
effort = [...]
horizons = ["0_3mo", "3_12mo", "12mo_plus"]
horizon_capacity = [40, 120, 360]   # FTE-months per horizon
dependencies = [(3, 0), (7, 3)]     # (downstream, upstream)
N = len(init_ids)
H = len(horizons)

# Item 2: variables — horizon assignment per initiative (0..H-1, plus -1 = unscheduled)
assigned = [Int(f"horizon_{i}") for i in range(N)]
scheduled = [Bool(f"scheduled_{i}") for i in range(N)]

opt = Optimize()
opt.set("timeout", 15000)   # scheduling is harder; allow more time

# Item 3: domain
for i in range(N):
    opt.add(assigned[i] >= -1)
    opt.add(assigned[i] < H)
    opt.add(scheduled[i] == (assigned[i] >= 0))

# Item 4: horizon capacity
for h in range(H):
    opt.add(Sum([If(assigned[i] == h, effort[i], 0) for i in range(N)]) <= horizon_capacity[h])

# Item 5: dependency ordering — downstream horizon ≥ upstream horizon (and both scheduled)
for down, up in dependencies:
    opt.add(Implies(scheduled[down],
                    And(scheduled[up], assigned[down] >= assigned[up])))

# Item 6: maximize total scheduled value
opt.maximize(Sum([If(scheduled[i], values[i], 0) for i in range(N)]))

variables = {f"horizon_{iid}": assigned[i] for i, iid in enumerate(init_ids)}

if opt.check() == sat:
    export_solution(solver=opt, variables=variables, objective=opt.objectives()[0])
else:
    export_solution(satisfiable=False, variables=variables)
```

**Output parsing.** Each `horizon_<init_id>` is an Int — `-1` means dropped from plan, `0..H-1` is the horizon index. Critical path = the longest dependency chain among scheduled items.

---

## Template 6: MaxSAT claim synthesis (D1 — `/gtm-audit`)

**Use cases.** Selecting the max-weight consistent subset of atomic GTM recommendations from across all agents when some pairs contradict each other. Uses the `solver-maxsat` MCP server (PySAT RC2 algorithm), NOT `solver-z3`.

**Solver.** `mcp__solver-maxsat__*` tools. Register `solver-maxsat` → `mcp-solver-maxsat.exe` in `~/.claude.json` before invoking.

**Model shape.**
- Each claim = 1-indexed SAT variable (PySAT convention)
- Hard clauses: incompatible pairs `[-i, -j]` — cannot both appear in the output
- Soft clauses: `[i]` with weight = `round(claim.weight × claim.confidence × 10)` — prefer including high-confidence, high-importance claims
- RC2 solver maximizes total weight of included claims subject to all hard constraints being satisfied

**Slots to fill.**
- `claims` — list of dicts, each with `id` (claimId string), `weight` (1–10), `confidence` (0.0–1.0)
- `incompatible_pairs` — list of `[i, j]` 0-indexed pairs from `incompatibleWithClaimIds` edges

**Template code (two `add_item` calls).**

```python
# Item 1: claim data (filled from collected stage outputs)
claims = [
    {"id": "analytics_agent.insight_001", "weight": 8, "confidence": 0.85},
    {"id": "ppc_agent.keyword_001",        "weight": 7, "confidence": 0.90},
    # ... all claims with claimId + weight + confidence
]
# Pairs are 0-indexed (claim A at index i, claim B at index j)
incompatible_pairs = [
    [0, 3],   # analytics_agent.insight_001 incompatible with competitor_mapper_agent.strategy_001
]
```

```python
# Item 2: WCNF model + RC2 solver + export
wcnf = WCNF()

# Hard clauses: incompatible pairs cannot both be selected
for pair in incompatible_pairs:
    wcnf.append([-(pair[0]+1), -(pair[1]+1)])

# Soft clauses: prefer each claim to be included, weight = importance × confidence
for idx, claim in enumerate(claims):
    w = max(1, round(claim["weight"] * claim["confidence"] * 10))
    wcnf.append([idx+1], weight=w)

# Solve with RC2 MaxSAT optimizer
with RC2(wcnf) as rc2:
    model = rc2.compute()

if model is not None:
    true_vars = set(v for v in model if v > 0)
    selected = sorted([i for i in range(len(claims)) if (i+1) in true_vars])
    dropped = sorted([i for i in range(len(claims)) if (i+1) not in true_vars])
    result = {
        "satisfiable": True,
        "status": "optimal",
        "selected_claim_ids": [claims[i]["id"] for i in selected],
        "dropped_claim_ids":  [claims[i]["id"] for i in dropped],
        "total_weight": sum(max(1, round(claims[i]["weight"] * claims[i]["confidence"] * 10))
                           for i in selected),
    }
    export_solution(result)
else:
    export_solution({
        "satisfiable": False,
        "status": "unsatisfiable",
        "selected_claim_ids": [],
        "dropped_claim_ids": [c["id"] for c in claims],
    })
```

**Output parsing.**
- `selected_claim_ids` — the max-weight consistent set; include these in the synthesis.
- `dropped_claim_ids` — excluded by solver. Each dropped claim's reason: "incompatible with higher-weight claim [X]" — compute this post-hoc by intersecting incompatible_pairs for the dropped claim with the selected set.
- `total_weight` — the objective value achieved by the solver.

**Claim collection protocol (upstream of the solver call).**
Scan every stage's `recommendations[]` array. Accept a claim into the MaxSAT input only if ALL four fields are present and valid: `claimId`, `atomicClaim`, `weight` (1–10), `confidence` (0.0–1.0). Skip any recommendation missing any field — do not default. Collect `incompatibleWithClaimIds` edges; build `incompatible_pairs` by mapping claim IDs to their 0-based indices.

**Important difference from z3 templates.**
- Use `export_solution(result_dict)` — pass the dict directly, not `solver=...` (RC2 object is already consumed by `.compute()`).
- No `clear_model` at the end — the `with RC2(wcnf) as rc2` context manager cleans up the solver.
- `mcp__solver-maxsat__solve_model` takes `timeout` in **milliseconds** like z3 (pass `timeout=10000`).
- The MCP server validates that `WCNF()`, `RC2`, and `solver.compute()` are all present in the code — all three are required or `solve_model` returns an error before executing.

**Common pitfalls.**
- Forgetting that PySAT variables are 1-indexed: claim at index 0 = variable 1. Off-by-one here produces silently wrong answers.
- Passing the RC2 object to `export_solution(data=rc2_solver)` instead of the result dict — RC2's `.model` attribute is only meaningful before the `with` block exits. Extract the model inside the `with` block.
- Building incompatible_pairs from only one direction of the edge (A→B but missing B→A). The `incompatibleWithClaimIds` field is directional — both directions are already declared if the schema was followed. De-duplicate before encoding.

---

## Quality bar

- **No model is ever authored from scratch — always start from a template.** If a problem doesn't fit one of these six shapes, propose a new template addition to this skill before encoding ad-hoc.
- **Item 1 of every model is data slot-filling**, never logic. This makes diffing two runs against the same brand easy.
- **All labeled assertions use lowercase snake_case tags** that read as English when narrated to the user. `budget_cap` not `c1`. `dep_seo_keyword_needs_seo_onpage` not `dep_3_0`.
- **No `print()` of variable values.** `export_solution` handles serialization. `print()` is for status only ("Solution found", "Property verified").
- **Always export.** Even when `result == unsat`, call `export_solution(satisfiable=False, variables=...)` — the command flow depends on the export envelope.

## Anti-patterns

- **Squashing all model items into one `add_item(0, very_long_code)` call.** The MCP server rejects items above a size threshold and the validation feedback per-item is lost. Split into 5–8 logical items.
- **Defining Z3 variables inside an inner function without returning them.** They become inaccessible to `export_solution`. Always return variables to the outer scope or pass them through a `variables` dict.
- **Using Python primitives in constraints.** `solver.add(5 + y == 10)` raises `'int' object has no attribute 'as_ast'`. Wrap with Int/Real constructors: `x = Int('x'); solver.add(x == 5); solver.add(x + y == 10)`.
- **Calling `solver.add(...)` on constraints that can drive UNSAT.** Use `solver.assert_and_track(constraint, "label")` so the unsat core has a human-readable explanation.
- **Forgetting `opt.set("timeout", 10000)`.** Hard scheduling/cover problems can hang for minutes. Always set a timeout. Treat timeout as functional infeasibility — surface as "constraints too tight, suggest relaxing: [active hard constraints]."

## Cross-skill references

- See `gtm-output-schemas` §8 (Solver Conventions) for the runtime conventions every command must follow when invoking the solver.
- See `marketing-channel-scoring` for how the linear-allocation template is wired into `/channel-score`.
- See `competitor-discovery-cot` for how set-cover is wired into `/competitor-map` candidate selection.
- See `swot-analysis` (Phase B1) for the knapsack template integration.
- See `porters-five-forces` (Phase C1) for the set-cover variant on response packaging.
- See `tam-sam-som-horizons` (Phase C2) for scheduling-with-deps.
- See `/gtm-audit` (Phase D1) for the maxsat-claim-synthesis template wired into the synthesis stage. Uses `solver-maxsat` MCP server, not `solver-z3`.

## Versioning

Patterns added or modified here are **MAJOR version bumps** for the skill — they change the contract every solver-using agent depends on.
