# Autonomous Online Income Lab

Onderzoek (3 nov 2026) naar het beste grotendeels geautomatiseerde, faceless online verdienmodel.

**Start hier:** [`REPORT.md`](REPORT.md): executive summary, top 10, top 3 diepgaand, winnaar, bouwplan, groeipad.

| Bestand | Inhoud |
|---|---|
| `REPORT.md` | Eindrapport (Deel 1–6) |
| `research/00_research_log.md` | Alle bevindingen met bronlabels [F]/[S]/[E]/[A] |
| `research/01_longlist_tracker.md` | 43 onderzochte modellen, status en afwijsreden |
| `research/atlassian_opportunities_<datum>.md/.csv` | Live marktvalidatie: vraag (stemmen) vs. aanbod (Marketplace) |
| `models/scoring.py` → `scoring_output.md` | Gewogen ranking |
| `models/financial_model.py` → `financial_output.md` | Scenario's conservatief/realistisch/optimistisch per winstniveau |
| `models/atlassian_opportunity_scan.py` | Herbruikbare vraag-mining-tool (wekelijks draaien) |

```bash
python3 income_lab/models/scoring.py
python3 income_lab/models/financial_model.py
python3 income_lab/models/atlassian_opportunity_scan.py --n 200   # ~10 min, alleen publieke API's
```
