#!/usr/bin/env python3
"""
ore_optimize.py

Find a (near-)optimal per-block allocation of a budget of SOL to maximize expected
value after fees for the ORE mining game.

Algorithm:
  Greedy discrete marginal-EV allocation:
    - Discretize budget into units (default 0.001 SOL).
    - Repeatedly compute marginal EV (per unit) for adding one unit to each block,
      pick the block with the highest positive marginal EV, allocate one unit there,
      and repeat until budget exhausted or no positive marginal EVs remain.

Fees & tokenomics implemented:
  - protocol_fee on mining rewards (default 10% -> 0.10).
  - Focus on SOL EV optimization only (ORE treated as bonus, not calculated).

Input:
  - Provide opposing grid of 25 numbers (row-major) either via --other (comma separated)
    or via --grid-file (CSV with 25 numbers). If neither provided, a sample grid is used.

Output:
  - Recommended gross allocation per block (25 numbers).
  - Expected SOL EV after protocol fees.
  - Marginal EV per block for one more unit.

Usage examples:
  python3 ore_optimize.py --budget 0.5 --unit 0.001 --other "0.25,0.27,..."
  python3 ore_optimize.py --budget 0.5 --unit 0.01 --grid-file other.csv
"""

import argparse
import numpy as np
import csv
import sys
from textwrap import dedent

def parse_grid_string(s):
    parts = [p.strip() for p in s.split(',') if p.strip() != '']
    if len(parts) != 25:
        raise ValueError("Must supply exactly 25 numbers for the grid.")
    return np.array([float(x) for x in parts], dtype=np.float64)

def read_grid_csv(path):
    vals = []
    with open(path, newline='') as f:
        r = csv.reader(f)
        for row in r:
            for cell in row:
                if cell.strip() != '':
                    vals.append(float(cell))
    if len(vals) != 25:
        raise ValueError("CSV must contain exactly 25 numbers (5x5). Found: %d" % len(vals))
    return np.array(vals, dtype=np.float64)

# ---- Core math functions ----
def compute_expected_return_and_components(T_net, s_net):
    """
    Given T_net (other miners' net in pool per block) and s_net (your net in pool per block),
    compute:
      - expected_return: expected SOL returned to you after the round (before reward-fee application)
      - expected_kept_stakes: expected kept-stake portion (the x_i kept when the block wins)
      - expected_rewards_before_fee: expected reward portion before reward fee
      - ore_expected_raw_share: expected raw ORE (raw number of ORE tokens before refining) from per-round awards (doesn't include motherlode)
    """
    n = len(T_net)
    total_net = T_net + s_net
    total_net_sum = total_net.sum()
    expected_return = 0.0
    ore_expected_raw = 0.0

    for i in range(n):
        denom = total_net[i]
        if denom <= 0:
            continue
        sum_others = total_net_sum - denom
        # payout if block i wins (before reward fee)
        reward = (s_net[i] / denom) * sum_others
        payout_i = s_net[i] + reward
        expected_return += payout_i

        # expected "chance" you get the single-miner ORE award when this block wins:
        ore_expected_raw += (s_net[i] / denom)

    expected_return /= n
    ore_expected_raw /= n  # because each block wins with probability 1/n

    expected_kept_stakes = s_net.sum() / n
    expected_rewards_before_fee = expected_return - expected_kept_stakes

    return {
        'expected_return': expected_return,
        'expected_kept_stakes': expected_kept_stakes,
        'expected_rewards_before_fee': expected_rewards_before_fee,
        'ore_expected_raw': ore_expected_raw
    }

def compute_ev(T_other_gross, s_alloc_gross, protocol_fee):
    """
    Compute EV in SOL given gross inputs:
      - T_other_gross: opponents' gross deployed per block (length 25)
      - s_alloc_gross: your gross deployed per block (length 25)
    Returns dictionary with SOL EV after protocol fees.
    """
    T_other_gross = np.array(T_other_gross, dtype=np.float64)
    s_alloc_gross = np.array(s_alloc_gross, dtype=np.float64)
    # no admin fee - amounts sit in pool as deployed
    T_net = T_other_gross
    s_net = s_alloc_gross

    comps = compute_expected_return_and_components(T_net, s_net)
    expected_return = comps['expected_return']
    expected_kept_stakes = comps['expected_kept_stakes']
    expected_rewards_before_fee = comps['expected_rewards_before_fee']

    # protocol fee is taken from reward portion:
    expected_rewards_after_fee = expected_rewards_before_fee * (1.0 - protocol_fee)
    expected_return_after_protocol_fee = expected_kept_stakes + expected_rewards_after_fee

    # EV in SOL terms:
    cost_gross = s_alloc_gross.sum()
    ev_sol_after_fees = expected_return_after_protocol_fee - cost_gross

    return {
        'ev_sol_after_fees': ev_sol_after_fees,
        'expected_return_after_protocol_fee': expected_return_after_protocol_fee,
        'cost_gross': cost_gross,
        's_net': s_net,
        'T_net': T_net,
        'components': comps
    }

