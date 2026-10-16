import json
import config
import db
import picker
import ui
from slack_sdk.errors import SlackApiError

def register_handlers(app):

    @app.command("/edit-pool")
    def handle_edit_pool_command(ack, body, client, logger):
        ack()
        channel_id = body.get("channel_id")
        trigger_id = body.get("trigger_id")
        pool_name = body.get("text", "").strip().lower() or "default"

        try:
            tickets, _, _ = db.get_pool_data(channel_id, pool_name)
            current_members = list(tickets.keys())

            client.views_open(
                trigger_id=trigger_id,
                view=ui.build_edit_pool_modal(channel_id, pool_name, current_members)
            )
        except SlackApiError as e:
            logger.error(f"Error opening modal: {e.response['error']}")
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user_id"],
                text=f"⚠️ Failed to open modal: `{e.response['error']}`"
            )

    @app.command("/pick")
    def handle_pick_command(ack, body, client):
        ack()
        channel_id = body.get("channel_id")
        pool_name = body.get("text", "").strip().lower() or "default"

        user = picker.select_and_update_pool(channel_id=channel_id, pool_name=pool_name)
        if user == "unknown":
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user_id"],
                text=f"⚠️ Pool `{pool_name}` is empty. Run `/edit-pool {pool_name}` to add team members."
            )
            return

        client.chat_postMessage(
            channel=channel_id,
            text=f"Today's pick is <@{user}>!",
            blocks=ui.build_picker_blocks(user, pool_name=pool_name)
        )

    @app.command("/sortes-stats")
    def handle_sortes_stats(ack, body, client):
        ack()
        channel_id = body.get("channel_id")
        pool_name = body.get("text", "").strip().lower()
        pools = db.get_channel_pools(channel_id)

        # Overview of all pools
        if not pool_name:
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user_id"],
                blocks=ui.build_all_pools_overview_blocks(pools)
            )
            return

        # Specific pool leaderboard
        if pool_name not in pools:
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user_id"],
                text=f"⚠️ Pool `{pool_name}` not found in this channel. Run `/sortes-stats` to see available pools."
            )
            return

        pool_data = pools[pool_name]
        blocks = ui.build_pool_leaderboard_blocks(
            pool_name=pool_name,
            tickets=pool_data["tickets"],
            picks_count=pool_data["picks_count"],
            last_picked=pool_data["last_picked"]
        )
        client.chat_postEphemeral(channel=channel_id, user=body["user_id"], blocks=blocks)

    @app.view("save_pool_modal")
    def handle_save_pool_modal(ack, body, client):
        ack()
        meta = json.loads(body["view"]["private_metadata"])
        channel_id = meta["channel_id"]
        pool_name = meta["pool_name"]

        state_values = body["view"]["state"]["values"]
        selected_users = state_values["pool_input_block"]["pool_users_select"]["selected_users"]

        count = picker.sync_pool_members(channel_id, pool_name, selected_users)

        client.chat_postEphemeral(
            channel=channel_id,
            user=body["user"]["id"],
            text=f"✅ Pool *{pool_name}* updated! Contains *{count}* members."
        )

    @app.action("spin_again")
    def handle_spin_again(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        payload = json.loads(body.get("actions", [{}])[0].get("value"))
        pool_name = payload.get("pool", "default")
        rejected_user = payload.get("user")

        picker.refund_skipped_user(channel_id, pool_name, rejected_user)
        next_user = picker.select_and_update_pool(
            channel_id=channel_id,
            pool_name=pool_name,
            exclude_user=rejected_user
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"~Today's pick is <@{rejected_user}>!~",
            blocks=ui.build_struck_through_blocks(rejected_user, pool_name)
        )
        client.chat_postMessage(
            channel=channel_id,
            text=f"Today's pick is <@{next_user}>!",
            blocks=ui.build_picker_blocks(next_user, pool_name)
        )

    @app.action("volunteer")
    def handle_volunteer(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        volunteer_user = body["user"]["id"]

        payload = json.loads(body.get("actions", [{}])[0].get("value"))
        pool_name = payload.get("pool", "default")
        previous_user = payload.get("user")

        picker.refund_skipped_user(channel_id, pool_name, previous_user)
        picker.select_and_update_pool(
            channel_id=channel_id,
            pool_name=pool_name,
            explicit_user=volunteer_user
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"~Today's pick is <@{previous_user}>!~",
            blocks=ui.build_struck_through_blocks(previous_user, pool_name)
        )
        client.chat_postMessage(
            channel=channel_id,
            text=f"🎯 <@{volunteer_user}> bravely volunteered for *{pool_name}*!",
            blocks=ui.build_picker_blocks(volunteer_user, pool_name)
        )


def trigger_scheduled_pick(app, pool_name: str = "default", channel_id: str | None = None) -> dict:
    channel = channel_id or config.DEFAULT_CHANNEL_ID
    user = picker.select_and_update_pool(channel_id=channel, pool_name=pool_name)

    if user != "unknown":
        app.client.chat_postMessage(
            channel=channel,
            text=f"Today's pick is <@{user}>!",
            blocks=ui.build_picker_blocks(user, pool_name=pool_name)
        )

    return {"statusCode": 200, "body": json.dumps({"status": "pick_posted", "user": user, "pool": pool_name})}