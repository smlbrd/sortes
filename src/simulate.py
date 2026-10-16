from collections import Counter
from picker import compute_weighted_pick

# ---------------------------------------------------------------------------
# Test 1: Step-by-Step Ticket Trace (8 Rounds)
# ---------------------------------------------------------------------------
print("=== Step-by-Step Trace (8 Rounds) ===")
tickets = {"Apple": 1, "Banana": 1, "Clementine": 1, "Durian": 1, "Egg": 1}
last_picked = None

print(f"Start:   Tickets = {tickets}")

for round_num in range(1, 9):
    chosen, tickets = compute_weighted_pick(tickets, last_picked=last_picked)
    last_picked = chosen
    print(f"Round {round_num}: Picked -> {chosen:<7} | New Tickets: {tickets}")


# ---------------------------------------------------------------------------
# Test 2: Monte Carlo Simulation (10,000 Rounds)
# ---------------------------------------------------------------------------
print("\n=== Running 10,000 Round Simulation ===")

users = ["Apple", "Banana", "Clementine", "Durian", "Egg"]
tickets = {u: 1 for u in users}
last_picked = None

NUM_ROUNDS = 10_000
pick_history = []
consecutive_violations = 0
min_gap_between_picks = {u: float("inf") for u in users}
last_seen_index = {}

for i in range(NUM_ROUNDS):
    chosen, tickets = compute_weighted_pick(tickets, last_picked=last_picked)
    last_picked = chosen

    # Check 1: Consecutive pick rule verification
    if pick_history and pick_history[-1] == chosen:
        consecutive_violations += 1

    # Check 2: Minimum gap tracking
    if chosen in last_seen_index:
        gap = i - last_seen_index[chosen]
        if gap < min_gap_between_picks[chosen]:
            min_gap_between_picks[chosen] = gap
    last_seen_index[chosen] = i

    pick_history.append(chosen)

# ---------------------------------------------------------------------------
# Results & Verification
# ---------------------------------------------------------------------------
counts = Counter(pick_history)

print("\n--- Constraints Check ---")
print(f"Back-to-back violations: {consecutive_violations} (Expected: 0)")

for u in users:
    gap = min_gap_between_picks[u]
    print(f"Minimum gap between picks for {u:<7}: {gap} rounds (Expected: >= 2)")

print("\n--- Distribution Over 10,000 Picks ---")
for user, count in sorted(counts.items()):
    pct = (count / NUM_ROUNDS) * 100
    print(f"{user:<7}: {count} picks ({pct:.1f}%)")