# Sortes

A serverless Slack bot running on AWS Lambda that selects team members for duties (standups, PR triage, chores) using self-balancing weighted sampling, strict consecutive-pick prevention, and multi-pool support.

## Features

- **Weighted Fairness**: Every round a user is not picked, they gain +1 ticket. When picked, their balance resets to 1 ticket.
- **No Back-to-Back Picks**: The previous round's winner is strictly excluded from the next draw ($P = 0$).
- **Multi-Pool Support**: Maintain multiple distinct rotation pools within the same channel (e.g., `standup`, `triage`, `demo`).
- **Interactive Controls**:
  - **Spin Again 🎲**: Rerolls the pick and refunds tickets to the skipped user so they aren't penalized.
  - **I Volunteer 🙋**: Allows someone to claim the duty, resetting their tickets to 1 and refunding the original pick.
- **Visual Pool Management**: Interactive Block Kit modals to create, edit, or delete pools and inspect pick leaderboards.
- **Scheduled Triggers**: Automated daily/weekly draws via Amazon EventBridge or CloudWatch cron triggers.

## Slash Commands

All commands accept an optional `[pool_name]` argument (defaults to `"default"` if omitted):

| Command | Description | Example |
| :--- | :--- | :--- |
| `/pick [pool]` | Draws a winner from the pool and announces it to the channel. | `/pick standup` |
| `/create [pool]` | Opens a modal to initialize a new pool with selected channel members. | `/create triage` |
| `/edit [pool]` | Opens a modal to add/remove users or delete an existing pool. | `/edit standup` |
| `/delete [pool]` | Opens a confirmation modal to permanently delete a pool. | `/delete chores` |
| `/stats [pool]` | Shows pool leaderboard and ticket weights. If no pool is specified, summarizes all channel pools. | `/stats` |

## Environment Variables

| Variable | Required | Description |
| :--- | :--- | :--- |
| `SLACK_BOT_TOKEN` | Yes | Slack bot user OAuth token (`xoxb-...`). |
| `SLACK_SIGNING_SECRET` | Yes | Slack app signing secret. |
| `SLACK_CHANNEL_ID` | No | Default fallback channel ID if not passed by the caller. |
| `DYNAMODB_TABLE` | No | DynamoDB table name (defaults to `slack-picker-pools`). |
| `USER_POOL` | No | Comma-separated Slack User IDs used as in-memory fallback if DynamoDB is unavailable. |