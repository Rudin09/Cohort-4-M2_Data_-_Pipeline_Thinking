# Lead Intelligence System - Testing Guide

This guide follows the phases in [WORKFLOW_PLAN.md](./WORKFLOW_PLAN.md). Commands use Windows PowerShell and assume the terminal starts in the repository root.

## Current alignment status

Phase 1-3 fixes remain in place. Phase 4 sends deterministic rubric results with stable per-run lead IDs and accepts explanation/review-note fields only; malformed output is retried once, and partial retries contain only missing leads while retaining prior successes. Per-batch diagnostics report duration, request attempts, validated count, finish reason, and a safe failure category; no prompt/response bodies or credentials are logged. The configured model returned HTTP 400 for `response_format={"type":"json_object"}` in a minimal pilot, so the client uses a compact JSON-only prompt and validates responses. Phase 5 provides three reproducible, fact-only outreach structures for QUALIFIED leads; the chosen variant is recorded per lead. Every lead has a unique report-wide `priority_rank`, retained by qualified queue entries. Automated provider tests use mocks.

## Latest Phase 6-8 verification (2026-10-31)

| Phase/check | Result | Observed evidence |
|---|---|---|
| 6 - Report generation | PASS | All seven report sections; unique sequential report-wide ranks, deterministic per-lead reasoning, qualified-only queue with preserved ranks, and REVIEW/error visibility. |
| 7 - End-to-end testing | PASS | Training/testing/full-scale deterministic runs process 30/20/100 leads; the regenerated 100-lead report has ranks 1-100 and the queue preserves those ranks. |
| 8 - Documentation and polish | PASS | README renders to one Letter page at 10pt Arial with 0.55-inch margins; notebook JSON and updated acceptance checks validate report ranks. |
| Unit tests | PASS | 27 tests passed, including all three outreach variants, safe batch diagnostics, bounded missing-only retries, unique rank/tie-break behavior, and report-contract tests. |
| Live Groq smoke test | PASS | Authenticated `/models` returned HTTP 200; configured model was listed; five leads were enriched in two batches with zero report errors; deterministic scores, decisions, and priorities were unchanged. |
| Live Groq 100-lead attempt (previous prompt/batch settings) | PARTIAL | 85/100 leads received LLM reasoning; 15 failed response validation. Seven batches took 428.9 seconds; deterministic decisions were preserved. |
| Fixed-input tuning pilot | PASS | Ten identical leads were tested at batch sizes 5/10/15. All had 10/10 reasoning and preserved deterministic outputs; batch 5 took 6.7 seconds with zero retries/errors, while 10/15 each needed strict-response retry. Default set to 5. |
| Live Groq 100-lead retest | PASS | All 100 leads received reasoning with zero errors; 20 batches, one request each, `finish_reason=stop`, no validation retries. Runtime 299.8 seconds; deterministic score/decision/priority matched the baseline. |

The first 100-lead attempt was PARTIAL; the retest passed the full acceptance gate and is now the submitted report. Runtime is 299.8 seconds, just under the five-minute limit, so allow for provider/network variability when rerunning. The live report was generated to a temporary path and promoted only after confirming complete reasoning, zero errors, and deterministic score/decision/priority equality. No API key or provider response body is included in logs or this guide.

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

Pass when deterministic score/decision/priority values remain authoritative, enrichments match the right leads despite duplicate names, malformed output gets one strict retry, partial output retries only missing leads, and any unresolved failure is surfaced in `errors`. Logs must include per-batch elapsed seconds, API request attempts, valid/total leads, safe finish reason, and a sanitized failure category—not API keys or raw provider text. Remove temporary smoke-test files after review. Mocked tests do not count as a live-provider pass.

To compare prompt-only JSON response quality at several batch sizes, use the same fixed input subset and test `--batch-size 5`, `10`, and `15`. Record elapsed time, `llm_reasoning` coverage, error count, batch diagnostics, and unchanged score/decision/priority against a deterministic baseline. In the 10-lead pilot, batch 5 was fastest with no recovery retries and was selected as the default. Do not select a setting based only on fewer API calls; use valid response coverage and throughput. The tested JSON-mode `response_format` option returned HTTP 400 for the configured model and is not enabled.

For a bounded live-provider check, run the notebook's **Optional live Groq/API smoke test** cell after setting a newly rotated `GROQ_API_KEY` in `lead-qualifier/.env`. It checks authenticated access to `/models`, confirms the configured model is available, then runs the real CLI on five training leads in two batches and compares the deterministic scores/decisions with an offline baseline. The cell suppresses API response bodies and never prints the key. A key pasted into a chat or notebook should be revoked before testing; never place credentials in notebook source.

## Phase 5 - Outreach drafts

Inspect the generated messages in the report. `outreach_variant` identifies one of three materially different structures (`fact_first`, `question_first`, or `direct_context`); selection is deterministic for the stable per-run lead ID.

