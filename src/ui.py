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
        if uid and re.match(r"^[UW][A-Z0-9]+\$", uid.strip(), re.IGNORECASE)
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

    # Add delete button at the bottom when editing an existing pool
    if not is_new:
        blocks.extend([
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🗑️ Delete Pool", "emoji": True},
                        "style": "danger",
                        "action_id": "initiate_delete_pool_from_modal",
                        "value": json.dumps({"channel_id": channel_id, "pool_name": pool_name})
                    }
                ]
            }
        ])

    return {
        "type": "modal",
        "callback_id": "save_pool_modal",
        "private_metadata": json.dumps({
            "channel_id": channel_id,
            "pool_name": pool_name,
            "is_new": is_new
        }),
        "title": {"type": "plain_text", "text": title_text[:24]},
        "submit": {"type": "plain_text", "text":