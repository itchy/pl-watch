# Terraform for PL Watch

This directory manages AWS infrastructure for the PL watchface endpoint.

## What is managed

- Primary Lambda function (default: `next-pl-session`)
- Primary Lambda Function URL + public invoke permission
- Scheduled scraper Lambda (default: `pl-snapshot-scraper`)
- EventBridge schedule for hourly snapshot refresh (`rate(1 hour)`)
- Optional secondary Lambda stack (`enable_premier_league_lambda`)
- Lambda packaging from:
  - `/Users/scott/code/pl/lambda_function.py`
  - `/Users/scott/code/pl/lambda_pl_function.py`
  - `/Users/scott/code/pl/lambda_scraper_function.py`
  - `/Users/scott/code/pl/src/`

## Prerequisites

- Terraform >= 1.6
- AWS credentials/profile (`f1-sso` by default)
- `zip` command available locally

## New environment workflow

```bash
cd /Users/scott/code/pl/infra
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

## Import workflow (if resource already exists)

```bash
cd /Users/scott/code/pl/infra
./scripts/import_existing.sh
```

## CloudFront

`cloudfront_distribution_id` is optional.

- Set it to `""` to skip CloudFront lookup.
- Set it to a real distribution ID to surface CloudFront outputs.
