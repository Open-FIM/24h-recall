# OpenFIM 24h Recall

OpenFIM 24h Recall is a multi-study workflow for managing 24-hour dietary recalls using Intake24, OpenWebUI, PostgreSQL, and a lightweight Flask webhook.

The tool supports study-specific recall links using:

- participant ID
- study ID
- timepoint
- recall number
- attempt number

Example identity structure:

    P001:STUDY_A:0:1

where:

    participant_id = P001
    study_id = STUDY_A
    timepoint = 0
    recall_number = 1

## What this system does

1. Generates participant-facing Intake24 recall links.
2. Receives completed Intake24 recall callbacks.
3. Saves raw Intake24 recall JSON.
4. Saves nutrient totals.
5. Preserves repeated attempts instead of overwriting prior recalls.
6. Allows recall summaries to be retrieved through OpenWebUI.

## What this repository does not include

This repository does not include:

- participant data
- database dumps
- JWT secrets
- server credentials
- SMTP passwords
- protected health information
- Intake24 image archives
- proprietary food databases

## Core components

    pipelines/openfim_recall_pipeline.py
    webhook/webhook_receiver.py
    sql/create_recall_tables.sql

## Safety rule

Only share the generated participant-facing Intake24 link with participants.

Do not share internal webhook URLs, localhost URLs, Docker bridge URLs, admin URLs, or server-side routes.


## How to cite

If you use this repository, please cite it as:

Amaning-Kwarteng G., Marru H., Puranik, I., Krishnan G., Marru S., Krishnan S. OpenFIM 24h Recall: Intake24 workflow for multi-study 24-hour dietary recall collection with USDA/FNDDS import support. GitHub repository: https://github.com/Open-FIM/24h-recall

Suggested BibTeX:

```bibtex
@software{openfim_24h_recall,
  title = {OpenFIM 24h Recall: Intake24 workflow for multi-study 24-hour dietary recall collection with USDA/FNDDS import support},
  author = {LAmaning-Kwarteng G., Marru H., Puranik, I., Krishnan G., Marru S., Krishnan S},
  organization = {Open-FIM},
  url = {https://github.com/Open-FIM/24h-recall},
  year = {2026},
  note = {GitHub repository}
}
