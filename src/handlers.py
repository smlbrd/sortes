import json
import config
import db
import picker
import ui
from slack_sdk.errors import SlackApiError


def register_handlers(app):

    # -----------------------------------------------------------------------
    # Shared Helper: Open Create / Edit Modal
    # -----------------------------------------------------------------------
    def _open_pool_modal(body, client, logger, pool_override=None):
        channel_id = body.get("channel_id")
        trigger_id = body.get("trigger_id")
        pool_name = (pool_override or body.get("text", "")).strip().lower() or "default"

        try:
            tickets, _, _ = db.get_pool_data(channel_id, pool_name)
            current_members = list(tickets.keys())

            client.views_open(
                trigger_id=trigger_id,
                view=ui.build_pool_modal(channel_id, pool_name, current_members)
            )
        except SlackApiError as e:
            logger.error(f"Error opening pool modal: {e.response['error']}")
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user_id"],
                text=f"⚠️ Failed to open modal: `{e.response['error']}`"
            )

    # -----------------------------------------------------------------------
    # Slash Commands: Create & Edit
    # -----------------------------------------------------------------------
    @app.command("/create")
    def handle_create_command(ack, body, client, logger):
        ack()
        _open_pool_modal(body, client, logger)

    @app.command("/edit")
    def handle_edit_command(ack, body, client, logger):
        ack()
        _open_pool_modal(body, client, logger)

    # Button click handler if someone clicked 'Create Pool' from an empty pick error
    @app.action("open_create_modal")
    def handle_open_create_modal_button(ack, body, client, logger):
        ack()
        pool_name = body.get("actions", [{}])[0].get("value", "default")
        _open_pool_modal(body, client, logger, pool_override=pool_name)

    # -----------------------------------------------------------------------
    # Modal Submission: Save / Create Pool
    # -----------------------------------------------------------------------
    @app.view("save_pool_modal")
    def handle_save_pool_modal(ack, body, client):
        ack()
        meta = json.loads(body["view"]["private_metadata"])
        channel_id = meta["channel_id"]
        pool_name = meta["pool_name"]
        is_new = meta.get("is_new", False)

        state_values = body["view"]["state"]["values"]
        selected_users = state_values["pool_input_block"]["pool_users_select"]["selected_users"]

        count = picker.sync_pool_members(channel_id, pool_name, selected_users)

        action_word = "created" if is_new else "updated"
        client.chat_postEphemeral(
            channel=channel_id,
            user=body["user"]["id"],
            text=f"✅ Pool *{pool_name}* {action_word}! Now contains *{count}* members."
        )

    # -----------------------------------------------------------------------
    # Pool Deletion Flow
    # -----------------------------------------------------------------------
    @app.command("/delete")
    def handle_delete_command(ack, body, client):
        ack()
        channel_id = body.get("channel_id")
        pool_name = body.get("text", "").strip().lower()

        if not pool_name:
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user_id"],
                text="⚠️ Please specify the pool to delete. Example: `/delete standup`"
            )
            return

        pools = db.get_channel_pools(channel_id)
        if pool_name not in pools:
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user_id"],
                text=f"⚠️ Pool `{pool_name}` does not exist in this channel."
            )
            return

        client.views_open(
            trigger_id=body["trigger_id"],
            view=ui.build_delete_confirm_modal(channel_id, pool_name)
        )

    @app.action("initiate_delete_pool_from_modal")
    def handle_initiate_delete_modal(ack, body, client):
        ack()
        payload = json.loads(body.get("actions", [{}])[0].get("value"))
        channel_id = payload["channel_id"]
        pool_name = payload["pool_name"]

        client.views_push(
            trigger_id=body["trigger_id"],
            view=ui.build_delete_confirm_modal(channel_id, pool_name)
        )

    @app.view("confirm_delete_pool_modal")
    def handle_confirm_delete_pool_modal(ack, body, client):
        ack(response_action="clear")

        meta = json.loads(body["view"]["private_metadata"])
        channel_id = meta["channel_id"]
        pool_name = meta["pool_name"]

        success = db.delete_pool(channel_id, pool_name)
        if success:
            client.chat_postEphemeral(
                channel=channel_id,
                user=body["user"]["id"],
                text=f"🗑️ Pool *{pool_name}* has been permanently deleted."
            )

    # -----------------------------------------------------------------------
    # Selection: /pick Command
    # -----------------------------------------------------------------------
    @app.command("/pick")
    def handle_pick_command(ack, body, client):
        ack()
        channel_id = body.get("channel_id")
        pool_name = body.get("text", "").strip().lower() or "default"

        user = picker.select_and_update_pool(channel_id=channel_id, pool_name=pool_name)
        if user == "unknown":