# plwatch

Template repo for a Premier League watchface API endpoint.

## Current status

- Primary Lambda entrypoint: `/Users/scott/code/pl/lambda_function.py`
- Primary handler: `/Users/scott/code/pl/src/f1watch/api/premier_league_handler.py`
- Returns a template JSON payload designed to be replaced with real PL fixtures/standings data.

## Local run

```bash
python -c "from src.f1watch.api.premier_league_handler import get_payload; import json; print(json.dumps(get_payload()))"
```

## API usage

Example:

```bash
curl "https://pl.itchy7.com/"
```

## Terraform (IaC)

Infrastructure config lives in:

- `/Users/scott/code/pl/infra`

Use:

```bash
cd /Users/scott/code/pl/infra
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

## Notes

- This repo was cloned from the F1 project as a starting template.
- Package/module paths still use `f1watch` for now; you can rename later if you want a clean PL namespace.
