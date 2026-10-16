terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  backend "s3" {
    # Backend parameters supplied via -backend-config in GitHub Actions
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. Package the Lambda code and dependencies staged by CI/CD
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build"
  output_path = "${path.module}/lambda.zip"
}

# 2. Execution Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "sortes_picker_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 3. Lambda Function
resource "aws_lambda_function" "sortes_picker" {
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  function_name    = "sortes-picker"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.11"
  memory_size      = 512
  timeout          = 10

  environment {
    variables = {
      SLACK_BOT_TOKEN      = var.slack_bot_token
      SLACK_SIGNING_SECRET = var.slack_signing_secret
      SLACK_CHANNEL_ID     = var.slack_channel_id
      USER_POOL            = var.user_pool
      DYNAMODB_TABLE       = aws_dynamodb_table.picker_pools.name
    }
  }
}

# 4. Lambda Function URL & Public Authorization Permission
resource "aws_lambda_function_url" "slack_url" {
  function_name      = aws_lambda_function.sortes_picker.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "allow_public_function_url" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.sortes_picker.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "allow_public_function_invoke" {
  statement_id  = "FunctionURLAllowPublicInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sortes_picker.function_name
  principal     = "*"
}

# 5. Scheduled Daily Pick Rule (UTC, Mon-Fri)
resource "aws_cloudwatch_event_rule" "daily_pick" {
  name                = "sortes-picker-daily"
  description         = "Trigger daily pick on weekdays"
  schedule_expression = "cron(30 9 ? * MON-FRI *)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_pick.name
  target_id = "SortesPickerDailyTrigger"
  arn       = aws_lambda_function.sortes_picker.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sortes_picker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_pick.arn
}

# 6. DynamoDB Table for Storing Channel Pools
resource "aws_dynamodb_table" "picker_pools" {
  name         = "slack-picker-pools"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "channel_id"

  attribute {
    name = "channel_id"
    type = "S"
  }
}

# 7. DynamoDB IAM Access Policy for Lambda
resource "aws_iam_policy" "lambda_dynamodb" {
  name        = "sortes_picker_dynamodb_policy"
  description = "Allows Lambda to read and update Slack user pools"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem"
        ]
        Resource = aws_dynamodb_table.picker_pools.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_dynamodb.arn
}