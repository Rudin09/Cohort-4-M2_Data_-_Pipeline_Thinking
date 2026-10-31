# Lead Intelligence System

A command-line tool that scores leads with a consistent rubric, flags records for human review, and prepares outreach drafts for salesperson review. It does not send emails.

## Quick Start (Windows PowerShell)

From the repository root, install the dependencies and configure Groq:

```powershell
Set-Location .\lead-qualifier
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Add your GROQ_API_KEY to .env, then run:
.\venv\Scripts\python.exe main.py --input ..\leads_full_scale_100.csv --output output_report.json --reference-date 2024-01-20
```

For an offline run without an API key, add `--no-llm`. The report includes a decision and explicit `priority_rank` for every lead; the qualified-only queue retains those report-wide ranks. Qualified leads receive one of three fact-only message structures, selected deterministically by lead ID. LLM requests default to five leads per batch; `--batch-size` overrides this setting.

## Qualification Rubric

The 1–10 score combines company-size fit (25%), industry alignment (25%), interaction recency (20%), lead source (15%), and buying signals (15%). Scores of 7.5 or higher qualify, scores from 5.0 to below 7.5 require review, and scores below 5.0 are rejected; missing required name or company forces review. Missing optional fields use documented rubric defaults and can still be flagged for human review.

## Known Limitations

- The rubric reflects documented business assumptions, not historical conversion data; aggregate statistics are directional.
- Missing optional data and unfamiliar industries or sources use rubric defaults and should be reviewed.
- LLM explanations depend on provider availability; the verified 100-lead run completed in 299.8 seconds, just under the five-minute target, so timing may vary. They never change deterministic scores or decisions.
- The configured Groq model rejected the JSON-mode `response_format` option in a pilot; the client uses a compact JSON-only prompt and validates every response.
- Outreach uses three static fact-based structures, requires salesperson review, and is not sent by the tool.

For detailed test commands and acceptance checks, see [TESTING_GUIDE.md](../TESTING_GUIDE.md).
