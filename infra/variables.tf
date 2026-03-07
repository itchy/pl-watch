variable "aws_region" {
  description = "AWS region for Lambda and related resources."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name used by Terraform."
  type        = string
  default     = "f1-sso"
}

variable "lambda_function_name" {
  description = "Existing Lambda function name."
  type        = string
  default     = "next-pl-session"
}

variable "lambda_role_arn" {
  description = "IAM role ARN already used by Lambda."
  type        = string
  default     = "arn:aws:iam::373892137535:role/service-role/next-f1-session-role-m81fwq00"
}

variable "lambda_handler" {
  description = "Lambda handler entrypoint."
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "lambda_runtime" {
  description = "Lambda runtime."
  type        = string
  default     = "python3.13"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 10
}

variable "lambda_memory_size" {
  description = "Lambda memory in MB."
  type        = number
  default     = 128
}

variable "lambda_layers" {
  description = "Lambda layer ARNs."
  type        = list(string)
  default = [
    "arn:aws:lambda:us-east-1:373892137535:layer:rfc3339:1",
  ]
}

variable "lambda_environment" {
  description = "Lambda environment variables."
  type        = map(string)
  default = {
    DATA_SOURCE      = "s3"
    DATA_BUCKET      = "f1-data-00000000"
    F1_YEAR          = "2026"
    PL_TEAM_DATA_KEY = "2026_pl_team_snapshot.json"
    LOCAL_TZ         = "America/Denver"
  }
}

variable "cloudfront_distribution_id" {
  description = "Existing CloudFront distribution ID for the API domain (optional)."
  type        = string
  default     = ""
}

variable "enable_premier_league_lambda" {
  description = "Create a second Lambda + Function URL for Premier League data."
  type        = bool
  default     = false
}

variable "pl_lambda_function_name" {
  description = "Premier League Lambda function name."
  type        = string
  default     = "next-pl-session-alt"
}

variable "pl_lambda_handler" {
  description = "Premier League Lambda handler entrypoint."
  type        = string
  default     = "lambda_pl_function.lambda_handler"
}

variable "pl_lambda_environment" {
  description = "Premier League Lambda environment variables."
  type        = map(string)
  default     = {}
}

variable "enable_pl_scraper_lambda" {
  description = "Create scheduled scraper Lambda to refresh PL snapshot in S3."
  type        = bool
  default     = true
}

variable "pl_scraper_function_name" {
  description = "Scheduled PL scraper Lambda function name."
  type        = string
  default     = "pl-snapshot-scraper"
}

variable "pl_scraper_handler" {
  description = "Scheduled PL scraper Lambda handler entrypoint."
  type        = string
  default     = "lambda_scraper_function.lambda_handler"
}

variable "pl_scraper_timeout" {
  description = "Scheduled PL scraper Lambda timeout in seconds."
  type        = number
  default     = 30
}

variable "pl_scraper_memory_size" {
  description = "Scheduled PL scraper Lambda memory in MB."
  type        = number
  default     = 256
}

variable "pl_scraper_schedule_expression" {
  description = "EventBridge schedule expression for PL scraper refresh."
  type        = string
  default     = "rate(1 hour)"
}

variable "pl_scraper_environment" {
  description = "Scheduled PL scraper Lambda environment variables."
  type        = map(string)
  default = {
    DATA_BUCKET      = "f1-data-00000000"
    F1_YEAR          = "2026"
    PL_TEAM_DATA_KEY = "2026_pl_team_snapshot.json"
  }
}

variable "pl_api_gateway_id" {
  description = "Existing API Gateway HTTP API ID used by pl.itchy7.com."
  type        = string
  default     = "he8mfyvbn6"
}

variable "pl_api_gateway_domain_name" {
  description = "API Gateway domain name used as CloudFront origin for pl.itchy7.com."
  type        = string
  default     = "he8mfyvbn6.execute-api.us-east-1.amazonaws.com"
}

variable "pl_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for pl.itchy7.com."
  type        = string
  default     = "E19TSLEXYXI6FI"
}

variable "enable_pl_cloudfront_origin_sync" {
  description = "Enforce CloudFront origin target for pl.itchy7.com during terraform apply."
  type        = bool
  default     = true
}
