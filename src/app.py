import json
import os
import random
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    process_before_response=True
)
slack_handler = SlackRequestHandler(app=app)

def get_user_pool():
    raw_pool = os.environ.get("USER_POOL", "")
    return [uid.strip() for uid in raw_pool.split(",") if uid.strip()]

def pick_user(exclude_user=None):
    pool = get_user_pool()
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
                    "text": {
                        "type": "plain_text",
                        "text": "Spin Again 🎲",
                        "emoji": True
                    },
                    "action_id": "spin_again",
                    "value": user_id
                }
            ]
        }
    ]

def run_sortes_pick():
    user = pick_user()
    channel = os.environ["SLACK_CHANNEL_ID"]
    app.client.chat_postMessage(
        channel=channel,
        text=f"Today's pick is <@{user}>!",
        blocks=build_picker_blocks(user)
    )
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "pick_posted", "user": user})
    }

@app.action("spin_again")
def handle_spin_again(ack, body, client):
    ack()
    previous_user = body.get("actions", [{}])[0].get("value")
    next_user = pick_user(exclude_user=previous_user)

    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"Today's pick is <@{next_user}>!",
        blocks=build_picker_blocks(next_user)
    )

def lambda_handler(event, context):
    if event.get("source") in ["aws.events", "aws.scheduler"]:
        return run_sortes_pick()
    return slack_handler.handle(event, context)