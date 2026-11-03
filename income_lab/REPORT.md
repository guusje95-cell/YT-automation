# The Autonomous Online Income Lab: onderzoeksrapport

_Datum: 3 november 2026 · Onderzoek: 43 businessmodellen, ~60 bronnen, 2 live API-validaties · Alle cijfers gelabeld._

**Labels:** **[F]** feit uit primaire/officiële bron · **[S]** secundaire bron (blog, aggregator, zelfgerapporteerd) · **[E]** mijn schatting, verankerd aan bronnen · **[A]** aanname die je moet toetsen.
Ondersteunende bestanden: `research/00_research_log.md` (alle bevindingen), `research/01_longlist_tracker.md` (43 modellen + afwijsredenen), `models/scoring.py`, `models/financial_model.py`, `models/atlassian_opportunity_scan.py` + output in `research/`.

---

## Deel 1: Executive summary

**De belangrijkste ontdekking:** de beste kans zit niet bij "digitale producten maken met AI" (templates, art, stock, 3D, muziek, boeken). Die markten worden overspoeld door AI-aanbod en de prijzen storten in. Twee harde datapunten:
- Bij CGTrader is 1 op de 6 nieuwe uploads AI-gegenereerd, maar die leveren slechts ~$1 van elke $90 omzet op [S].
- Menselijke Etsy-verkopers van printables verloren ~40% van hun views toen AI-listings explodeerden [S].

Als AI iets goedkoop kan maken, kan iedereen het. Dan blijft er geen marge over.

De kans zit waar **AI het werk goedkoop maakt, maar de koper het zelf niet kan of wil maken**, en waar een **marktplaats met ingebouwde koopintentie** de verkoop, betaling, licentie en btw regelt. Dat is **kleine, gespecialiseerde software verkocht via enterprise-marktplaatsen**.

De vergelijking die de doorslag gaf: hoeveel omzet gaat er per verkoper rond op elke marktplaats?

| Marktplaats | Jaarlijkse omzet naar makers | Aantal verkopers/producten | Gemiddeld per verkoper/jaar |
|---|---|---|---|
| **Atlassian Marketplace** | ~$1,8 mrd GMV (2024) [S: Aventis] | ~1.800 partners, 8.000+ apps | **≈ $1M per partner, ≈ $225k per app** [E, zeer scheef verdeeld] |
| Apify Store | $1,7M/mnd ≈ $20M/jaar [F] | 5.600 ontwikkelaars, 108.000 actors | ≈ $3.600 per ontwikkelaar, ≈ $190 per actor [E] |
| Fab (Epic) | >$24M (2025) [S, Epic-cijfers] | >20.000 publishers, 420.000 listings | ≈ $1.200 per publisher [E] |
| Booth.pm 3D-modellen | ¥10,4 mrd ≈ $70M GMV (2025) [F] | onbekend | — |
| Civitai creatorpool | $26.900/mnd (juni 2026) [S] | duizenden | verwaarloosbaar |

Zelfs als je een factor 50 corrigeert voor scheefheid (Appfire, Tempo enz.), verdient een gemiddelde Atlassian-app nog vele malen meer dan een gemiddelde asset op welke creatieve marktplaats dan ook. Kopers zijn bedrijven die per gebruiker per maand betalen, terugkerend, via hun bestaande Atlassian-factuur.

**Top 3:**
1. **Atlassian Forge micro-apps** (gewogen score 8,00). Een portfolio van kleine Jira/Confluence-apps die precies één gat vullen waar duizenden gebruikers al jaren om vragen. Atlassian neemt **0% commissie tot $1M lifetime-omzet** [F], doet facturatie, trials, licenties en btw, en klanten vinden apps in de marketplace in hun eigen Jira.
2. **Apify Store Actor-portfolio** (7,65). Data- en automatiseringstools met betaling per gebruik. Apify betaalt **$1,7M/maand** uit [F] en AI-agents vinden en betalen tools via de Apify MCP-server en x402 [F]. Snelste tijd tot eerste omzet (dagen), maar lage omzet per actor en hevige concurrentie.
3. **JetBrains betaalde plugins** (6,85). Ontwikkelaars kopen in hun IDE; JetBrains regelt alles voor 15% [F]. Kleiner, maar weinig concurrentie in betaalde niches.

**Winnaar: Atlassian Forge micro-apps**, met de Apify-pijplijn als optionele tweede motor vanaf maand 4. Live-validatie (deze sessie):
- De publieke Atlassian-issuetracker bevat **5.808 onopgeloste featureverzoeken**. Het populairste heeft **2.798 stemmen** [F: jira.atlassian.com API].
- Kleine leveranciers met apps van één functie halen duizenden installaties [F: Marketplace API]:
  - *Subcomponents* (Broken Build): 1.417 installaties
  - *Default Values for Create Issue* (Big Fig Tree): 2.420 installaties
  - *Numbered Headings*: 5.040 installaties. Gestart door het Nederlandse Avisi, inmiddels eigendom van Appfire. Dat is ook een exit-route.

**Eerlijke verwachting (realistisch scenario):**
- Eerste omzet in maand 2–4.
- €500–€2.500 winst/maand na 6–12 maanden.
- €5.000–€10.000 na 12–24 maanden met 3–6 apps, bij **4–8 uur/week**.
- €25.000+ is mogelijk, maar vereist meerdere hits en is geen basisverwachting.

