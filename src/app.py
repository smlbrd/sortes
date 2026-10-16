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
    if event.get("source") in ["aws.events", "aws.scheduler"]:
        return trigger_scheduled_pick(app)
    return slack_handler.handle(event, context)