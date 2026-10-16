def build_picker_blocks(user_id: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🎯 Today's pick is *<@{user_id}>*!"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Spin Again 🎲", "emoji": True},
                    "action_id": "spin_again",
                    "value": user_id
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "I Volunteer 🙋", "emoji": True},
                    "action_id": "volunteer",
                    "value": user_id
                }
            ]
        }
    ]


def build_struck_through_blocks(user_id: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"~🎯 Today's pick is *<@{user_id}>*~"
            }
        }
    ]


def build_edit_pool_modal(channel_id: str, current_members: list[str]) -> dict:
    user_select_element = {
        "type": "multi_users_select",
        "action_id": "pool_users_select",
        "placeholder": {"type": "plain_text", "text": "Select team members"}
    }
    if current_members:
        user_select_element["initial_users"] = current_members

    return {
        "type": "modal",
        "callback_id": "save_pool_modal",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "Manage Picker Pool"},
        "submit": {"type": "plain_text", "text": "Save Pool"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Add or remove members eligible for the random draw:"
                }
            },
            {
                "type": "input",
                "block_id": "pool_input_block",
                "element": user_select_element,
                "label": {"type": "plain_text", "text": "Eligible Members"}
            }
        ]
    }