```powershell
.\venv\Scripts\python.exe -c "import json; r=json.load(open('output_training.json', encoding='utf-8')); assert all((x['outreach_message'] is not None)==(x['decision']=='QUALIFIED') for x in r['leads']); qualified={x['name'] for x in r['leads'] if x['decision']=='QUALIFIED'}; messages=r['sample_outreach_messages']; assert all(x['lead'] in qualified for x in messages); assert len(messages)<=5; assert r['summary']['qualified_count']<3 or len(messages)>=3; print('Sample drafts:', len(messages)); [print(x['lead'], x['message'][:160]) for x in messages]"
```

Pass when each qualified lead receives one of the three variants, REVIEW/REJECTED leads have no draft or variant, and the report samples name the same variant as their lead record. Messages should cite the supplied company and available industry, size, and source facts; they must not invent needs, budgets, or customer references. Drafts are for salesperson review—not automatic sending.

## Phase 6 - Report generation

Validate the required report sections and key constraints:

```powershell
.\venv\Scripts\python.exe -c "import json; r=json.load(open('output_training.json', encoding='utf-8')); required={'metadata','summary','leads','priority_queue','sample_outreach_messages','flagged_for_review','errors'}; assert required <= r.keys(), required-r.keys(); s=r['summary']; assert s['total_processed']==len(r['leads'])==30; assert s['qualified_count']+s['review_count']+s['rejected_count']==30; assert all({'lead_id','name','company','score','decision','priority','priority_rank','reasoning','factor_breakdown','outreach_message'} <= x.keys() for x in r['leads']); variants={'fact_first','question_first','direct_context'}; assert all((x.get('outreach_variant') in variants)==(x['decision']=='QUALIFIED') for x in r['leads']); assert all(1 <= x['score'] <= 10 and x['reasoning'] for x in r['leads']); ranks={x['lead_id']:x['priority_rank'] for x in r['leads']}; assert sorted(ranks.values())==list(range(1,31)); q=r['priority_queue']; assert all(x['priority']=='HIGH' and x['priority_rank']==ranks[x['lead_id']] for x in q); assert [x['score'] for x in q]==sorted((x['score'] for x in q), reverse=True); assert [x['priority_rank'] for x in q]==sorted(x['priority_rank'] for x in q); qids={x['lead_id'] for x in q}; assert qids=={x['lead_id'] for x in r['leads'] if x['decision']=='QUALIFIED'}; fids={x['lead_id'] for x in r['flagged_for_review']}; assert {x['lead_id'] for x in r['leads'] if x['decision']=='REVIEW'} <= fids; assert all((x['outreach_message'] is not None)==(x['decision']=='QUALIFIED') for x in r['leads']); assert len(r['sample_outreach_messages'])<=5; assert all(x['outreach_variant']==next(row['outreach_variant'] for row in r['leads'] if row['lead_id']==x['lead_id']) for x in r['sample_outreach_messages']); assert s['qualified_count']<3 or len(r['sample_outreach_messages'])>=3; assert isinstance(r['errors'],list); print('Phase 6 report contract OK')"
```

Pass when every lead has a unique sequential report-wide rank ordered by deterministic score (ties by lead ID), qualified queue entries retain the same ranks, and the report includes per-lead deterministic reasoning, score, decision, priority, and factor breakdown; consistent summary counts and qualified percentage; common rejection reasons; a qualified-only priority queue; 3-5 varied sample drafts when at least three leads qualify; every REVIEW or failed-enrichment record in `flagged_for_review`; and all processing failures in `errors`.

## Phase 7 - End-to-end testing

Run the production-size deterministic regression first:

```powershell
$reportPath = Join-Path $env:TEMP 'lead-qualifier-phase7-report.json'
$timer = [Diagnostics.Stopwatch]::StartNew()
.\venv\Scripts\python.exe main.py --input ..\leads_full_scale_100.csv --output $reportPath --reference-date 2024-01-20 --no-llm
if ($LASTEXITCODE -ne 0) { throw '100-lead CLI run failed.' }
$timer.Stop()
.\venv\Scripts\python.exe -c "import json,sys; r=json.load(open(sys.argv[1], encoding='utf-8')); assert r['summary']['total_processed']==100; assert len(r['leads'])==100; assert len({x['lead_id'] for x in r['leads']})==100; assert sorted(x['priority_rank'] for x in r['leads'])==list(range(1,101)); ranks={x['lead_id']:x['priority_rank'] for x in r['leads']}; q=r['priority_queue']; assert all(x['priority_rank']==ranks[x['lead_id']] for x in q); assert [x['priority_rank'] for x in q]==sorted(x['priority_rank'] for x in q); assert all('reasoning' in x and 1 <= x['score'] <= 10 for x in r['leads']); print(r['summary'])" $reportPath
if ($LASTEXITCODE -ne 0) { throw '100-lead report validation failed.' }
if ($timer.Elapsed.TotalSeconds -ge 300) { throw "Runtime target exceeded: $($timer.Elapsed.TotalSeconds) seconds" }
Remove-Item -LiteralPath $reportPath -ErrorAction SilentlyContinue
"100-lead deterministic run completed in $([math]::Round($timer.Elapsed.TotalSeconds, 2)) seconds"
```

