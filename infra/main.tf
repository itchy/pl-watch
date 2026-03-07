locals {
  lambda_zip_path = "${abspath(path.module)}/build/${var.lambda_function_name}.zip"
  pl_lambda_zip_path = "${abspath(path.module)}/build/${var.pl_lambda_function_name}.zip"
  pl_scraper_zip_path = "${abspath(path.module)}/build/${var.pl_scraper_function_name}.zip"
  lambda_sources = concat(
    [
      "${path.module}/../lambda_function.py",
      "${path.module}/../lambda_pl_function.py",
      "${path.module}/../lambda_scraper_function.py",
    ],
    [for file in fileset("${path.module}/../src", "**") : "${path.module}/../src/${file}"]
  )
  lambda_source_hash = sha256(join("", [for file in local.lambda_sources : filesha256(file)]))
  lambda_role_name = element(reverse(split("/", var.lambda_role_arn)), 0)
  pl_scraper_bucket = try(var.pl_scraper_environment["DATA_BUCKET"], "")
}

resource "terraform_data" "package_lambda" {
  triggers_replace = [
    local.lambda_source_hash,
  ]

  provisioner "local-exec" {
    command = "mkdir -p ${abspath(path.module)}/build && rm -f ${local.lambda_zip_path} && cd ${abspath(path.module)}/.. && zip -r ${local.lambda_zip_path} lambda_function.py src >/dev/null"
  }
}

resource "terraform_data" "package_pl_lambda" {
  count = var.enable_premier_league_lambda ? 1 : 0

  triggers_replace = [
    local.lambda_source_hash,
  ]

  provisioner "local-exec" {
    command = "mkdir -p ${abspath(path.module)}/build && rm -f ${local.pl_lambda_zip_path} && cd ${abspath(path.module)}/.. && zip -r ${local.pl_lambda_zip_path} lambda_pl_function.py src >/dev/null"
  }
}

resource "terraform_data" "package_pl_scraper_lambda" {
  count = var.enable_pl_scraper_lambda ? 1 : 0

  triggers_replace = [
    local.lambda_source_hash,
  ]

  provisioner "local-exec" {
    command = "mkdir -p ${abspath(path.module)}/build && rm -f ${local.pl_scraper_zip_path} && cd ${abspath(path.module)}/.. && zip -r ${local.pl_scraper_zip_path} lambda_scraper_function.py src >/dev/null"
  }
}

resource "aws_lambda_function" "next_f1_session" {
  function_name = var.lambda_function_name
  role          = var.lambda_role_arn
  runtime       = var.lambda_runtime
  handler       = var.lambda_handler
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  layers        = var.lambda_layers

  filename         = local.lambda_zip_path
  source_code_hash = base64encode(local.lambda_source_hash)

  environment {
    variables = var.lambda_environment
  }

  depends_on = [
    terraform_data.package_lambda,
  ]
}

resource "aws_lambda_function_url" "next_f1_session" {
  function_name      = aws_lambda_function.next_f1_session.function_name
  authorization_type = "NONE"
  invoke_mode        = "BUFFERED"
}

resource "aws_lambda_permission" "function_url_public" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.next_f1_session.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "pl_api_gateway_invoke" {
  statement_id  = "ApiGatewayInvokePlNextSessionManaged"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.next_f1_session.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:373892137535:${var.pl_api_gateway_id}/*/*/*"
}

resource "aws_lambda_function" "premier_league" {
  count = var.enable_premier_league_lambda ? 1 : 0

  function_name = var.pl_lambda_function_name
  role          = var.lambda_role_arn
  runtime       = var.lambda_runtime
  handler       = var.pl_lambda_handler
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  layers        = var.lambda_layers

  filename         = local.pl_lambda_zip_path
  source_code_hash = base64encode(local.lambda_source_hash)

  environment {
    variables = var.pl_lambda_environment
  }

  depends_on = [
    terraform_data.package_pl_lambda,
  ]
}

