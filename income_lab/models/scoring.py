"""Gewogen scoring van de top-kandidaten (Autonomous Online Income Lab).

Scores 1-10 per criterium zijn oordelen [E] op basis van research/00_research_log.md.
Run: python income_lab/models/scoring.py  -> schrijft scoring_output.md
"""
from pathlib import Path

WEIGHTS = {
    "winst": 0.25,          # potentieel winstniveau
    "automatisering": 0.20,
    "geen_marketing": 0.20,
    "vraag": 0.15,
    "concurrentie": 0.10,   # hoog = gunstige concurrentiepositie
    "lage_kosten": 0.05,
    "onderhoud": 0.05,      # hoog = weinig onderhoud
}

# (naam, scores in volgorde van WEIGHTS, korte motivatie)
CANDIDATES = [
    ("Atlassian Forge micro-apps", [9, 7, 9, 8, 6, 9, 6],
     "$1.8B GMV / ~8k apps; 0% fee tot $1M; enterprise koopt self-service; support/security-eisen"),
    ("Apify Store Actor-portfolio", [7, 9, 8, 9, 4, 10, 5],
     "$1.7M/mnd uitbetaald; MCP/agent-distributie; 108k actors (2x in ~1 jaar); scrapers breken"),
    ("JetBrains betaalde plugins", [6, 7, 8, 6, 7, 9, 6],
     "85% share, licenties door JetBrains; kleinere markt; AI-assistenten vervangen sommige plugins"),
    ("MQL5 indicatoren/utilities", [7, 7, 8, 6, 4, 9, 5],
     "store in MT5-terminal, 80% share; reputatierisico, reviews, meertalige vragen"),
    ("Parametrische 3D-print/laserbestanden", [5, 8, 8, 7, 4, 9, 8],
     "code-gegenereerd, Etsy/Cults/MakerWorld-zoekverkeer; lage prijzen, AI-vloed"),
    ("Game-engine code-tools (Fab/Unity/Roblox)", [6, 7, 7, 7, 5, 10, 6],
     "Fab gemiddeld ~$1.2k/publisher/jr; editor-tools verkopen beter dan art; reviews en updates per engine-versie"),
    ("Booth.pm VRChat 3D-assets", [6, 4, 8, 9, 5, 8, 7],
     "snelgroeiend (+79%), maar 3D-artistiek vakwerk, AI-weerstand bij kopers"),
    ("Shopify-app (ter vergelijking)", [8, 5, 6, 8, 3, 9, 3],
     "veel omzet mogelijk, maar live-chat-support en reviewcultuur = verborgen werk"),
    ("Google Workspace add-ons", [6, 7, 6, 6, 6, 9, 6],
     "marketplace-zoekverkeer, maar installs != omzet; eigen checkout"),
    ("Framer templates", [5, 5, 8, 6, 5, 10, 8],
     "100% voor creator; visuele editor beperkt automatisering"),
    ("Chrome-extensie freemium", [6, 7, 5, 6, 4, 10, 6],
     "store-zoekverkeer, maar meeste extensies <100 users; eigen betaling"),
]


def weighted(scores):
    return sum(w * s for w, s in zip(WEIGHTS.values(), scores))


def main():
    rows = sorted(CANDIDATES, key=lambda c: weighted(c[1]), reverse=True)
    head = "| Rang | Kandidaat | " + " | ".join(
        f"{k} ({int(v*100)}%)" for k, v in WEIGHTS.items()) + " | **Totaal** | Motivatie |"
    sep = "|" + "---|" * (len(WEIGHTS) + 4)
    lines = ["# Gewogen scoring (gegenereerd door scoring.py)", "", head, sep]
    for i, (name, sc, why) in enumerate(rows, 1):
        lines.append(f"| {i} | {name} | " + " | ".join(map(str, sc)) +
                     f" | **{weighted(sc):.2f}** | {why} |")
    out = "\n".join(lines) + "\n"
    Path(__file__).with_name("scoring_output.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