# ---- Greedy discrete optimizer ----
def greedy_optimize(T_other_gross, budget, unit, protocol_fee, max_iters=None):
    """
    Greedy allocate discrete units to maximize SOL EV.
    Returns s_alloc_gross vector.
    """
    n = len(T_other_gross)
    assert n == 25
    s = np.zeros(n, dtype=np.float64)
    remaining_units = int(round(budget / unit))
    if remaining_units <= 0:
        return s

    if max_iters is None:
        max_iters = remaining_units

    # Precompute T_other_gross constant
    T_other_gross = np.array(T_other_gross, dtype=np.float64)

    for step in range(max_iters):
        if remaining_units <= 0:
            break

        # compute base EV
        base = compute_ev(T_other_gross, s, protocol_fee)
        base_score = base['ev_sol_after_fees']

        best_idx = None
        best_delta = -1e18

        # evaluate adding one unit to each block
        for i in range(n):
            s_test = s.copy()
            s_test[i] += unit
            candidate = compute_ev(T_other_gross, s_test, protocol_fee)
            candidate_score = candidate['ev_sol_after_fees']
            delta = candidate_score - base_score
            if delta > best_delta:
                best_delta = delta
                best_idx = i

        # stop if no positive marginal EV
        if best_delta <= 1e-12:
            # tiny tolerance
            break

        # allocate one unit to best_idx
        s[best_idx] += unit
        remaining_units -= 1

    return s

def pretty_print_grid(arr, label="grid"):
    arr = np.array(arr).reshape((5,5))
    print(f"\n{label} (5x5):")
    for r in arr:
        print("  ".join(f"{x:8.4f}" for x in r))

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=dedent(__doc__))
    parser.add_argument("--budget", type=float, required=True, help="Total SOL budget to deploy this round (gross).")
    parser.add_argument("--unit", type=float, default=0.001, help="Discretization unit for greedy allocation (SOL).")
    parser.add_argument("--other", type=str, default=None,
                        help="25 comma-separated numbers for other miners' total (gross) stakes on each block (row-major).")
    parser.add_argument("--grid-file", type=str, default=None, help="CSV file containing 25 numbers for other miners.")
    parser.add_argument("--protocol-fee", type=float, default=0.10, help="Protocol fee fraction on mining rewards (default 0.10).")
    parser.add_argument("--max-iters", type=int, default=None, help="Max greedy allocation iterations (default based on budget/unit).")

    args = parser.parse_args()

    if args.other is not None:
        try:
            T_other = parse_grid_string(args.other)
        except Exception as e:
            print("Error parsing --other:", e)
            sys.exit(1)
    elif args.grid_file is not None:
        try:
            T_other = read_grid_csv(args.grid_file)
        except Exception as e:
            print("Error reading grid file:", e)
            sys.exit(1)
    else:
        # default sample grid (replace with actual values)
        T_other = np.array([
            0.3356,0.3281,0.346,0.3346,0.3148,
            0.3745,0.341,0.3288,0.3097,0.3339,
            0.3669,0.3444,0.3456,0.3495,0.3425,
            0.3402,0.3399,0.3118,0.3346,0.3227,
            0.3172,0.3455,0.3681,0.3423,0.3198
        ], dtype=np.float64)
        print("No grid supplied; using built-in example grid (replace via --other or --grid-file).")

    if len(T_other) != 25:
        print("Error: other grid must contain 25 numbers.")
        sys.exit(1)

    print("\n--- Input summary ---")
    pretty_print_grid(T_other, label="Other miners' gross stakes (per-block)")
    print(f"\nBudget: {args.budget:.6f} SOL, unit: {args.unit:.6f} SOL")
    print(f"Protocol fee: {args.protocol_fee*100:.2f}%")
    print("\nRunning greedy optimizer... (this may take some seconds depending on budget/unit)")

    s_alloc = greedy_optimize(T_other, args.budget, args.unit, args.protocol_fee, max_iters=args.max_iters)

    pretty_print_grid(s_alloc, label="Recommended gross allocation (your deployed SOL per block)")

    results = compute_ev(T_other, s_alloc, args.protocol_fee)

    print("\n--- Results ---")
    print(f"Total deployed (gross): {results['cost_gross']:.6f} SOL")
    print(f"Total deployed (net in pool): {results['s_net'].sum():.6f} SOL")
    print(f"Expected final SOL returned after round (post protocol-fee): {results['expected_return_after_protocol_fee']:.6f} SOL")
    print(f"Expected SOL EV after fees: {results['ev_sol_after_fees']:.8f} SOL")

    # show top allocations and marginal EVs
    idxs = np.argsort(-s_alloc)
    print("\nTop allocations (index 0..24, row-major):")
    for idx in idxs[:8]:
        print(f"  block #{idx:02d}: allocate {s_alloc[idx]:.6f} SOL (net in pool {s_alloc[idx]:.6f} SOL)")

    # marginal EV per block for adding one unit
    print("\nMarginal EV for adding one unit to each block:")
    base = compute_ev(T_other, s_alloc, args.protocol_fee)
    base_score_sol = base['ev_sol_after_fees']
    for i in range(25):
        s_test = s_alloc.copy()
        s_test[i] += args.unit
        cand = compute_ev(T_other, s_test, args.protocol_fee)
        cand_score_sol = cand['ev_sol_after_fees']
        delta_sol = cand_score_sol - base_score_sol
        print(f"  block {i:02d}: marginal = {delta_sol:+.10f} SOL")

    print("\nDone.")

if __name__ == "__main__":
    main()
