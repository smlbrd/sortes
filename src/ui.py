import json
import re

def build_picker_blocks(user_id: str, pool_name: str = "default") -> list[dict]:
    payload = json.dumps({"pool": pool_name, "user": user_id})
    title = f" [{pool_name}]" if pool_name != "default" else ""

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🎯 Today's pick{title} is *<@{user_id}>*!"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Spin Again 🎲", "emoji": True},
                    "action_id": "spin_again",
                    "value": payload
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "I Volunteer 🙋", "emoji": True},
                    "action_id": "volunteer",
                    "value": payload
                }
            ]
        }
    ]


def build_struck_through_blocks(user_id: str, pool_name: str = "default") -> list[dict]:
    title = f" [{pool_name}]" if pool_name != "default" else ""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"~🎯 Today's pick{title} is *<@{user_id}>*~"
            }
        }
    ]


def build_edit_pool_modal(channel_id: str, pool_name: str, current_members: list[str]) -> dict:
    valid_slack_ids = [uid for uid in current_members if re.match(r"^[UW][A-Z0-9]+\$", uid)]

    user_select_element = {
        "type": "multi_users_select",
        "action_id": "pool_users_select",
        "placeholder": {"type": "plain_text", "text": "Select team members"}
    }
    if valid_slack_ids:
        user_select_element["initial_users"] = valid_slack_ids

    return {
        "type": "modal",
        "callback_id": "save_pool_modal",
        "private_metadata": json.dumps({"channel_id": channel_id, "pool_name": pool_name}),
        "title": {"type": "plain_text", "text": f"Pool: {pool_name[:18]}"},
        "submit": {"type": "plain_text", "text": "Save Pool"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Edit eligible members for *{pool_name}*:"}
            },
            {
                "type": "input",
                "block_id": "pool_input_block",
                "element": user_select_element,
                "label": {"type": "plain_text", "text": "Eligible Members"}
            }
        ]
    }


def build_all_pools_overview_blocks(pools: dict) -> list[dict]:
    if not pools:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "ℹ️ No pools exist in this channel yet. Create one with `/edit-pool <pool_name>`."}
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
        "elements": [{"type": "mrkdwn", "text": "💡 Run `/sortes-stats <pool_name>` to view detailed odds & leaderboard."}]
    })
    return blocks


def build_pool_leaderboard_blocks(pool_name: str, tickets: dict, picks_count: dict, last_picked: str | None) -> list[dict]:
    total_tickets = sum(tickets.values())
    total_picks = sum(picks_count.values())
    sorted_users = sorted(tickets.keys(), key=lambda u: picks_count.get(u, 0), reverse=True)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 Pool Stats: {pool_name}", "emoji": True}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Total rounds: *{total_picks}* | Active members: *{len(tickets)}*"}]
        },
        {"type": "divider"}
    ]

    lines = []
    # Candidate tickets excluding cooldown member
    cooldown_tickets = tickets.get(last_picked, 0) if last_picked else 0
    candidate_tickets = total_tickets - cooldown_tickets

    for uid in sorted_users:
        picks = picks_count.get(uid, 0)
        tix = tickets.get(uid, 1)

        if uid == last_picked:
            odds_str = "0% (Cooldown 🕒)"
        elif candidate_tickets > 0:
            pct = (tix / candidate_tickets) * 100
            odds_str = f"~{pct:.1f}% ({tix} tickets)"
        else:
            odds_str = "—"

        line = f"• <@{uid}>: *{picks}* picks | Odds: {odds_str}"
        if uid == last_picked:
            line += " 🎯"
        lines.append(line)

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n".join(lines)}
    })
    return blocks