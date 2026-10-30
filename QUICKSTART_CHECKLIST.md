# Quick-Start Checklist - Lead Intelligence Mini Project

## ✅ Pre-Flight (Before Coding)

- [ ] Read Mini_Project_Brief.docx completely
- [ ] Review DATA_README.md for data file purposes
- [ ] Understand: NO ground truth - you define the rubric
- [ ] Choose LLM provider (Groq/OpenAI/Gemini/Claude free tier)
- [ ] Get API key, add to `.env` file

## 🏗️ Phase 1: Setup (30 min)

- [ ] Create project folder structure
- [ ] Initialize git repo
- [ ] Create `requirements.txt` with dependencies
- [ ] Set up virtual environment
- [ ] Create `config.yaml` with rubric (start with template)

## 🎯 Phase 2: Rubric Design (1-2 hours)

- [ ] Define 3-5 scoring factors with weights (must total 100%)
- [ ] Set decision thresholds (qualified/review/rejected)
- [ ] Document rubric in config.yaml AND README
- [ ] Test rubric logic manually on 5 training leads

## 🔧 Phase 3: Core Pipeline (2-3 hours)

- [ ] `data_loader.py`: Load CSV, validate, handle missing data
- [ ] `rubric_engine.py`: Apply scoring rules to each lead
- [ ] Test on `leads_training.csv` (30 leads) - verify scores make sense
- [ ] Add logging for debugging

## 🤖 Phase 4: LLM Integration (2-3 hours)

- [ ] `llm_client.py`: Batched API calls with retry logic
- [ ] Design batch prompt (include rubric in prompt)
- [ ] Test on 5-10 leads first
- [ ] Handle: rate limits, timeouts, invalid JSON responses
- [ ] Parse LLM output into structured format

## ✍️ Phase 5: Messages & Report (1-2 hours)

- [ ] `message_generator.py`: Personalized templates by priority
- [ ] `report_builder.py`: Build JSON report with all required sections
- [ ] Generate sample outreach messages (3-5 examples)
- [ ] Create priority queue (sorted by score)

## 🧪 Phase 6: Testing (1-2 hours)

- [ ] **Training**: `python main.py --input leads_training.csv` ✓ 30 leads
- [ ] **Edge Cases**: `python main.py --input leads_testing.csv` ✓ 20 leads, no crashes
- [ ] **Production**: `python main.py --input leads_full_scale_100.csv` ✓ 100 leads
- [ ] Verify output_report.json has all required fields

## 📝 Phase 7: Documentation (30 min)

- [ ] `README.md`: Run instructions, rubric summary, limitations
- [ ] Code comments and type hints
- [ ] Remove API keys, large files from repo

## 📦 Phase 8: Submit (15 min)

- [ ] Zip project folder (exclude venv, __pycache__, .env)
- [ ] Verify zip contains: source, sample leads.csv, output_report.json, README.md
- [ ] Submit

---

## 🎯 Key Files to Create

| File | Purpose |
|------|---------|
| `main.py` | Entry point, orchestrates pipeline |
| `config.yaml` | Rubric, thresholds, LLM settings |
| `utils/data_loader.py` | CSV reading + validation |
| `utils/rubric_engine.py` | Deterministic scoring |
| `utils/llm_client.py` | Batched LLM calls + retries |
| `utils/message_generator.py` | Personalized outreach |
| `utils/report_builder.py` | Output report assembly |
| `requirements.txt` | Dependencies |
| `README.md` | Documentation |
| `output_report.json` | **From 100-lead run** |

---

## ⚡ Pro Tips

1. **Start simple**: Get deterministic rubric scoring working BEFORE adding LLM
2. **Batch LLM calls**: 10-20 leads per call, not 1-per-lead
3. **Log everything**: Failed leads, retries, parsing errors
4. **Test prompts early**: Bad prompt = bad output, waste of time
5. **Handle missing data gracefully**: Flag for review, don't crash
6. **Personalize messages**: Reference specific lead details (industry, size, source)

---

## 🚨 Common Pitfalls to Avoid

- ❌ Calling LLM once per lead (slow, expensive, rate limits)
- ❌ No error handling for API failures
- ❌ Crashing on missing CSV fields
- ❌ Generic outreach messages ("Hi, interested in our product?")
- ❌ No rubric documentation in README
- ❌ Including API keys in submission
- ❌ Not testing on all three datasets

---

## 📊 Data Quick Reference

| Dataset | Leads | Use For |
|---------|-------|---------|
| `leads_training.csv` | 30 | Development, rubric tuning |
| `leads_testing.csv` | 20 | Edge case validation |
| `leads_full_scale_100.csv` | **100** | **Final submission run** |

**Workflow**: Train (30) → Test (20) → **Scale (100)** → Submit

---

## 🏆 Grading Focus

| Area | What They Check |
|------|-----------------|
| Correctness | No crashes, consistent scoring, defensible decisions |
| Usefulness | Sales-ready report, personalized messages, priority queue |
| Robustness | Handles missing data, API errors, edge cases |
| Efficiency | Batched LLM, reasonable runtime |
| Docs | Runnable, rubric explained, limitations noted |

---

*Keep this checklist handy. Check off each item as you complete it.*