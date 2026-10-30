# Lead Intelligence System - Testing Guide

This guide follows the phases in [WORKFLOW_PLAN.md](./WORKFLOW_PLAN.md). Commands use Windows PowerShell and assume the terminal starts in the repository root.

## Current alignment status

Phase 1-3 fixes remain in place. Phase 4 now sends deterministic rubric results with stable per-run lead IDs and accepts explanation/review-note fields only; `--batch-size` overrides the config value, invalid/partial responses get a strict-prompt retry, and failures are surfaced per lead. Phase 5 produces first-touch drafts for QUALIFIED leads only, includes them in per-lead report details, and avoids fabricated reference-customer claims. Automated tests use mocked providers; live API credentials and network behavior still need an optional manual smoke test.

## Latest Phase 1-3 verification (2026-10-30)

Run against the updated project with Python 3.13.14:

| Phase | Result | Observed evidence |
|---|---|---|
| 1 - Setup | PASS | Required files and dependency imports are present; `.env` is ignored. |
| 2 - Rubric | PASS | Five factor weights total 1.0; config thresholds are 7.5/5.0; score outputs are 1-10 and decisions use the unrounded score. |
| 3 - Data pipeline | PASS | Deterministic CLI runs completed for training/testing/full-scale datasets (30/20/100 leads). The missing-company edge case is REVIEW and flagged, every REVIEW record is flagged, and the priority queue contains qualified leads only. |
| Unit tests | PASS | Includes mocked Phase 4 provider and Phase 5 outreach/report checks. |

Deterministic CLI checks used `--no-llm`; no live API requests were made. Generated verification reports were written to the system temporary directory.

## Before testing

From the repository root:

