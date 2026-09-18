# Video Tutorial
https://arizona.box.com/s/7bj0ck0gmr0jlhzwlp60yorn8gwqd98b

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


## Resources showing use of Intake24 across countries
## Validation
Foster E, Lee C, Imamura F, Hollidge SE, Westgate KL, Venables MC, Poliakov I, Rowland MK, Osadchiy T, Bradley JC, Simpson EL, Adamson AJ, Olivier P, Wareham N, Forouhi NG, Brage S. Validity and reliability of an online self-report 24-h dietary recall method (Intake24): a doubly labelled water study and repeated-measures analysis. J Nutr Sci. 2019 Aug 30;8:e29. doi: 10.1017/jns.2019.20. Erratum in: J Nutr Sci. 2019 Dec 19;8:e41. doi: 10.1017/jns.2019.38. PMID: 31501691; PMCID: PMC6722486.

Whitton, C., et al. "Intake24 in Australia: evaluating the criterion validity of a self-administered 24-hour recall using a controlled feeding study in Western Australia adults." Proceedings of the Nutrition Society 82.OCE2 (2023): E84.

Nik Mohd Fakhruddin NNI, Rajasegaram ST, Osman NN, Foster E, Ng CM, Abu Hassan Shaari NS, McCaffrey T, Prawira C, Olivier P, Watterson J, Ramadas A. A Digital Dietary Assessment Tool for a Multicultural Population (Intake24 Malaysia): Protocol for a Development and Validation Study. JMIR Res Protoc. 2026 Aug 4;15:e90106. doi: 10.2196/90106. PMID: 42550985; PMCID: PMC13436792.

## Adopted to different countries
Mackay S, Haliburton C, Follong B, Lister C, Gibbs M, Ni Mhurchu C. Developing a food list for a new 24-h dietary recall tool for New Zealand. Nutr Diet. 2025 Jun;82(3):292-300. doi: 10.1111/1747-0080.70014. PMID: 40518948; PMCID: PMC12168050.

McCaffrey, Tracy; Foster, Emma; Ng, Heidi; Ivaturi, Anu; Abdulgalimov, Dinislam; Poliakov, Ivan; et al. (2025). Intake24-AUS Food List. Monash University. Dataset. https://doi.org/10.26180/29664170.v1

Bhagtani D, Amoutzopoulos B, Steer T, Collins D, Abraham S, Holmes BA, Rai BK, Pradeepa R, Mahmood S, Shamim AA, Mathur P, Athauda L, De Silva L, Khawaja KI, Jha V, Kasturiratne A, Katulanda P, Mridha MK, Anjana RM, Chambers JC, Page P, Forouhi NG. The Adaptation, Implementation, and Performance Evaluation of Intake24, a Digital 24-h Dietary Recall Tool for South Asian Populations: The South Asia Biobank. Curr Dev Nutr. 2025 Jan 16;9(2):104543. doi: 10.1016/j.cdnut.2025.104543. PMID: 39991134; PMCID: PMC11847516.

Ali HI, Akkad L, Al Hassan MAT, Almasri RS, Al Marzooqi H, Afifi HS, Shehata MG and Bataineh MF (2026) Design and usability of Abu Dhabi Food Intake24: a culturally adapted digital 24-hour dietary recall for the United Arab Emirates. Front. Nutr. 13:1866000. doi: 10.3389/fnut.2026.1866000

## How to cite

If you use this repository, please cite it as:

Amaning-Kwarteng G., Marru H., Puranik, I., Krishnan G., Marru S., Krishnan S. OpenFIM 24h Recall: Intake24 workflow for multi-study 24-hour dietary recall collection with USDA/FNDDS import support. GitHub repository: https://github.com/Open-FIM/24h-recall

[![DOI](https://zenodo.org/badge/1351604264.svg)](https://doi.org/10.5281/zenodo.22699801)

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

