import os
import sys

# Ensure Python loads sibling modules from this file's directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

import config
from handlers import register_handlers, trigger_scheduled_pick

app = App(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET,
    process_before_response=True
)

register_handlers(app)
slack_handler = SlackRequestHandler(app=app)

def lambda_handler(event, context):
    # Route scheduled AWS EventBridge / CloudWatch cron triggers
    if event.get("source") in ["aws.events", "aws.scheduler"]:
        pool_name = event.get("pool", "default")
        channel_id = event.get("channel_id")
        return trigger_scheduled_pick(app, pool_name=pool_name, channel_id=channel_id)

    return slack_handler.handle(event, context)