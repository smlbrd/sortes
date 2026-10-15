variable "aws_region" {
  type        = string
  description = "Target AWS region"
  default     = "eu-west-2"
}

variable "slack_bot_token" {
  type        = string
  description = "Slack Bot OAuth Token (xoxb-...)"
  sensitive   = true
}

variable "slack_signing_secret" {
  type        = string
  description = "Slack App Signing Secret"
  sensitive   = true
}

variable "slack_channel_id" {
  type        = string
  description = "Slack target channel ID"
}

variable "user_pool" {
  type        = string
  description = "Comma-delimited Slack User IDs (e.g. U123,U456)"
}