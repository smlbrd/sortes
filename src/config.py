import os
import boto3

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
DEFAULT_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "")
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "slack-picker-pools")
FALLBACK_USER_POOL = [
    uid.strip()
    for uid in os.environ.get("USER_POOL", "").split(",")
    if uid.strip()
]

dynamodb = boto3.resource("dynamodb")
pool_table = dynamodb.Table(DYNAMODB_TABLE_NAME)