resource "aws_lambda_function_url" "premier_league" {
  count = var.enable_premier_league_lambda ? 1 : 0

  function_name      = aws_lambda_function.premier_league[0].function_name
  authorization_type = "NONE"
  invoke_mode        = "BUFFERED"
}

resource "aws_lambda_permission" "premier_league_function_url_public" {
  count = var.enable_premier_league_lambda ? 1 : 0

  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.premier_league[0].function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_iam_role_policy" "pl_scraper_s3_write" {
  count = var.enable_pl_scraper_lambda && local.pl_scraper_bucket != "" ? 1 : 0

  name = "pl-scraper-s3-write"
  role = local.lambda_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
        ]
        Resource = "arn:aws:s3:::${local.pl_scraper_bucket}/*"
      }
    ]
  })
}

resource "aws_lambda_function" "pl_scraper" {
  count = var.enable_pl_scraper_lambda ? 1 : 0

  function_name = var.pl_scraper_function_name
  role          = var.lambda_role_arn
  runtime       = var.lambda_runtime
  handler       = var.pl_scraper_handler
  timeout       = var.pl_scraper_timeout
  memory_size   = var.pl_scraper_memory_size

  filename         = local.pl_scraper_zip_path
  source_code_hash = base64encode(local.lambda_source_hash)

  environment {
    variables = var.pl_scraper_environment
  }

  depends_on = [
    terraform_data.package_pl_scraper_lambda,
    aws_iam_role_policy.pl_scraper_s3_write,
  ]
}

resource "aws_cloudwatch_event_rule" "pl_scraper_hourly" {
  count = var.enable_pl_scraper_lambda ? 1 : 0

  name                = "${var.pl_scraper_function_name}-schedule"
  description         = "Hourly refresh of PL snapshot data to S3"
  schedule_expression = var.pl_scraper_schedule_expression
}

resource "aws_cloudwatch_event_target" "pl_scraper_lambda" {
  count = var.enable_pl_scraper_lambda ? 1 : 0

  rule      = aws_cloudwatch_event_rule.pl_scraper_hourly[0].name
  target_id = "pl-snapshot-scraper"
  arn       = aws_lambda_function.pl_scraper[0].arn
}

resource "aws_lambda_permission" "allow_eventbridge_pl_scraper" {
  count = var.enable_pl_scraper_lambda ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridgePlScraper"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pl_scraper[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.pl_scraper_hourly[0].arn
}

resource "terraform_data" "sync_pl_cloudfront_origin" {
  count = var.enable_pl_cloudfront_origin_sync ? 1 : 0

  triggers_replace = [
    var.pl_cloudfront_distribution_id,
    var.pl_api_gateway_domain_name,
    var.pl_api_gateway_id,
    var.aws_profile,
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -euo pipefail
      TMP_IN="$(mktemp /tmp/pl-cf-XXXXXX.json)"
      TMP_OUT="$(mktemp /tmp/pl-cf-dist-XXXXXX.json)"
      AWS_PROFILE="${var.aws_profile}" aws cloudfront get-distribution-config --id "${var.pl_cloudfront_distribution_id}" --output json > "$TMP_IN"
      ETAG="$(jq -r '.ETag' "$TMP_IN")"
      jq '.DistributionConfig
        | .Origins.Items[0].DomainName = "${var.pl_api_gateway_domain_name}"
        | .Origins.Items[0].Id = "${var.pl_api_gateway_domain_name}"
        | .DefaultCacheBehavior.TargetOriginId = "${var.pl_api_gateway_domain_name}"
        | del(.DefaultCacheBehavior.OriginRequestPolicyId)' "$TMP_IN" > "$TMP_OUT"
      AWS_PROFILE="${var.aws_profile}" aws cloudfront update-distribution --id "${var.pl_cloudfront_distribution_id}" --if-match "$ETAG" --distribution-config "file://$TMP_OUT" >/dev/null
      rm -f "$TMP_IN" "$TMP_OUT"
    EOT
  }

  depends_on = [
    aws_lambda_permission.pl_api_gateway_invoke,
  ]
}
