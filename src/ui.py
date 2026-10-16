def build_all_pools_overview_blocks(pools: dict) -> list[dict]:
    if not pools:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "ℹ️ No pools exist in this channel yet. Create one with `/create <pool_name>`."}
        }]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📋 Channel Pools Overview", "emoji": True}
        },
        {"type": "divider"}
    ]

    for name, data in pools.items():
        member_count = len(data.get("tickets", {}))
        total_picks = sum(data.get("picks_count", {}).values())
        last = data.get("last_picked")
        last_str = f"<@{last}>" if last else "None"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"• *`{name}`*: *{member_count}* members | *{total_picks}* total picks | Last pick: {last_str}"
            }
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "💡 Run `/stats <pool_name>` to view detailed odds & leaderboard."}]
    })
    return blocks