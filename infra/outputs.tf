output "lambda_function_name" {
  value = aws_lambda_function.next_f1_session.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.next_f1_session.arn
}

output "lambda_function_url" {
  value = aws_lambda_function_url.next_f1_session.function_url
}

output "cloudfront_domain_name" {
  value = try(one(data.aws_cloudfront_distribution.f1_api[*].domain_name), null)
}

output "cloudfront_aliases" {
  value = try(one(data.aws_cloudfront_distribution.f1_api[*].aliases), null)
}

output "pl_lambda_function_name" {
  value = try(one(aws_lambda_function.premier_league[*].function_name), null)
}

output "pl_lambda_function_arn" {
  value = try(one(aws_lambda_function.premier_league[*].arn), null)
}

output "pl_lambda_function_url" {
  value = try(one(aws_lambda_function_url.premier_league[*].function_url), null)
}

output "pl_scraper_lambda_function_name" {
  value = try(one(aws_lambda_function.pl_scraper[*].function_name), null)
}

output "pl_scraper_lambda_function_arn" {
  value = try(one(aws_lambda_function.pl_scraper[*].arn), null)
}

output "pl_scraper_schedule_expression" {
  value = try(one(aws_cloudwatch_event_rule.pl_scraper_hourly[*].schedule_expression), null)
}