```powershell
Set-Location .\lead-qualifier
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -c "import pandas, yaml, requests, tenacity, dotenv, groq; print('Required imports OK')"
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Use the project dependencies in the selected Jupyter kernel as well. The dashboard additionally needs `matplotlib` and `seaborn`. Keep the LLM API key in `.env`; do not commit it.

## Phase 1 - Project setup and environment

Check the planned files and package layout:

```powershell
$required = @(
  'main.py', 'config.yaml', 'requirements.txt', 'README.md',
  '.env.example', '.gitignore', 'leads.csv',
  'utils\__init__.py', 'utils\models.py', 'utils\data_loader.py',
  'utils\rubric_engine.py', 'utils\llm_client.py',
  'utils\message_generator.py', 'utils\report_builder.py',
  'tests\__init__.py', 'tests\test_rubric.py',
  'tests\test_data_validation.py', 'tests\test_edge_cases.py',
  'tests\test_phase4_5.py', 'tests\test_phase6_reports.py'
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) { throw "Missing planned files: $($missing -join ', ')" }
```

Verify dependencies and that `.env` is ignored:

```powershell
.\venv\Scripts\python.exe -c "import pandas, yaml, requests, tenacity, dotenv, groq; print('Dependencies OK')"
git check-ignore .env
Get-Content .env.example
```

Pass when required files/imports are present and `.env` is ignored. Do not require a clean Git worktree as a project test.

## Phase 2 - Qualification rubric

Check the configured factor count, weights, and plan thresholds:

```powershell
.\venv\Scripts\python.exe -c "import math, yaml; c=yaml.safe_load(open('config.yaml', encoding='utf-8')); r=c['rubric']; t=c['thresholds']; assert 3 <= len(r) <= 5, len(r); assert math.isclose(sum(x['weight'] for x in r.values()), 1.0, abs_tol=1e-9); assert t['qualified'] == 7.5 and t['review'] == 5.0, t; print('Rubric and thresholds match the workflow plan')"
```

Check the rubric implementation with a fixed reference date and confirm five factor scores, a 1-10 total, and a decision/priority consistent with the configured thresholds:

```powershell
.\venv\Scripts\python.exe -c "from datetime import date; from utils.data_loader import load_leads; from utils.rubric_engine import load_rubric, score_lead; leads=load_leads('..\leads_training.csv'); r=load_rubric('config.yaml'); s=score_lead(leads[0], r, reference_date=date(2024,1,20)); print(s.total_score, s.decision, s.priority, len(s.factor_scores)); assert len(s.factor_scores)==5 and 1 <= s.total_score <= 10"
```

Pass when weights sum to 1, all factors are represented, the final score is 1-10, and the 7.5/5.0 thresholds are applied to the unrounded score.

## Phase 3 - Data pipeline

Verify sample-data coverage and edge cases:

```powershell
$trainingCount = (Import-Csv ..\leads_training.csv).Count
$sampleCount = (Import-Csv .\leads.csv).Count
$testingCount = (Import-Csv ..\leads_testing.csv).Count
$fullCount = (Import-Csv ..\leads_full_scale_100.csv).Count
Write-Output "Training=$trainingCount PackagedSample=$sampleCount Testing=$testingCount Full=$fullCount"
if ($trainingCount -lt 30 -or $sampleCount -lt 30) { throw 'Training data and packaged sample must each contain at least 30 leads.' }
if ($testingCount -lt 1 -or $fullCount -ne 100) { throw 'Testing/full-scale dataset count is incorrect.' }
```

Run the deterministic CLI on the training and edge-case sets:

```powershell
.\venv\Scripts\python.exe main.py --input ..\leads_training.csv --output output_training.json --reference-date 2024-01-20 --no-llm
.\venv\Scripts\python.exe main.py --input ..\leads_testing.csv --output output_testing.json --reference-date 2024-01-20 --no-llm
```

Verify that incomplete required fields cannot qualify and all review decisions appear in the report's review list:

```powershell
.\venv\Scripts\python.exe -c "import json; r=json.load(open('output_testing.json', encoding='utf-8')); missing=next(x for x in r['leads'] if x['name']=='Test_MissingCompany'); assert missing['decision']=='REVIEW' and missing['priority']=='MEDIUM'; flagged={x['name'] for x in r['flagged_for_review']}; assert missing['name'] in flagged; assert {x['name'] for x in r['leads'] if x['decision']=='REVIEW'} <= flagged; assert all(x['priority']=='HIGH' for x in r['priority_queue']); print('Required-field and review routing OK')"
```

Pass when valid rows load, missing/invalid values do not crash processing, missing required name/company fields are routed to REVIEW, review-worthy records appear in `flagged_for_review`, and only QUALIFIED leads appear in `priority_queue`.

## Phase 4 - Batched LLM integration

Run this phase only when `groq` is installed and `GROQ_API_KEY` is set in `.env`. For a 10-lead smoke test, create a temporary subset and explicitly set the batch size:

```powershell
Import-Csv ..\leads_training.csv | Select-Object -First 10 | Export-Csv .\leads_llm_smoke.csv -NoTypeInformation
.\venv\Scripts\python.exe main.py --input .\leads_llm_smoke.csv --output .\output_llm_smoke.json --reference-date 2024-01-20 --batch-size 3 --verbose
```

Inspect the logs to confirm four batched requests (3, 3, 3, and 1 leads) and verify the report:

```powershell
.\venv\Scripts\python.exe -c "import json; r=json.load(open('output_llm_smoke.json', encoding='utf-8')); assert len(r['leads'])==10; assert all(x['score'] is not None and x['decision'] in {'QUALIFIED','REVIEW','REJECTED'} for x in r['leads']); assert all('llm_reasoning' not in x or isinstance(x['llm_reasoning'],str) for x in r['leads']); print('LLM enrichment report shape OK; errors:', len(r['errors']))"
```

Pass when deterministic score/decision/priority values remain authoritative, enrichments match the right leads despite duplicate names, and any malformed/partial response or API failure is retried where applicable and surfaced in `errors`. Never expose API keys in output or logs. Remove the two temporary smoke-test files after review. Mocked tests do not count as a live-provider pass.

For a bounded live-provider check, run the notebook's **Optional live Groq/API smoke test** cell after setting a newly rotated `GROQ_API_KEY` in `lead-qualifier/.env`. It checks authenticated access to `/models`, confirms the configured model is available, then runs the real CLI on five training leads in two batches and compares the deterministic scores/decisions with an offline baseline. The cell suppresses API response bodies and never prints the key. A key pasted into a chat or notebook should be revoked before testing; never place credentials in notebook source.

## Phase 5 - Outreach drafts

Inspect the generated messages in the report:

```powershell
.\venv\Scripts\python.exe -c "import json; r=json.load(open('output_training.json', encoding='utf-8')); assert all((x['outreach_message'] is not None)==(x['decision']=='QUALIFIED') for x in r['leads']); qualified={x['name'] for x in r['leads'] if x['decision']=='QUALIFIED'}; messages=r['sample_outreach_messages']; assert all(x['lead'] in qualified for x in messages); assert len(messages)<=5; assert r['summary']['qualified_count']<3 or len(messages)>=3; print('Sample drafts:', len(messages)); [print(x['lead'], x['message'][:160]) for x in messages]"
```

Pass when only qualified leads receive drafts, sample examples vary across industry/source when the data permits, and messages do not invent customer references, lead interests, or other facts. Drafts are for salesperson review—not automatic sending. REVIEW leads need human judgment; rejected leads must not enter the immediate outreach queue.

## Phase 6 - Report generation

Validate the required report sections and key constraints:

```powershell
.\venv\Scripts\python.exe -c "import json; r=json.load(open('output_training.json', encoding='utf-8')); required={'metadata','summary','leads','priority_queue','sample_outreach_messages','flagged_for_review','errors'}; assert required <= r.keys(), required-r.keys(); s=r['summary']; assert s['total_processed']==len(r['leads'])==30; assert s['qualified_count']+s['review_count']+s['rejected_count']==30; assert all({'lead_id','name','company','score','decision','priority','reasoning','factor_breakdown','outreach_message'} <= x.keys() for x in r['leads']); assert all(1 <= x['score'] <= 10 and x['reasoning'] for x in r['leads']); q=r['priority_queue']; assert all(x['priority']=='HIGH' for x in q); assert [x['score'] for x in q]==sorted((x['score'] for x in q), reverse=True); qids={x['lead_id'] for x in q}; assert qids=={x['lead_id'] for x in r['leads'] if x['decision']=='QUALIFIED'}; fids={x['lead_id'] for x in r['flagged_for_review']}; assert {x['lead_id'] for x in r['leads'] if x['decision']=='REVIEW'} <= fids; assert all((x['outreach_message'] is not None)==(x['decision']=='QUALIFIED') for x in r['leads']); assert len(r['sample_outreach_messages'])<=5; assert s['qualified_count']<3 or len(r['sample_outreach_messages'])>=3; assert isinstance(r['errors'],list); print('Phase 6 report contract OK')"
```

Pass when the report includes per-lead deterministic reasoning, score, decision, priority, and factor breakdown; consistent summary counts and qualified percentage; common rejection reasons; a score-descending queue of qualified leads; 3-5 varied sample drafts when at least three leads qualify; every REVIEW or failed-enrichment record in `flagged_for_review`; and all processing failures in `errors`.

## Phase 7 - End-to-end testing

Run the production-size deterministic regression first:

```powershell
$reportPath = Join-Path $env:TEMP 'lead-qualifier-phase7-report.json'
$timer = [Diagnostics.Stopwatch]::StartNew()
.\venv\Scripts\python.exe main.py --input ..\leads_full_scale_100.csv --output $reportPath --reference-date 2024-01-20 --no-llm
if ($LASTEXITCODE -ne 0) { throw '100-lead CLI run failed.' }
$timer.Stop()
.\venv\Scripts\python.exe -c "import json,sys; r=json.load(open(sys.argv[1], encoding='utf-8')); assert r['summary']['total_processed']==100; assert len(r['leads'])==100; assert len({x['lead_id'] for x in r['leads']})==100; assert all('reasoning' in x and 1 <= x['score'] <= 10 for x in r['leads']); print(r['summary'])" $reportPath
if ($LASTEXITCODE -ne 0) { throw '100-lead report validation failed.' }
if ($timer.Elapsed.TotalSeconds -ge 300) { throw "Runtime target exceeded: $($timer.Elapsed.TotalSeconds) seconds" }
Remove-Item -LiteralPath $reportPath -ErrorAction SilentlyContinue
"100-lead deterministic run completed in $([math]::Round($timer.Elapsed.TotalSeconds, 2)) seconds"
```

This deterministic run validates the CLI/report path and runtime without credentials. When provider credentials and network access are available, run the LLM-enabled full-scale submission separately and verify batching and runtime. Without credentials, record live provider behavior as unverified; mocked tests do not certify external API behavior.

## Phase 8 - Documentation and polish

Check the README sections and review the final report/notebook as a business analyst:

```powershell
$readme = Get-Content README.md -Raw
foreach ($section in @('Quick Start', 'Qualification Rubric', 'Known Limitations')) {
  if (-not $readme.Contains($section)) { throw "README is missing $section" }
}
if (-not $readme.Contains('directional')) { throw 'README must describe aggregate statistics as directional.' }
'README sections OK'
```

Confirm the README explains CLI arguments and limitations; review score explanations, flagged records, and example drafts as an analyst. Aggregate statistics must be described as directional—not proof of conversion or revenue. The notebook's **Phases 6-8 acceptance checks** cell provides an offline report, end-to-end CLI, and documentation verification.

## Phase 9 - Submission package

Create a ZIP from `lead-qualifier` using an explicit include list so the virtual environment and `.env` cannot be included:

```powershell
$include = @('main.py', 'config.yaml', 'leads.csv', 'output_report.json', 'README.md', 'requirements.txt', '.env.example', '.gitignore', 'utils', 'tests')
Compress-Archive -Path $include -DestinationPath ..\lead-qualifier-submission.zip -Force
```

Verify required entries and exclusions:

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path ..\lead-qualifier-submission.zip))
try {
  $entries = $archive.Entries.FullName
  foreach ($requiredPath in @('main.py', 'config.yaml', 'leads.csv', 'output_report.json', 'README.md', 'requirements.txt')) {
    if (-not ($entries | Where-Object { $_ -eq $requiredPath -or $_.EndsWith("/$requiredPath") })) {
      throw "Archive missing $requiredPath"
    }
  }
  if ($entries | Where-Object { $_ -match '(^|/)(\.env|venv|__pycache__)(/|$)' }) {
    throw 'Archive contains a secret or environment/cache directory.'
  }
  'Submission archive contents OK'
} finally {
  $archive.Dispose()
}
```
