import random

# ---------------------------------------------------------------------------
# Pure Algorithm (Zero dependencies - runs cleanly in simulate.py)
# ---------------------------------------------------------------------------

def compute_weighted_pick(
    tickets: dict[str, int],
    last_picked: str | None = None,
    exclude_user: str | None = None,
    explicit_user: str | None = None
) -> tuple[str, dict[str, int]]:
    """
    Pure selection logic: calculates winner and returns updated ticket weights.
    Returns: (chosen_user_id, updated_tickets_dict)
    """
    if not tickets:
        return "unknown", {}

    updated = dict(tickets)

    # Disallow back-to-back picks and excluded (rerolled) users
    disallowed = {u for u in [last_picked, exclude_user] if u}
    candidates = [u for u in updated if u not in disallowed]

    # Fallback if pool is small (<= 2 members)
    if not candidates:
        candidates = [u for u in updated if u != exclude_user]
    if not candidates:
        candidates = list(updated.keys())

    if explicit_user:
        chosen = explicit_user
    else:
        weights = [updated[u] for u in candidates]
        chosen = random.choices(candidates, weights=weights, k=1)[0]

    # Update tickets: winner drops to 1, others gain +1
    for user_id in updated:
        if user_id == chosen:
            updated[user_id] = 1
        else:
            updated[user_id] += 1

    return chosen, updated


# ---------------------------------------------------------------------------
# I/O Orchestration (DynamoDB-dependent functions)
# ---------------------------------------------------------------------------

def select_and_update_pool(
    channel_id: str | None = None,
    pool_name: str = "default",
    exclude_user: str | None = None,
    explicit_user: str | None = None
) -> str:
    import config
    import db

    target_channel = channel_id or config.DEFAULT_CHANNEL_ID
    tickets, picks_count, last_picked = db.get_pool_data(target_channel, pool_name)

    if not tickets:
        return "unknown"

    chosen, new_tickets = compute_weighted_pick(
        tickets=tickets,
        last_picked=last_picked,
        exclude_user=exclude_user,
        explicit_user=explicit_user
    )

    picks_count[chosen] = picks_count.get(chosen, 0) + 1
    db.save_pool_data(target_channel, pool_name, new_tickets, picks_count, last_picked=chosen)
    return chosen


def refund_skipped_user(channel_id: str, pool_name: str, user_id: str) -> None:
    import db

    tickets, picks_count, last_picked = db.get_pool_data(channel_id, pool_name)

    if user_id in tickets:
        tickets[user_id] = max(tickets.values(), default=1)

    if user_id in picks_count and picks_count[user_id] > 0:
        picks_count[user_id] -= 1

    db.save_pool_data(channel_id, pool_name, tickets, picks_count, last_picked)


def sync_pool_members(channel_id: str, pool_name: str, selected_users: list[str]) -> int:
    import db

    old_tickets, old_picks, last_picked = db.get_pool_data(channel_id, pool_name)
    avg_tickets = (sum(old_tickets.values()) // len(old_tickets)) if old_tickets else 1

    updated_tickets = {
        uid: old_tickets.get(uid, max(1, avg_tickets))
        for uid in selected_users
    }
    updated_picks = {
        uid: old_picks.get(uid, 0)
        for uid in selected_users
    }

    if last_picked not in updated_tickets:
        last_picked = None

    db.save_pool_data(channel_id, pool_name, updated_tickets, updated_picks, last_picked)
    return len(updated_tickets)