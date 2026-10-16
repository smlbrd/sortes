import config

def get_channel_pools(channel_id: str | None = None) -> dict:
    """Returns all pools defined for a given channel."""
    target_channel = channel_id or config.DEFAULT_CHANNEL_ID
    if not config.pool_table:
        return _fallback_pools()

    try:
        response = config.pool_table.get_item(Key={"channel_id": target_channel})
        if "Item" in response:
            item = response["Item"]

            # 1. Multi-pool format: item["pools"]
            if "pools" in item:
                pools = {}
                for pool_name, data in item["pools"].items():
                    raw_tickets = data.get("tickets", {})
                    raw_picks = data.get("picks_count", {})
                    pools[pool_name] = {
                        "tickets": {uid: int(c) for uid, c in raw_tickets.items()},
                        "picks_count": {uid: int(c) for uid, c in raw_picks.items()},
                        "last_picked": data.get("last_picked")
                    }
                return pools

            # 2. Legacy fallback A: single-pool weighted record
            if "tickets" in item:
                raw_tickets = item.get("tickets", {})
                return {
                    "default": {
                        "tickets": {uid: int(c) for uid, c in raw_tickets.items()},
                        "picks_count": {uid: 0 for uid in raw_tickets},
                        "last_picked": item.get("last_picked")
                    }
                }

            # 3. Legacy fallback B: original app format with 'users' list
            if "users" in item:
                raw_users = item.get("users", [])
                return {
                    "default": {
                        "tickets": {uid: 1 for uid in raw_users},
                        "picks_count": {uid: 0 for uid in raw_users},
                        "last_picked": None
                    }
                }
    except Exception as e:
        print(f"Error reading DynamoDB for channel {target_channel}: {e}")

    return _fallback_pools()

def get_pool_data(channel_id: str | None, pool_name: str = "default") -> tuple[dict[str, int], dict[str, int], str | None]:
    """Returns (tickets, picks_count, last_picked) for a specific pool."""
    pools = get_channel_pools(channel_id)

    # If 'default' is requested but doesn't exist, and the channel only has 1 named pool,
    # automatically resolve to that pool (e.g. user ran `/edit-pool` instead of `/edit-pool standup`)
    resolved_name = pool_name
    if resolved_name == "default" and "default" not in pools and len(pools) == 1:
        resolved_name = next(iter(pools.keys()))

    pool = pools.get(resolved_name, {"tickets": {}, "picks_count": {}, "last_picked": None})
    return pool.get("tickets", {}), pool.get("picks_count", {}), pool.get("last_picked")


def save_pool_data(
    channel_id: str,
    pool_name: str,
    tickets: dict[str, int],
    picks_count: dict[str, int],
    last_picked: str | None
) -> None:
    """Persists a pool's tickets, pick stats, and last pick to DynamoDB."""
    if not config.pool_table:
        return

    pools = get_channel_pools(channel_id)
    pools[pool_name] = {
        "tickets": tickets,
        "picks_count": picks_count,
        "last_picked": last_picked
    }
    config.pool_table.put_item(
        Item={
            "channel_id": channel_id,
            "pools": pools
        }
    )

def _fallback_pools() -> dict:
    return {
        "default": {
            "tickets": {uid: 1 for uid in config.FALLBACK_USER_POOL},
            "picks_count": {uid: 0 for uid in config.FALLBACK_USER_POOL},
            "last_picked": None
        }
    }

def delete_pool(channel_id: str, pool_name: str) -> bool:
    """Removes a pool from DynamoDB. Returns True if deleted, False if not found."""
    if not config.pool_table:
        return False

    pools = get_channel_pools(channel_id)
    if pool_name not in pools:
        return False

    del pools[pool_name]

    config.pool_table.put_item(
        Item={
            "channel_id": channel_id,
            "pools": pools
        }
    )
    return True