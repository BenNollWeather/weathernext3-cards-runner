# WeatherNext 3 storm impact card runner

Renders storm impact cards (light mode, 3x2) from the WeatherNext 3 ensemble
on Google DeepMind's [Weather Lab](https://deepmind.google.com/science/weatherlab)
and publishes them to Amazon S3 whenever a new WNV3 run is posted.

Each card shows, for one storm or possible new storm: member tracks colored by
the regional intensity scale, the chance of gale/tropical-storm-force and
hurricane/typhoon-force winds by country with likely timing, the chance of
reaching the region's headline category, and the range of peak winds.

## Published output

- Viewer page: https://bennollweather.s3.amazonaws.com/climate_imagery/weathernext3/index.html
- Current card list: https://bennollweather.s3.amazonaws.com/climate_imagery/weathernext3/latest.json

## How it works

The card code lives in the notebook (`notebook/weathernext3_cyclones.ipynb`).
`scripts/run_cards.py` runs only the cells the cards need, with these settings
forced: light mode, 3x2 layout, a disposable working folder, no inline display.

Each run of `bin/run`:

1. Finds the newest WNV3 run on Weather Lab. If it already appears in the public
   `latest.json`, it stops.
2. Renders the cards.
3. Uploads them to a fixed S3 folder (`.../weathernext3/cards/`; the same storm
   keeps the same file name), then removes cards left from the previous run.
4. Updates `latest.json`, the viewer page (`web/index.html`) and a status JSON.

```bash
bash bin/run --no-upload   # render only; print what would be uploaded
bash bin/run               # render + upload if there is a new run
bash bin/run --force       # redo the newest run
```

Settings are in `config/settings.env`; environment variables override them.

## Scheduling: GitHub Actions started by AWS EventBridge

GitHub's scheduled (cron) workflows can start hours late, so
`.github/workflows/cards.yml` is started on time by an AWS EventBridge rule
calling the GitHub API (`workflow_dispatch`). GitHub's own cron (every 3 hours)
is only a backup.

Setup:

1. Repository secret `AWS_ROLE_ARN`: an IAM role that GitHub Actions can assume
   through OpenID Connect, allowed to write to the S3 output prefix. Restrict its
   trust policy to this repository's `main` branch.
2. A fine-grained GitHub token with **Actions: Read and write** on this
   repository, stored by deploying `aws/eventbridge-github-dispatch.yaml`
   (zsh shown; it prompts for the token without echoing it):

```bash
read -rs "GH_TOKEN?GitHub token: " && echo && \
aws cloudformation deploy --region us-east-1 \
  --stack-name weathernext3-cards-dispatch \
  --template-file aws/eventbridge-github-dispatch.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides GitHubToken="$GH_TOKEN"; unset GH_TOKEN
```

The template can be deployed again for other workflows (different stack name,
`Repository`, `WorkflowFile`, `ScheduleExpression`, `RuleName`) reusing the
connection through `ExistingConnectionArn`.

## Updating the notebook

Edit the working notebook, then copy it in (outputs stripped) and push:

```bash
bash bin/sync-notebook /path/to/weathernext3_cyclones.ipynb
git add notebook && git commit -m "Update notebook" && git push
```

## Running locally (optional)

`bin/run` also works on a workstation (set `PYTHON_CMD`, `NOTEBOOK_PATH` and an
AWS profile in `config/settings.env`). `launchd/` has a template for an hourly
macOS job; edit its paths before installing it.

## Fonts and data

- Cards use **Libre Franklin** from
  [impallari/Libre-Franklin](https://github.com/impallari/Libre-Franklin),
  SIL Open Font License 1.1 (`assets/fonts/OFL.txt`). The runner substitutes it
  for the Franklin ITC file names the notebook uses.
- Forecast data: Google DeepMind WeatherNext 3 via Weather Lab. Storm names and
  intensities: NHC and JTWC. Season comparisons: NHC/JTWC working best tracks
  (NCAR mirror), with NOAA IBTrACS as a fallback. Map data: Natural Earth.
