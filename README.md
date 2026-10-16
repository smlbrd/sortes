# Sortes

A serverless Slack bot running on AWS Lambda that selects team members for duties (standups, PR triage, chores) using self-balancing weighted sampling and strict consecutive-pick prevention.

## Features

- Weighted Fairness: Every round a user is not picked, they gain +1 ticket. When picked, their balance resets to 1 ticket.
- No Back-to-Back Picks: The previous round's winner is strictly excluded from the next draw ($P = 0$).
- Interactive Controls:
  - Spin Again 🎲: Rerolls the pick and refunds tickets to the skipped user so they aren't penalized.
  - I Volunteer 🙋: Allows someone to claim the duty, resetting their tickets to 1 and refunding the original pick.
- Pool Management: /edit-pool slash command opens a modal to add/remove channel members. New members are initialised with the pool's average ticket balance.
- Scheduled Triggers: Supports AWS EventBridge / CloudWatch cron triggers for automated daily draws.

## Project Structure

```
src/
├── app.py          # Lambda entrypoint routing Slack webhooks & EventBridge crons
├── config.py       # Environment variables & Boto3 client initialization
├── db.py           # DynamoDB CRUD operations and type conversions
├── handlers.py     # Slack commands, action button handlers, and modal callbacks
├── picker.py       # Core selection logic, ticket adjustments, and state syncing
├── ui.py           # Block Kit message and modal definitions
└── simulate.py     # Standalone Monte Carlo test runner (no dependencies)
```

## Local Testing

Verify the selection logic, gap distribution, and zero-consecutive-pick guarantees without needing AWS credentials or Slack tokens:

```shell
python3 src/simulate.py
```