**Wat ik níét beloof:** geen enkel model in dit onderzoek is 100% passief. Elk serieus model heeft rest-werk: supportvragen beantwoorden (schriftelijk), platformupdates en kwaliteitscontrole. Het verschil zit in hoeveel: 2–8 uur/week bij de winnaar, tegenover 20+ uur bij de meeste alternatieven met vergelijkbare omzet.

---

## Deel 2: Top 10 (ranking)

Scores 1–10 per criterium (gewichten volgens opdracht). Berekening: `models/scoring.py` → `models/scoring_output.md`.

| # | Model | Winst 25% | Autom. 20% | Geen mkt 20% | Vraag 15% | Conc. 10% | Kosten 5% | Onderh. 5% | **Totaal** |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Atlassian Forge micro-apps | 9 | 7 | 9 | 8 | 6 | 9 | 6 | **8,00** |
| 2 | Apify Store Actor-portfolio | 7 | 9 | 8 | 9 | 4 | 10 | 5 | **7,65** |
| 3 | JetBrains betaalde plugins | 6 | 7 | 8 | 6 | 7 | 9 | 6 | **6,85** |
| 4 | MQL5 indicatoren/utilities | 7 | 7 | 8 | 6 | 4 | 9 | 5 | **6,75** |
| 5 | Parametrische 3D-print/laserbestanden | 5 | 8 | 8 | 7 | 4 | 9 | 8 | **6,75** |
| 6 | Game-engine code-tools (Fab/Unity/Roblox) | 6 | 7 | 7 | 7 | 5 | 10 | 6 | **6,65** |
| 7 | Booth.pm VRChat 3D-assets | 6 | 4 | 8 | 9 | 5 | 8 | 7 | **6,50** |
| 8 | Google Workspace add-ons | 6 | 7 | 6 | 6 | 6 | 9 | 6 | **6,35** |
| 9 | Shopify-app | 8 | 5 | 6 | 8 | 3 | 9 | 3 | **6,30** |
| 10 | Framer templates | 5 | 5 | 8 | 6 | 5 | 10 | 8 | **6,15** |

