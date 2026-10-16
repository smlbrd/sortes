import json
import config
import db
import picker
import ui

def register_handlers(app):

    @app.command("/edit-pool")
    def handle_edit_pool_command(ack, body, client):
        ack()
        channel_id = body["channel_id"]
        tickets, _ = db.get_channel_state(channel_id)
        current_members = list(tickets.keys())

        client.views_open(
            trigger_id=body["trigger_id"],
            view=ui.build_edit_pool_modal(channel_id, current_members)
        )

    @app.view("save_pool_modal")
    def handle_save_pool_modal(ack, body, client):
        ack()
        channel_id = body["view"]["private_metadata"]
        state_values = body["view"]["state"]["values"]
        selected_users = state_values["pool_input_block"]["pool_users_select"]["selected_users"]

        member_count = picker.sync_pool_members(channel_id, selected_users)

        client.chat_postEphemeral(
            channel=channel_id,
            user=body["user"]["id"],
            text=f"✅ Updated! Pool now contains *{member_count}* members."
        )

    @app.action("spin_again")
    def handle_spin_again(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        rejected_user = body.get("actions", [{}])[0].get("value")

        # Restore tickets to the skipped user so they aren't penalized
        picker.refund_skipped_user(channel_id, rejected_user)

        # Draw a new user, actively excluding the skipped user
        next_user = picker.select_and_update_pool(
            channel_id=channel_id,
            exclude_user=rejected_user
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"~Today's pick is <@{rejected_user}>!~",
            blocks=ui.build_struck_through_blocks(rejected_user)
        )

        client.chat_postMessage(
            channel=channel_id,
            text=f"Today's pick is <@{next_user}>!",
            blocks=ui.build_picker_blocks(next_user)
        )

    @app.action("volunteer")
    def handle_volunteer(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        volunteer_user = body["user"]["id"]
        previous_user = body.get("actions", [{}])[0].get("value")

        # Restore tickets to the superseded user
        picker.refund_skipped_user(channel_id, previous_user)

        # Force pick the volunteer
        picker.select_and_update_pool(
            channel_id=channel_id,
            explicit_user=volunteer_user
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"~Today's pick is <@{previous_user}>!~",
            blocks=ui.build_struck_through_blocks(previous_user)
        )

        client.chat_postMessage(
            channel=channel_id,
            text=f"🎯 <@{volunteer_user}> bravely volunteered!",
            blocks=ui.build_picker_blocks(volunteer_user)
        )


def trigger_scheduled_pick(app) -> dict:
    """Executes the cron pick triggered via AWS EventBridge/CloudWatch."""
    channel = config.DEFAULT_CHANNEL_ID
    user = picker.select_and_update_pool(channel_id=channel)
    app.client.chat_postMessage(
        channel=channel,
        text=f"Today's pick is <@{user}>!",
        blocks=ui.build_picker_blocks(user)
    )
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "pick_posted", "user": user})
    }