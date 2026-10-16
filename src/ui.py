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


def build_pool_modal(channel_id: str, pool_name: str, current_members: list[str]) -> dict:
    is_new = len(current_members) == 0

    title_text = f"Create: {pool_name}" if is_new else f"Edit: {pool_name}"
    submit_text = "Create Pool" if is_new else "Save Changes"
    intro_text = (
        f"Select team members to initialize the *{pool_name}* pool:"
        if is_new else
        f"Add or remove eligible members for *{pool_name}*:"
    )

    valid_slack_ids = list(dict.fromkeys([
        uid.strip()
        for uid in current_members
        if uid and re.match(r"^[UW][A-Z0-9]+$", uid.strip(), re.IGNORECASE)
    ]))

    user_select_element = {
        "type": "multi_users_select",
        "action_id": "pool_users_select",
        "placeholder": {"type": "plain_text", "text": "Select team members"}
    }
    if valid_slack_ids:
        user_select_element["initial_users"] = valid_slack_ids

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": intro_text}
        },
        {
            "type": "input",
            "block_id": "pool_input_block",
            "element": user_select_element,
            "label": {"type": "plain_text", "text": "Eligible Members"}
        }
    ]

    return {
        "type": "modal",
        "callback_id": "save_pool_modal",
        "private_metadata": json.dumps({
            "channel_id": channel_id,
            "pool_name": pool_name,
            "is_new": is_new
        }),
        "title": {"type": "plain_text", "text": title_text[:24]},
        "submit": {"type": "plain_text", "text": submit_text[:24]},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks
    }


def build_delete_confirm_modal(channel_id: str, pool_name: str) -> dict:
    return {
        "type": "modal",
        "callback_id": "confirm_delete_pool_modal",
        "private_metadata": json.dumps({
            "channel_id": channel_id,
            "pool_name": pool_name
        }),
        "title": {"type": "plain_text", "text": "Delete Pool"[:24]},
        "submit": {"type": "plain_text", "text": "Yes, Delete"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ Are you sure you want to permanently delete the *{pool_name}* pool? All pick counts and weight history will be lost."
                }
            }
        ]
    }


def build_all_pools_overview_blocks(pools: dict) -> list[dict]:
    if not pools:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "ℹ️ No pools configured for this channel yet. Use `/create <pool_name>` to make one."
                }
            }
        ]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Channel Pools Overview", "emoji": True}
        },
        {"type": "divider"}
    ]

    for name, data in sorted(pools.items()):
        member_count = len(data.get("tickets", {}))
        total_picks = sum(data.get("picks_count", {}).values())
        last_picked = data.get("last_picked")
        last_picked_str = f"<@{last_picked}>" if last_picked else "None"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{name}*\n"
                    f"• Members: `{member_count}`\n"
                    f"• Total Picks: `{total_picks}`\n"
                    f"• Last Picked: {last_picked_str}"
                )
            }
        })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "💡 Run `/stats <pool_name>` for individual ticket weights and member leaderboards."}
        ]
    })
    return blocks


def build_pool_leaderboard_blocks(
    pool_name: str,
    tickets: dict[str, int],
    picks_count: dict[str, int],
    last_picked: str | None
) -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Stats: {pool_name}", "emoji": True}
        }
    ]

    last_str = f"<@{last_picked}>" if last_picked else "None"
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Last selected: *{last_str}*"}
        ]
    })
    blocks.append({"type": "divider"})

    if not tickets:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No members registered in this pool._"}
        })
        return blocks

    # Sort users primarily by picks count (descending), then ticket weight
    sorted_users = sorted(
        tickets.keys(),
        key=lambda u: (picks_count.get(u, 0), tickets.get(u, 1)),
        reverse=True
    )

    lines = []
    for rank, uid in enumerate(sorted_users, start=1):
        picks = picks_count.get(uid, 0)
        weight = tickets.get(uid, 1)
        lines.append(f"`{rank}.` <@{uid}> — *{picks}* picks (Current tickets: `{weight}`)")

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n".join(lines)}
    })

    return blocks