| # | Realistische winst na 12–24 mnd [E] | Automatisering [E] | Opstartkosten | Eerste omzet | Uren/week (stabiel) |
|---|---|---|---|---|---|
| 1 | €2.500–€10.000 | ~75–80% | €0–€300 | 2–4 mnd | 4–8 |
| 2 | €500–€3.000 | ~85% | €0–€150 | dagen–6 weken | 3–15 (schaalt met #actors) |
| 3 | €500–€3.000 | ~75% | €0–€200 | 1–3 mnd | 3–6 |
| 4 | €500–€5.000 | ~70% | €0–€200 | 1–2 mnd | 5–10 (veel berichten) |
| 5 | €200–€2.000 | ~80% | €100–€400 (printer/laser helpt) | 2–8 weken | 3–6 |
| 6 | €300–€2.500 | ~70% | €0–€200 | 1–3 mnd | 4–8 |
| 7 | €500–€5.000 | ~40% | €0–€500 | 1–3 mnd | 10+ (vakwerk) |
| 8 | €0–€2.000 | ~70% | €0–€100 | 1–6 mnd | 3–6 |
| 9 | €1.000–€10.000 | ~50% | €19 registratie | 2–6 mnd | 10–20 (support) |
| 10 | €200–€2.000 | ~50% | €0 | 1–3 mnd | 3–6 |

**Waarom deze volgorde, kort:**
- #1 wint op omzet per klant en op koopintentie binnen het platform.
- #2 wint op automatisering, maar verliest op omzet per eenheid en concurrentie: het aantal actors verdubbelde in ~1 jaar van 54k naar 108k [S/F].
- #9 Shopify heeft veel potentieel, maar Shopify-merchants verwachten live chat en de reviewdruk is hoog. Dat is precies het werk dat je niet wilt.
- #7 Booth is de grootste groeier (+79%) [F], maar 3D-avatarkleding is vakwerk. AI-3D verkoopt aantoonbaar slecht.

**Afgewezen:** 33 andere modellen, met redenen in `research/01_longlist_tracker.md`. De belangrijkste afwijzingen en de doorslaggevende feiten:
- **Etsy-printables, Notion, Canva, stock, AI-art, AI-muziek, KDP en POD**: verzadigd of beleidsmatig geblokkeerd. Canva verbiedt AI-content [F], Spotify verwijderde 75M spamtracks [F], KDP heeft een limiet van 3 titels/dag [S] en Amazon laat kopers zelf merch-designs genereren [S].
- **Contentsites, websites kopen en domeinen**: AI Overviews kosten clicks. Content-site-deals daalden 33,5% [S] en je hebt kapitaal nodig.
- **Betaalde MCP-servers, x402-API's en de ChatGPT-store**: echte trend, maar nu nog geen echte omzet. Minder dan 5% van de MCP-servers verdient iets [S]. Echte agent-uitgaven bedragen slechts 0,6–7,5% van het x402-volume [S]. ChatGPT heeft geen digitale betalingen [F]. Je pakt dit mee via Apify (#2) zonder erop te gokken.

---

## Deel 3: Top 3 diepgaand

### 3.1 Atlassian Forge micro-apps (#1)

**Exact businessmodel.** Je bouwt een portfolio van kleine, scherp afgebakende apps voor Jira, Confluence en Jira Service Management (Cloud). Ze draaien op Forge, Atlassians eigen serverless platform. Elke app lost één al jaren bestaand gat op, bijvoorbeeld:
- hiërarchische componenten;
- standaardwaarden voor systeemvelden;
- automatisch genummerde koppen;
- pagina's alfabetisch sorteren;
- bulk-acties;
- export- en rapportfuncties.

De apps worden verkocht als "Paid via Atlassian": de klant start een gratis trial in zijn eigen Jira en daarna factureert Atlassian per gebruiker per maand of jaar. Jij krijgt maandelijks uitbetaald.

**Doelgroep.** Jira- en Confluence-beheerders bij bedrijven van 10–5.000 gebruikers, wereldwijd. Zij zoeken in de in-product Marketplace ("Apps → Explore more apps") naar een oplossing op het moment dat ze het probleem hebben. Dat is koopintentie zonder dat jij iemand benadert.

**Marktvalidatie (bewezen):**
- Marketplace ≈ **$1,8 mrd omzet 2024**, ~19% CAGR sinds 2021 [S: Aventis Advisors, aug 2025].
- **3.572 betaalde Jira Cloud-apps** (live API, 3 nov 2026) [F].
- Vraag is publiek meetbaar: **5.808 onopgeloste suggesties** voor Jira Cloud, top-5 met 1.847–2.798 stemmen [F: jira.atlassian.com].
  - Veel verzoeken zijn 10–20 jaar oud. JRACLOUD-846 "subcomponents" is aangemaakt in **2002** en heeft 1.026 stemmen.
  - Het signaal: Atlassian bouwt dit niet zelf, dus de markt is aan app-leveranciers gelaten.
- Kleine leveranciers met micro-apps halen duizenden installaties [F: Marketplace API, zie §5 en `research/atlassian_opportunities_2026-11-03.md`].
- Indie-bewijs: Agile Docs $4.149 MRR na 18 maanden [S: Indie Hackers]; Lizard Brain (solo gestart) $1M lifetime-omzet in 2019 [S].
- Structurele wind mee: **Atlassian Data Center stopt op 28 maart 2029** [F]. Nieuwe DC-verkoop stopt rond maart 2028 [S]. Duizenden enterprise-klanten moeten naar Cloud en hebben daar vervangers nodig voor server/DC-apps die niet (goed) naar Cloud zijn gemigreerd.

**Concurrenten.**
- **Grote roll-ups** zoals Appfire (~200 apps) en Tempo [S]. Die zijn sterk in brede categorieën (testmanagement, tijdregistratie, scripting) en die vermijd je.
- **Kleine niche-apps met 50–500 installaties en weinig reviews.** Daar win je met betere UX, sneller updaten en een scherpere prijs.

**Verkoopplatformen.**
- Atlassian Marketplace (Jira, Confluence, JSM; later Bitbucket en Compass).
- Daarnaast nieuwe categorieën als **Rovo-agent-acties**: Forge-apps die AI-acties leveren aan Atlassians AI. Dat is vroeg en heeft minder concurrentie.

**Prijsstrategie.**
- Per-gebruiker-tiers volgens Atlassian-standaard, gratis voor kleine sites (≤10 gebruikers) om reviews en installaties op te bouwen.
- Daarna ~$0,50–$2 per gebruiker per maand, met dalende tiers [A, ijk aan concurrenten in de niche].
- Uitgangspunt: gemiddeld $40–$150 per betalende site per maand.
- Jaarabonnementen geven 10 maanden voor 12 (Atlassian-standaard).

**Financiële prognose** (`models/financial_output.md`, 1 USD = 0,87 EUR [A]):

| Doel winst/mnd | Conservatief: klanten / apps lanceren / u/wk | Realistisch | Optimistisch |
|---|---|---|---|
| €500 | 20 / 5 / 6 | 10 / 3 / 5 | 6 / 2 / 4 |
| €2.500 | 77 / 10 / 9 | 39 / 3 / 5 | 21 / 2 / 4 |
| €5.000 | 149 / 20 / 15 | 75 / 3 / 5 | 40 / 2 / 4 |
| €10.000 | 293 / 40 / 26 | 147 / 6 / 8 | 78 / 2 / 5 |
| €25.000 | 724 / 95 / 58 | 362 / 12 / 13 | 193 / 2 / 6 |
| €50.000 | 1.442 / 185 / 110 | 721 / 20 / 20 | 385 / 4 / 9 |

Aannames per scenario (cons./real./opt.):

| Aanname | Conservatief | Realistisch | Optimistisch |
|---|---|---|---|
| Gemiddelde omzet per betalende site | $40 | $80 | $150 |
| Trial → betaald | 15% | 25% | 35% |
| Betalende klanten per volwassen app | 40 | 120 | 300 |
| Hitrate (rest flopt) | 20% | 35% | 50% |
| Churn per maand | 3% | 2,5% | 2% |

Overige uitgangspunten:
- **Kosten:** ~€175/mnd vast. Forge-hosting valt binnen de gratis quota [A]. Variabele kosten per verkoop zijn ~0 tot $1M; daarna 17% commissie [F].
- **Brutomarge:** ~95–100% tot $1M lifetime, daarna ~80%.
- **Break-even:** 3–5 betalende klanten.
- **Omzet vs. winst:** bij €10k winst is de omzet ~$11,7k/mnd. Bij €50k loopt de commissie na ~17 maanden op naar 17%; je hebt dan ~20% meer omzet nodig.
- **Tijd tot eerste omzet:** listing-review 1–3 weken + trial 30 dagen + uitbetaling maandelijks achteraf ⇒ **eerste geld op de bank in maand 3–4** [E].
- **Stabiele inkomstenstroom:** 9–18 maanden [E].

**Automatiseringsarchitectuur:** zie Deel 5 (deze kandidaat is de winnaar).

**Risico's (reality check):**
- *"Waarom zou iemand dit kopen?"* Omdat duizenden mensen er al jaren publiek om stemmen en het native niet bestaat [F].
- *"Waarom bij mij?"* Je concurreert op exacte fit, prijs, UX en reviews, niet op merk. Dat is haalbaar in niches waar de bestaande app <500 installaties en matige reviews heeft. In de grote categorieën (Xray, Tempo, ScriptRunner) win je niet.
- *"Kan een concurrent het kopiëren?"* Ja. De moat is dun: eerste-in-niche, reviews, installed base (overstappen kost een beheerder moeite) en onderhoudsdiscipline. Daarom een **portfolio** in plaats van één app.
- *"Bestaat dit over 3 jaar nog?"* Risico op "sherlocking": Atlassian bouwt de functie zelf, of Rovo-AI maakt de app overbodig. Mitigatie: kies verzoeken die al >5 jaar openstaan, spreid over 5–20 apps en lever Rovo-acties mee. De DC-uitfasering (2028–2029) duwt juist vraag richting Cloud-apps.
- *"Kan AI het product goedkoper maken?"* Een klant gaat geen eigen Forge-app bouwen, laten beveiligen en onderhouden voor $50/mnd. Wel daalt de drempel voor concurrenten: verwacht meer kleine apps vanaf 2026–2027.
- *Platformafhankelijkheid:* hoog. Eén leverancier bepaalt commissie, ranking en regels. Commissies zijn al gestegen: Connect 75% vanaf okt 2026 [F]. Forge ging van 85% naar 83%, met 0% tot $1M als tijdelijke incentive [F].
- *Verborgen werk:*
  - Supportvragen (schriftelijk, vaak "hoe stel ik X in").
  - Security-eisen: EcoScanner, security-bugfix-SLA's [F].
  - Een 24-uurs werkdag-responstijd als je de "Runs on Atlassian"/Cloud Fortified-badge wilt [F].
  - Enterprise-klanten sturen soms beveiligingsvragenlijsten. Die zijn schriftelijk en grotendeels met standaardantwoorden te vullen.
- *Faceless?* Ja. De partnernaam is een handelsnaam en alle contact verloopt schriftelijk via een helpdesk. Let op: bij een eenmanszaak staat je naam in het KvK-register. Wil je dat afschermen, overweeg dan een BV. Nog te verifiëren [A]: of een particulier zonder onderneming Marketplace-partner kan worden voor betaalde apps.

### 3.2 Apify Store Actor-portfolio (#2)

**Exact businessmodel.** Je publiceert tientallen kleine "Actors" op de Apify Store: dataverzamelaars, converters, verrijkers en agent-tools. Ze worden afgerekend per event (bijv. $0,50–$5 per 1.000 resultaten). Apify host, schaalt, factureert en betaalt maandelijks 80% van de winst na platformkosten uit [F]. Actors zijn automatisch vindbaar voor AI-agents via de Apify MCP-server (Claude, Cursor) en zijn betaalbaar via x402 (USDC) [F].

**Doelgroep.** Growth-teams, data-analisten, AI-agent-bouwers en no-code-automatiseerders (Make/Zapier/n8n), wereldwijd.

**Marktvalidatie:**
- $1,7M/mnd uitbetaald aan 5.600 ontwikkelaars [F].
- 10.000+ aanmeldingen per dag [F].
- Topactors: Google Maps Scraper 680K gebruikers, Instagram 465K, TikTok 379K [F, Store-pagina].
- Categorie-leiders in niches (Idealista, Booking-reviews, Google News): 2.700–17.000 gebruikers [F].
- Topmakers: >$10.000 MRR [F].

**Concurrenten.** 108.000 actors [F], verdubbeld in ongeveer een jaar [S]. Ook verdienen is ongelijk verdeeld; ervaringen van nieuwkomers:

| Nieuwkomer | Resultaat |
|---|---|
| 13 actors | ~$110–$128 in de eerste 15 dagen [S] |
| 1 goede actor | ~$200/mnd na 3 maanden [S] |
| 35 scrapers | $0 na 90 dagen [S] |

Store-zoekverkeer was in die verslagen het belangrijkste kanaal; contentmarketing leverde vrijwel niets op [S].

**Prijsstrategie.** Pay-per-event rond de kleinste koopeenheid, bijvoorbeeld $0,001–$0,005 per resultaat plus een kleine start-fee. Rentals zijn sinds 1 oktober 2026 uitgefaseerd [S].

**Financiële prognose** (netto per actor per maand: cons. $8 / real. $30 / opt. $90 [E]):

| Doel | Conservatief: actors / u/wk | Realistisch | Optimistisch |
|---|---|---|---|
| €500 | 90 / 12 | 24 / 4 | 8 / 2 |
| €2.500 | 377 / 46 | 101 / 9 | 34 / 4 |
| €5.000 | 736 / 87 | 197 / 16 | 66 / 5 |
| €10.000 | 1.455 / 170 | 388 / 29 | 130 / 8 |
| €25.000+ | onhaalbaar | onhaalbaar (69+ u) | 321 / 17 |

Conclusie: Apify is uitstekend voor **snelle eerste omzet en leren**, maar het onderhoud schaalt lineair met het aantal actors. Scrapers breken als sites veranderen; na 3 dagen falen volgt een onderhoudsvlag en na 30 dagen deprecatie [F]. Boven ~€3.000/mnd wordt het een baan, tenzij je 1–3 grote hits hebt.

**Automatisering:**

| Stap | Hoe | % automatisch |
|---|---|---|
| Ontwikkeling | Claude Code met `apify create`/Crawlee-templates en input-schema's | 85% |
| QA | Apify draait dagelijks een test (default-input <5 min) [F] plus eigen asserts: faal luid bij lege output | 90% |
| Publicatie | `apify push` plus Store-metadata in de code | 90% |
| Verkoop, betaling, levering | Volledig via Apify, inclusief agent-betalingen via MCP/x402 [F] | 100% |
| Updates | Monitor-actor detecteert falen → Claude Code repareert → mens keurt goed | 60% |
| Vragen | Publieke Issues-tab: AI-concept, mens verstuurt | 60% |
| Tracking | Apify API → wekelijks rapport | 95% |

**Risico's:**
- Juridisch: scrapen van persoonsgegevens valt onder de AVG. Kies publieke, niet-persoonlijke data, officiële open data of conversie-utilities. De Amerikaanse uitspraak Meta v. Bright Data (2024) beschermt alleen uitgelogd scrapen en zegt niets over de AVG [F/S].
- Anti-botmaatregelen kosten proxy-geld en marge.
- Apify kan zelf concurrerende actors uitbrengen.
- Prijsdruk door 108k aanbieders.

### 3.3 JetBrains betaalde plugins (#3)

**Model.** Betaalde plugins (abonnement, met of zonder fallback-licentie) voor IntelliJ, PyCharm, WebStorm, Rider enz. JetBrains is merchant of record en regelt licenties, facturatie, btw, resellers en betaling voor 15% commissie [F]. Ontwikkelaars installeren en betalen vanuit de IDE.

**Validatie.** De marketplace en de licentie-infrastructuur zijn bewezen en de commissie kan contractueel niet boven 25% [F]. Openbare omzetcijfers van indie-plugins vond ik niet; dat is een zwakte in het bewijs.

**Concurrentie.** Weinig betaalde plugins per niche, maar AI-codeassistenten (inclusief JetBrains AI) maken een deel van de klassieke "productiviteitsplugins" overbodig. Kansen liggen in tooling voor specifieke frameworks, talen of bestandsformaten en in integraties.

**Prijs.** €3–€5/mnd persoonlijk, €10–€20/mnd organisatie [A].

**Prognose:**

| Scenario | €2.500/mnd | €10.000/mnd |
|---|---|---|
| Conservatief | 709 betalende licenties, ~8 plugins | 2.737 licenties, 28 plugins |
| Realistisch | 443 licenties, 2 plugins | 1.711 licenties, 6 plugins |

**Automatisering.** Claude Code schrijft Kotlin/Java met het IntelliJ Platform Gradle Plugin. Tests draaien headless; publicatie gaat via `publishPlugin` naar de Marketplace API. Ongeveer 75% automatiseerbaar. Elke IDE-release (3× per jaar) vraagt compatibiliteitsupdates; dat is goed te automatiseren met `verifyPlugin`.

**Risico.** De markt is kleiner dan Atlassian en de omzet per klant is ~10× lager (individuele licenties tegenover bedrijfslicenties per site). Hetzelfde sherlocking-risico door JetBrains AI.

---

## Deel 4: De winnaar: Atlassian Forge micro-app-fabriek

**Waarom dit wint:**

| Eis | Atlassian Forge micro-apps |
|---|---|
| Faceless | ✅ Handelsnaam en schriftelijk contact; geen gezicht of persoonlijk merk |
| Geen klantgesprekken | ✅ Self-service trial → betaling; enterprise-procurement loopt via Atlassian en resellers |
| Geen cold outreach | ✅ Koopintentie in de in-product Marketplace en publieke featureverzoeken |
| Geen traditionele marketing | ✅ Marketplace-zoekfunctie, categorieën en "trending"; geen ads of social nodig |
| Maximale automatisering | ✅ ~75–80% (zie tabel Deel 5); bouwen, testen, deployen, rapporteren |
| Automatische betaling en levering | ✅ Atlassian factureert, int, licenseert en installeert direct in de klantsite |
| Weinig support | ⚠️ Schriftelijke support is verplicht (redelijke inspanning; 24u-werkdag-SLA alleen met badge) [F] |
| Internationaal schaalbaar | ✅ Wereldwijde Atlassian-klantbasis; Atlassian is merchant of record |
| Opstart €0–€1.000 | ✅ Forge en dev-sites gratis; ~€100–€300 voor domein, helpdesk en KvK |
| Geen persoonlijke reputatie nodig | ✅ App-reviews in plaats van persoonlijk merk |

**Waarom de andere kandidaten verliezen:**
- **Apify:** sneller geld en meer automatisering, maar ~100–1.000× minder omzet per product en meer onderhoud per euro (scrapers breken). Wél waardevol als tweede motor.
- **JetBrains:** dezelfde mechaniek, maar een kleinere markt en lagere prijzen per klant.
- **MQL5:** omzet mogelijk, maar het klimaat is giftig (scams, gekochte reviews, chargebacks) en klanten verwachten tradingresultaten. Elk verlies wordt jouw supportticket.
- **3D-print/laser en Framer:** lage prijzen en hoge kopieerbaarheid; je concurreert met een AI-vloed.
- **Game-engine-tools:** Fab-gemiddelde ≈ $1.200/publisher/jaar [E]; de helft van de omzet komt uit sales-events [S].
- **Booth/VRChat:** hoge groei, maar het vakwerk is niet automatiseerbaar en kopers zijn AI-kritisch.
- **Shopify:** grote markt, maar de supportcultuur staat haaks op je eisen.
- **Google Workspace en Chrome:** installs zijn niet hetzelfde als omzet (een add-on met 3.000 installs en $0 omzet [S]) en je moet zelf betalingen inbouwen.

**De eerlijke kanttekening:** dit is minder "passief" dan een Etsy-winkel in het eerste jaar. De eerste 2–3 maanden kosten ~10–15 uur/week aan review, validatie en listing. Daarna verschuift het naar ~4–8 uur/week, terwijl de omzet per app (terugkerend, bedrijfsklanten) een orde groter is dan bij elk asset-model.

---

## Deel 5: Concreet bouwplan

### Automatiseringsontwerp (de "fabriek")

```
[1 Vraag-mining]  atlassian_opportunity_scan.py (wekelijks, cron)
   votes op onopgeloste suggesties  ×  marketplace-aanbod (aantal apps, installs, reviews)
   + 1–3★ reviews van concurrerende apps (Marketplace API) = onvervulde wensen
        ↓  gerankte backlog (CSV/MD)
[2 Spec]  Claude schrijft PRD + prijsvoorstel  →  JIJ keurt goed (15 min)
        ↓
[3 Bouw]  Claude Code: forge create → UI Kit/Custom UI → Jest unit-tests → forge deploy (dev)
        ↓
[4 QA]    forge lint · tests · Playwright e2e op gratis Atlassian dev-site · screenshots
          security-checklist (geen egress = "Runs on Atlassian"-geschikt)  →  JIJ klikt 20 min door
        ↓
[5 Publicatie]  forge deploy -e production · listing-tekst + screenshots auto-gegenereerd
                Marketplace-listing indienen via partnerportal (JIJ, ~1 u per app)
        ↓
[6 Verkoop/betaling/levering]  Atlassian: trial, factuur, btw, licentie (context.license), installatie
        ↓
[7 Support]  Jira Service Management Free (helpdesk) + kennisbank
             Claude stelt antwoord op uit docs + code → JIJ verstuurt (5 min/ticket)
        ↓
[8 Updates]  Dependabot + Atlassian-deprecatiemeldingen → Claude Code-taak → tests → deploy
        ↓
[9 Rapportage]  Marketplace Reporting API (sales, licenties, churn, evaluaties) → wekelijks dashboard/e-mail
```

| Onderdeel | Volledig automatisch | AI met menselijke controle | Zelf | % autom. |
|---|---|---|---|---|
| 1 Kansen vinden | Scan en ranking | Selectie top-3 | Eindkeuze | 85% |
| 2 Product ontwikkelen | Scaffold, code, tests | Spec en UX-keuzes | Goedkeuring | 80% |
| 3 Kwaliteitscontrole | Lint, unit, e2e, screenshots | Security-checklist | Doorklikken | 75% |
| 4 Publiceren | Deploy, listingtekst, beelden | — | Indienen in portal, partnerprofiel | 60% |
| 5 Verkopen | Atlassian (trial → betaald) | — | — | 100% |
| 6 Betalingen | Atlassian | — | Bank/belasting (jaarlijks) | 95% |
| 7 Levering | Atlassian-installatie, licentiecheck | — | — | 100% |
| 8 Updates | Dependency-bumps, tests, deploy | Fixes bij platformwijzigingen | Goedkeuring | 70% |
| 9 Vragen | Kennisbank, auto-reply | AI-conceptantwoorden | Verzenden/escalatie | 60% |
| 10 Tracking | Reporting API → rapport | — | Wekelijks lezen (10 min) | 95% |
| **Gewogen geheel** | | | | **≈ 78%** |

Technische haalbaarheid (geverifieerd in deze sessie):
- De Marketplace REST API v2 en de publieke Jira-tracker-API zijn zonder login bereikbaar (scan gedraaid op 3 nov 2026).
- Forge ondersteunt betaalde apps alleen als "Paid via Atlassian" [F]. Licentiecontrole loopt via de Forge-licentiecontext.
- Niet geautomatiseerd: het indienen van listings en het partnerprofiel (handmatige portal-stappen). Dat reken ik als werk voor jou.

### Week 1: Marktvalidatie en definitieve selectie
1. Draai `python income_lab/models/atlassian_opportunity_scan.py --n 200`. Eerste run (n=40): `research/atlassian_opportunities_2026-11-03.md`.
2. Voeg toe: Confluence-, JSM- en Data-Center-only-apps zonder Cloud-versie. Die laatste zijn migratiekansen; het zijn apps met veel DC-installs zonder Cloud-hosting.
3. Haal per top-20-kans de concurrerende apps op (installs, reviews, prijs, laatste update) en lees hun 1–3★-reviews.
4. Kies 3 kansen op deze criteria:
   - ≥500 stemmen of duidelijk DC→Cloud-gat;
   - beste concurrent <1.500 installs of rating <3,8;
   - bouwbaar in Forge zonder externe server;
   - niet iets wat Atlassian op de publieke roadmap heeft staan.
5. Juridisch: KvK-handelsnaam (of BV-afweging), zakelijke rekening, en Atlassian-partneraccount aanmaken. Verifieer de voorwaarden voor betaalde listings [A].

### Week 2: Productontwikkeling en automatiseringsarchitectuur
- Repo-structuur: `apps/<app>/` (Forge), gedeelde UI-componenten, CI (lint/test/deploy).
- Gratis Atlassian cloud-developer-sites voor Jira en Confluence. Playwright-e2e-harnas.
- Bouw app #1 (MVP: één kernfunctie, instellingenpagina, docs). Claude Code bouwt; jij reviewt.
- Helpdesk (JSM Free), kennisbank-skelet, privacybeleid en EULA (template), supportadres op de handelsnaam.

### Week 3: Technische implementatie en eerste publicaties
- App #1 af: tests groen, security-checklist, screenshots en demo-gif automatisch gegenereerd.
- Indienen als **Paid via Atlassian**, met gratis tier ≤10 gebruikers.
- Start app #2 (en #3 als de bouw meevalt).
- Rapportage-pipeline: Marketplace Reporting API → wekelijks overzicht.

### Week 4: Lancering, kwaliteitscontrole en eerste metingen
- Verwerk feedback uit de Marketplace-review en publiceer.
- Meet dagelijks: listing-views, installs, trials en eerste supportvragen. Leg alles vast in `analytics/`.
- App #2 indienen.
- Retrospectief: bouwtijd per app, wat de AI fout deed, welke stappen nog handwerk zijn.

### Eerste 90 dagen

| Periode | Doel | Meetpunt om door te gaan |
|---|---|---|
| Dag 1–30 | 2 apps live, fabriek staat | Listings goedgekeurd; ≥20 installs per app |
| Dag 31–60 | App #3–#4; eerste trials → betalend | ≥5 betalende sites in totaal; supportlast <2 u/week |
| Dag 61–90 | App #5–#6; prijs-/tierexperimenten; eerste uitbetaling | ≥$500 MRR; ≥1 app met >50 installs/maand |
| **Stop/pivot-regel** | Als na dag 90 <10 betalende sites en <100 installs totaal | Stop met bouwen. Herbekijk de nichekeuze of zet de fabriek in op Apify (#2), met dezelfde vaardigheden |

---

## Deel 6: Lange termijn: groeipad

| Niveau winst/mnd | Wat er nodig is (realistisch scenario) | Tijdlijn [E] | Uren/week |
|---|---|---|---|
| **€1.000** | ~16 betalende sites; 1–2 succesvolle apps (3–6 gelanceerd) | 4–9 maanden | 4–6 |
| **€5.000** | ~75 sites; 1–2 sterke apps (3–6 gelanceerd) | 9–18 maanden | 5–6 |
| **€10.000** | ~150 sites; 2–3 sterke apps | 12–24 maanden | 6–8 |
| **€25.000** | ~360 sites; 4–5 sterke apps (≈12 gelanceerd) | 2–3 jaar | 10–13 (overweeg een freelance supportmedewerker) |
| **€50.000** | ~720 sites; 7+ sterke apps (≈20 gelanceerd); 17% commissie na $1M | 3–4 jaar | 15–20 of support uitbesteed |

**Ja, groei gaat grotendeels door meer van hetzelfde toe te voegen**, maar niet lineair:
- **Meer apps** (dezelfde fabriek): de belangrijkste hefboom. Elke nieuwe app hergebruikt componenten, tests en listing-automatisering.
- **Meer producten**: Jira → Confluence → JSM → Bitbucket/Compass. Dezelfde klanten, andere vragen.
- **Rovo/AI-acties** bovenop bestaande apps: vroege categorie, minder concurrentie.
- **DC→Cloud-vervangers** (2027–2029): gericht apps bouwen voor wat migrerende klanten missen.
- **Tweede motor: Apify (#2)**. Dezelfde Claude-Code-fabriek, andere marktplaats, sneller geld; een hedge tegen Atlassian-afhankelijkheid.
- **Derde motor: JetBrains (#3)**. Dezelfde mechaniek (marketplace als merchant of record).
- **Exit-optie:** Atlassian-apps worden structureel opgekocht door roll-ups. Numbered Headings van het Nederlandse Avisi is nu Appfire [F: Marketplace API]. Multiples heb ik niet onafhankelijk kunnen verifiëren.

**Wat de groei begrenst (eerlijk):**
1. Support schaalt mee met klanten: ~1 u/week per 100 sites [E]. Boven ~€25k is een parttime supportmedewerker (schriftelijk, op afstand) logischer dan zelf doen.
2. De hitrate is onzeker. Het realistische scenario neemt aan dat 1 op 3 apps volwassen wordt; als dat 1 op 5 is, verdubbelt het aantal te bouwen apps.
3. Eén platform. Spreid na €5k/mnd naar een tweede marktplaats.

---

## Bijlage A: Belangrijkste bronnen

**Atlassian**
- Marketplace-commissie 2026 en 0%-incentive: [Atlassian blog](https://www.atlassian.com/blog/developer/updates-to-marketplace-revenue-share-2026), [verlengde tijdlijn](https://www.atlassian.com/blog/developer/extended-timelines-for-marketplace-revenue-share-changes), [pricing FAQ](https://developer.atlassian.com/market/faqs/pricing-payment-billing)
- Marketplace ~$1,8 mrd: [Aventis Advisors](https://aventis-advisors.com/atlassian-marketplace-ma/)
- Data Center EOL: [Atlassian cloud-migration](https://www.atlassian.com/cloud-migration), [Adaptavist](https://www.adaptavist.com/blog/atlassian-data-center-end-of-life-march-2029)
- Support-, security- en badge-eisen: [Atlassian Trust Marketplace](https://www.atlassian.com/trust/marketplace), [app-approval guidelines](https://developer.atlassian.com/platform/marketplace/app-approval-guidelines/), [listing Forge apps](https://developer.atlassian.com/platform/marketplace/listing-forge-apps/)
- Indie-voorbeeld: [Agile Docs $4.149 MRR](https://www.indiehackers.com/post/reaching-4149-mrr-in-the-atlassian-marketplace-a3cc93a067)
- Live data: `https://marketplace.atlassian.com/rest/2/addons` en `https://jira.atlassian.com/rest/api/2/search` (opgevraagd 3 nov 2026)

**Apify**
- [partnerpagina ($1,7M/mnd, 5.600 devs)](https://apify.com/partners/actor-developers), [monetisatie-hulp](https://help.apify.com/en/articles/8684010-make-money-publishing-your-actors-on-apify-store), [hoe de Store werkt](https://docs.apify.com/academy/actor-marketing-playbook/store-basics/how-store-works), [x402](https://docs.apify.com/platform/integrations/x402), [Store](https://apify.com/store)
- Nieuwkomers: [Vinted-actor $200/mnd](https://dev.to/boo_n/3-months-shipping-my-first-apify-actor-64-users-200mo-and-everything-i-got-wrong-52i7), [13 Koreaanse scrapers](https://dev.to/sessionzero_ai/after-10000-why-i-stopped-building-and-started-marketing-1c5o), [analyse](https://www.reinventing.ai/blog/apify-actor-passive-income)

**JetBrains, MQL5, Fab, Roblox, Unity, Shopify, Setapp**
- [JetBrains revenue sharing](https://plugins.jetbrains.com/docs/marketplace/revenue-sharing-and-fees.html)
- [MQL5 Market verkopen](https://www.metatrader5.com/en/terminal/help/market/market_sell)
- Fab: [Epic](https://www.unrealengine.com/en-US/blog/fab-content-marketplace-launches-in-october-publishing-portal-opens-today), [12-maanden-retrospectief](https://www.strayspark.studio/blog/fab-marketplace-12-month-retrospective-seller-2026)
- [Roblox Creator Store USD](https://devforum.roblox.com/t/creator-store-buy-and-sell-plug-ins-with-real-world-currency/2923445)
- [Unity AI-beleid](https://support.unity.com/hc/en-us/articles/16456407029524)
- [Shopify revenue share](https://shopify.dev/apps/store/revenue-share)
- [Setapp](https://docs.setapp.com/docs/distributing-revenue)

**Afgewezen markten**
- CGTrader AI-aandeel: [CGTrader forum/help](https://help.cgtrader.com/hc/en-us/sections/46191136402321-Platform-Terms-Changes-2026)
- Etsy-AI-vloed: [findskill/DC360-verwijzing](https://findskill.ai/blog/etsy-sellers-ai-listings-flood-3-question-audit/)
- [Canva AI-verbod](https://www.canva.com/help/updates-to-contributor-agreement-jan-2026/)
- [Spotify 75M](https://betanews.com/2025/09/26/spotify-removes-75-million-spam-tracks-and-introduces-stronger-ai-rules/)
- [KDP 3/dag](https://authorsguild.org/news/amazon-adds-to-kdp-generative-ai-policy-caps-daily-self-publishing-uploads/)
- [Contentsites/AI Overviews](https://digiday.com/media/how-ais-hit-to-publisher-traffic-is-quietly-rewiring-media-ma)
- x402-realiteit: [TechFlow/Chainalysis-analyse](https://www.techflowpost.com/en-US/article/34585)
- [MCP-monetisatie](https://dev.to/t49qnsx7qtkpanks/15000-mcp-servers-97m-monthly-downloads-and-almost-no-one-getting-paid-4g7b)
- [ChatGPT apps](https://openai.com/blog/developers-can-now-submit-apps-to-chatgpt)
- [Envato 50%](https://purethemes.net/envato-author-exclusivity-merchant-of-record/)
- [Booth 3D ¥10,4 mrd](https://www.gamebusiness.jp/article/2026/02/07/26157.html)
- [Framer creator program](https://www.framer.com/help/articles/how-the-creator-program-works/)
- [Civitai 2026](https://civitai.com/articles/33294/the-2026-creator-program-the-full-picture)
- [Amazon AI-merch](https://techcrunch.com/2026/06/08/amazon-now-lets-you-design-custom-merch-using-ai/)
- [Meta v. Bright Data](https://techcrunch.com/2024/01/24/court-rules-in-favor-of-a-web-scraper-bright-data-which-meta-had-used-and-then-sued)
- Google Sheets add-ons: [postmortem 3k installs/$0](https://hn.jakechampion.name/reader/https://developerwithacat.com/blog/202606/google-sheets-forecasting/), [Sync2Sheets $9k MRR](https://www.starterstory.com/stories/sync2sheets-give-notion-the-superpowers-of-google-sheets)

## Bijlage B: Onzekerheden die je in week 1 moet toetsen
1. Partnervoorwaarden voor betaalde Forge-apps voor een Nederlandse eenmanszaak of BV (identiteit en belasting) [A].
2. De werkelijke verhouding installs : betalende sites bij vergelijkbare apps. Installs omvatten trials en de gratis ≤10-gebruikerstier, dus 1.400 installs ≠ 1.400 betalers.
3. De Forge-quota en -kosten bij groei (het gratis gebruik is ruim, maar check de actuele limieten) [A].
4. De gemiddelde prijs per site in de gekozen niche (ijk aan 3–5 concurrenten).
5. De doorlooptijd van de Marketplace-review voor betaalde apps.
