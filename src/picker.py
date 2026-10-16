import random
import config
import db

def select_and_update_pool(
    channel_id: str | None = None,
    exclude_user: str | None = None,
    explicit_user: str | None = None
) -> str:
    """
    Runs weighted selection excluding the last picked user, updates tickets,
    and commits state to DynamoDB.
    """
    target_channel = channel_id or config.DEFAULT_CHANNEL_ID
    tickets, last_picked = db.get_channel_state(target_channel)

    if not tickets:
        return "unknown"

    # Rule: Exclude both the last picked user and any explicitly excluded user (rerolls)
    disallowed = {u for u in [last_picked, exclude_user] if u}
    candidates = [u for u in tickets if u not in disallowed]

    # Graceful degradation if pool is small (e.g., <= 2 members)
    if not candidates:
        candidates = [u for u in tickets if u != exclude_user]
    if not candidates:
        candidates = list(tickets.keys())

    # Determine winner
    if explicit_user:
        chosen = explicit_user
    else:
        weights = [tickets[u] for u in candidates]
        chosen = random.choices(candidates, weights=weights, k=1)[0]

    # Update tickets: winner resets to 1, all others gain +1
    for user_id in tickets:
        if user_id == chosen:
            tickets[user_id] = 1
        else:
            tickets[user_id] += 1

    db.save_channel_state(target_channel, tickets, last_picked=chosen)
    return chosen


def refund_skipped_user(channel_id: str, user_id: str) -> None:
    """
    Restores ticket weight for a user who was skipped via 'Spin Again'
    or superseded by a volunteer, preventing unfair penalization.
    """
    tickets, last_picked = db.get_channel_state(channel_id)
    if user_id in tickets:
        # Restore their tickets to the pool's current maximum weight
        tickets[user_id] = max(tickets.values(), default=1)
        db.save_channel_state(channel_id, tickets, last_picked)


def sync_pool_members(channel_id: str, selected_users: list[str]) -> int:
    """
    Updates the pool membership while preserving existing ticket counts.
    New members receive the pool's average ticket weight.
    """
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