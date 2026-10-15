output "slack_interactivity_request_url" {
  description = "Slack Interactivity Request URL"
  value       = aws_lambda_function_url.slack_url.function_url
}