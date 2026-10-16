from decimal import Decimal
import config

def get_channel_state(channel_id: str | None = None) -> tuple[dict[str, int], str | None]:
    """
    Retrieves the ticket mapping and last_picked user for a given channel.
    Returns: (tickets_dict, last_picked_user_id)
    """
    target_channel = channel_id or config.DEFAULT_CHANNEL_ID
    try:
        response = config.pool_table.get_item(Key={"channel_id": target_channel})
        if "Item" in response:
            item = response["Item"]
            raw_tickets = item.get("tickets", {})
            # DynamoDB deserializes numbers as Decimal; convert to standard ints
            tickets = {uid: int(count) for uid, count in raw_tickets.items()}
            return tickets, item.get("last_picked")
    except Exception as e:
        print(f"Error reading DynamoDB for channel {target_channel}: {e}")

    # Fallback to environment variable if no record exists
    return {uid: 1 for uid in config.FALLBACK_USER_POOL}, None


def save_channel_state(channel_id: str, tickets: dict[str, int], last_picked: str | None) -> None:
    """Persists updated tickets and last_picked user ID to DynamoDB."""
    config.pool_table.put_item(
        Item={
            "channel_id": channel_id,
            "tickets": tickets,
            "last_picked": last_picked
        }
    )