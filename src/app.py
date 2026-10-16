import json
import os
import random
import boto3
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    process_before_response=True
)
slack_handler = SlackRequestHandler(app=app)

# Initialize DynamoDB table
dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("DYNAMODB_TABLE", "slack-picker-pools")
pool_table = dynamodb.Table(table_name)


# ---------------------------------------------------------------------------
# Data Persistence Helpers
# ---------------------------------------------------------------------------

def get_user_pool(channel_id=None):
    target_channel = channel_id or os.environ.get("SLACK_CHANNEL_ID")
    try:
        response = pool_table.get_item(Key={"channel_id": target_channel})
        if "Item" in response and "users" in response["Item"]:
            return response["Item"]["users"]
    except Exception as e:
        print(f"Error fetching pool from DynamoDB: {e}")

    # Fallback to environment variable if DB lookup yields nothing
    raw_pool = os.environ.get("USER_POOL", "")
    return [uid.strip() for uid in raw_pool.split(",") if uid.strip()]


def save_user_pool(channel_id, users):
    pool_table.put_item(
        Item={
            "channel_id": channel_id,
            "users": users
        }
    )


# ---------------------------------------------------------------------------
# Picker Logic & UI Blocks
# ---------------------------------------------------------------------------

def pick_user(exclude_user=None, channel_id=None):
    pool = get_user_pool(channel_id)
    candidates = [u for u in pool if u != exclude_user]
    if not candidates:
        candidates = pool
    return random.choice(candidates) if candidates else "unknown"


def build_picker_blocks(user_id):
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


def run_sortes_pick():
    channel = os.environ["SLACK_CHANNEL_ID"]
    user = pick_user(channel_id=channel)
    app.client.chat_postMessage(
        channel=channel,
        text=f"Today's pick is <@{user}>!",
        blocks=build_picker_blocks(user)
    )
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "pick_posted", "user": user})
    }


# ---------------------------------------------------------------------------
# Slash Command & Modal Handlers
# ---------------------------------------------------------------------------

@app.command("/edit-pool")
def handle_edit_pool_command(ack, body, client):
    ack()
    channel_id = body["channel_id"]
    current_pool = get_user_pool(channel_id)

    # Note: Slack rejects the modal payload if initial_users is an empty list
    user_select_element = {
        "type": "multi_users_select",
        "action_id": "pool_users_select",
        "placeholder": {"type": "plain_text", "text": "Select team members"}
    }
    if current_pool:
        user_select_element["initial_users"] = current_pool

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "save_pool_modal",
            "private_metadata": channel_id,  # Passes channel_id to the view submission
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
    )


@app.view("save_pool_modal")
def handle_save_pool_modal(ack, body, client):
    ack()
    channel_id = body["view"]["private_metadata"]
    state_values = body["view"]["state"]["values"]
    selected_users = state_values["pool_input_block"]["pool_users_select"]["selected_users"]

    save_user_pool(channel_id, selected_users)

    # Ephemeral notification visible only to the user who updated the list
    client.chat_postEphemeral(
        channel=channel_id,
        user=body["user"]["id"],
        text=f"✅ Updated! Pool now contains *{len(selected_users)}* members."
    )


# ---------------------------------------------------------------------------
# Interaction Handlers
# ---------------------------------------------------------------------------

@app.action("spin_again")
def handle_spin_again(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    previous_user = body.get("actions", [{}])[0].get("value")
    next_user = pick_user(exclude_user=previous_user, channel_id=channel_id)

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"~Today's pick is <@{previous_user}>!~",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"~🎯 Today's pick is *<@{previous_user}>*~"
                }
            }
        ]
    )

    client.chat_postMessage(
        channel=channel_id,
        text=f"Today's pick is <@{next_user}>!",
        blocks=build_picker_blocks(next_user)
    )


@app.action("volunteer")
def handle_volunteer(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    volunteer_user = body["user"]["id"]
    previous_user = body.get("actions", [{}])[0].get("value")

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"~Today's pick is <@{previous_user}>!~",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🎯 ~Today's pick is *<@{previous_user}>*~"
                }
            }
        ]
    )

    client.chat_postMessage(
        channel=channel_id,
        text=f"🎯 <@{volunteer_user}> bravely volunteered!",
        blocks=build_picker_blocks(volunteer_user)
    )


def lambda_handler(event, context):
    if event.get("source") in ["aws.events", "aws.scheduler"]:
        return run_sortes_pick()
    return slack_handler.handle(event, context)