This deterministic run validates the CLI/report path and runtime without credentials. The optional live Groq smoke-test cell verifies a small authenticated batch run; the separate full-scale live retest above validates provider behavior on 100 leads. Mocked tests alone do not certify external API behavior.

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

Confirm the README explains how to run the CLI, the rubric, and limitations; review score explanations, flagged records, and example drafts as an analyst. Render/print the README to PDF using a consistent page setup and confirm it is no more than one page. Aggregate statistics must be described as directional—not proof of conversion or revenue. The notebook's **Phases 6-9 acceptance checks** cell provides offline report, end-to-end CLI, documentation, and submission archive verification.

## Phase 9 - Submission package

From the repository root, create a package containing the app, tests, final report, analyst notebook, workflow/testing documentation, and all input datasets. Entries are written explicitly so `.env`, the virtual environment, caches, and one-off helper scripts are excluded. The ZIP layout keeps `lead-qualifier/README.md` beside the root-level `TESTING_GUIDE.md` that it links to.

```powershell
$root = (Get-Location).Path
$archivePath = Join-Path $root 'lead-qualifier-submission.zip'
$buildPath = Join-Path $root 'lead-qualifier-submission.build.zip'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path -LiteralPath $buildPath) {
  Remove-Item -LiteralPath $buildPath -Force
}
$archive = [System.IO.Compression.ZipFile]::Open($buildPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
  $package = Join-Path $root 'lead-qualifier'
  $packageFiles = @(
    'main.py', 'config.yaml', 'leads.csv', 'output_report.json',
    'README.md', 'requirements.txt', '.env.example', '.gitignore'
  )
  foreach ($file in $packageFiles) {
    $source = Join-Path $package $file
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $source, "lead-qualifier/$file") | Out-Null
  }
  foreach ($folder in @('utils', 'tests')) {
    Get-ChildItem -LiteralPath (Join-Path $package $folder) -Recurse -File |
      Where-Object { $_.FullName -notmatch '\\(__pycache__|venv)\\' -and $_.Extension -ne '.pyc' } |
      ForEach-Object {
        $relative = $_.FullName.Substring($package.Length + 1).Replace('\', '/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $_.FullName, "lead-qualifier/$relative") | Out-Null
      }
  }
  foreach ($file in @(
    'TESTING_GUIDE.md', 'WORKFLOW_PLAN.md', 'lead_analyst_dashboard.ipynb',
    'leads_training.csv', 'leads_testing.csv', 'leads_full_scale_100.csv'
  )) {
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, (Join-Path $root $file), $file) | Out-Null
  }
} finally {
  $archive.Dispose()
}
```

Verify the archive contents and exclusions:

```powershell
$archive = [System.IO.Compression.ZipFile]::OpenRead($buildPath)
try {
  $entries = $archive.Entries.FullName
  foreach ($requiredPath in @(
    'lead-qualifier/main.py', 'lead-qualifier/config.yaml',
    'lead-qualifier/leads.csv', 'lead-qualifier/output_report.json',
    'lead-qualifier/README.md', 'lead-qualifier/requirements.txt',
    'lead_analyst_dashboard.ipynb', 'TESTING_GUIDE.md', 'WORKFLOW_PLAN.md',
    'leads_training.csv', 'leads_testing.csv', 'leads_full_scale_100.csv'
  )) {
    if ($requiredPath -notin $entries) { throw "Archive missing $requiredPath" }
  }
  if ($entries | Where-Object { $_ -match '(^|/)(\.env|venv|__pycache__)(/|$)|\.pyc$|(^|/)check_.*\.py$' }) {
    throw 'Archive contains a secret, environment/cache directory, or one-off helper.'
  }
  $reportEntry = $archive.GetEntry('lead-qualifier/output_report.json')
  if (-not $reportEntry) { throw 'Archive is missing the final report.' }
  'Submission archive contents and exclusions OK'
} finally {
  $archive.Dispose()
}
Move-Item -LiteralPath $buildPath -Destination $archivePath -Force
'Verified archive published as lead-qualifier-submission.zip'
```

The submitted `output_report.json` is the validated live 100-lead report (`llm_model: openai/gpt-oss-20b`), with LLM reasoning for every lead and zero errors. Scores, decisions, and priorities exactly match the deterministic baseline. A deterministic offline report remains reproducible with `--no-llm`.
