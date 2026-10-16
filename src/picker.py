import random

# ---------------------------------------------------------------------------
# Pure Domain Logic (No AWS, no Slack, standard library only)
# ---------------------------------------------------------------------------

def compute_weighted_pick(
    tickets: dict[str, int],
    last_picked: str | None = None,
    exclude_user: str | None = None,
    explicit_user: str | None = None
) -> tuple[str, dict[str, int]]:
    """
    Pure function: calculates the winner and new ticket balances.
    Returns: (chosen_user_id, updated_tickets_dict)
    """
    if not tickets:
        return "unknown", {}

    updated = dict(tickets)

    # Hard recency filter: exclude last_picked and rerolled user
    disallowed = {u for u in [last_picked, exclude_user] if u}
    candidates = [u for u in updated if u not in disallowed]

    # Fallbacks for small pools (<= 2 members)
    if not candidates:
        candidates = [u for u in updated if u != exclude_user]
    if not candidates:
        candidates = list(updated.keys())

    # Selection
    if explicit_user:
        chosen = explicit_user
    else:
        weights = [updated[u] for u in candidates]
        chosen = random.choices(candidates, weights=weights, k=1)[0]

    # Update weights
    for user_id in updated:
        if user_id == chosen:
            updated[user_id] = 1
        else:
            updated[user_id] += 1

    return chosen, updated


# ---------------------------------------------------------------------------
# I/O Orchestration (DynamoDB-backed)
# ---------------------------------------------------------------------------

def select_and_update_pool(
    channel_id: str | None = None,
    exclude_user: str | None = None,
    explicit_user: str | None = None
) -> str:
    import config
    import db

    target_channel = channel_id or config.DEFAULT_CHANNEL_ID
    tickets, last_picked = db.get_channel_state(target_channel)

    chosen, new_tickets = compute_weighted_pick(
        tickets=tickets,
        last_picked=last_picked,
        exclude_user=exclude_user,
        explicit_user=explicit_user
    )

    db.save_channel_state(target_channel, new_tickets, last_picked=chosen)
    return chosen


def refund_skipped_user(channel_id: str, user_id: str) -> None:
    import db
    tickets, last_picked = db.get_channel_state(channel_id)
    if user_id in tickets:
        tickets[user_id] = max(tickets.values(), default=1)
        db.save_channel_state(channel_id, tickets, last_picked)


def sync_pool_members(channel_id: str, selected_users: list[str]) -> int:
    import db
    old_tickets, last_picked = db.get_channel_state(channel_id)
    avg_tickets = (sum(old_tickets.values()) // len(old_tickets)) if old_tickets else 1

    updated_tickets = {
        uid: old_tickets.get(uid, max(1, avg_tickets))
        for uid in selected_users
    }

    if last_picked not in updated_tickets:
        last_picked = None

    db.save_channel_state(channel_id, updated_tickets, last_picked)
    return len(updated_tickets)