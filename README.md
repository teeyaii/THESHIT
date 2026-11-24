# THESHIT
AI-powered research automation and statistical analysis engine.

## v0.2 — versioned synthetic codebook
Generic four-construct, 14-item Likert demo. Independent random fixtures, not actual responses or a validated questionnaire. No real-data input in this version.

## Run
Python 3.11+:
```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python research_demo.py
```
The generated outputs/SYNTHETIC_demo.json includes descriptive statistics, Cronbach's alpha, correlation, OLS and HC3 p-values. Retain negative, null and nonsignificant findings; never tune fixtures for desired findings.

## Governance
Public code only; keep participant data, unpublished documents, credentials and evidence in approved private storage. See AGENTS.md and docs/ROADMAP.md. A synthetic report is never research evidence. Human approval before merge and academic release.


The draft schema is in config/demo_codebook.json. Reports include its SHA-256 and data audit. See docs/MASTER_PLAN.md for release gates. Actual questionnaire wording and demographic coding are not verified or included.
