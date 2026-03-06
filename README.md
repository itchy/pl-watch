# plwatch

Premier League watchface API endpoint.

## Current status

- Primary Lambda entrypoint: `/Users/scott/code/pl/lambda_function.py`
- Primary handler: `/Users/scott/code/pl/src/f1watch/api/premier_league_handler.py`
- Returns per-team data for:
  - last result (`W`/`L`/`D`)
  - last opponent
  - next opponent
  - next kickoff time (UTC + localized via `tz`)

## Data pipeline

Data source APIs:

- `https://fantasy.premierleague.com/api/bootstrap-static/`
- `https://fantasy.premierleague.com/api/fixtures/`

Scraper module:

- `/Users/scott/code/pl/src/f1watch/scrapers/premier_league.py`

Generated file:

- `<year>_pl_team_snapshot.json`

## Local run (handler)

```bash
DATA_SOURCE=local PL_TEAM_DATA_KEY=/Users/scott/code/pl/2026_pl_team_snapshot.json \
python3 -c "from src.f1watch.api.premier_league_handler import get_payload; import json; print(json.dumps(get_payload(), indent=2))"
```

## API usage

Example:

```bash
curl "https://pl.itchy7.com/"
curl "https://pl.itchy7.com/?tz=America/Los_Angeles"
```

## Scrape + upload

```bash
cd /Users/scott/code/pl
./scripts/update_data.sh
```

Dry-run:

```bash
./scripts/scrape_and_upload.sh --year 2026 --bucket f1-data-00000000 --dry-run
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
