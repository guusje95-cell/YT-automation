# Research log — Autonomous Online Income Lab (started 2026-11-03)
Labels: **[F]** fact from a primary/official source · **[S]** secondary source (blog/aggregator) · **[E]** my estimate · **[A]** assumption.

## Apify Store (Actors / scrapers / agent tools)
- [F] apify.com/partners/actor-developers (fetched 2026-11-03): "$1.7M paid out last month", 5,600 community developers, 108,508 Actors, 10k+ signups/day; Actors exposed "via API and MCP" (Claude, Cursor, Windsurf).
- [F] help.apify.com art. 8684010: pricing models pay-per-event / pay-per-result / pay-per-usage / rental; Apify keeps 20% (PPE/PPR: 20% of profit after platform costs); monthly payout; top independent creators ">$10,000 MRR", "many >$1,000/month".
- [S] reinventing.ai: earlier partner page said $1.4M/month, ~3,000 devs; avg ≈ $300–470/dev/month, highly skewed; rentals retired (listing stop 2026-04-01, full retirement 2026-10-01); store prices typically $1–10 per 1,000 results; maintenance 5–10 h per quarter per stable portfolio (Apify staff), Apify docs suggest ~2 h/week.
- Derived [E]: $1.7M / 5,600 = ~$304 average per developer per month → median far lower. Store grew ~2x in Actors (54k → 108k) in ~1 year → competition rising fast.

## Fab (Epic)
- [F] Epic blog/GameDeveloper: 88/12 revenue share. AI-made content must be tagged "CreatedWithAI". [S] strayspark retrospective: fees before split on some paths.

## Etsy
- [S] 2026: $0.20 listing, 6.5% transaction, ~3% + $0.25 processing (varies by country); offsite ads 12–15% when triggered. AI-assisted digital downloads allowed with disclosure ("designed by seller"); Oct-2026 tightening per secondary blogs.

## MakerWorld (Bambu Lab)
- [F] Exclusive Model Program: points convertible to cash, requires ≥100 accumulated prints; no direct paid one-off sales found (forum feature request only).

## Developer/app marketplaces
- [F] JetBrains Marketplace: commission 15% of list price (dev 85%), JetBrains handles licensing/billing/VAT; paid plugins need approval request.
- [F] Atlassian Marketplace: Forge apps 0% rev-share until $1M lifetime Forge revenue (from 2026-01-01); standard Forge share 84% → 83% from 2026-10-01; Connect 75%.
- [F] Shopify App Store: 0% on first $1M lifetime revenue (since 2025), 15% above. Known for heavy merchant support load (see Reddit notes).
- [F] MQL5 Market (MetaTrader): 20% commission, min price $30; [promo, undated] top-10 sellers $15k–100k/month; [S] ~11,000 transactions/30 days.
- [F] Setapp: 70% of usage-weighted pool, curated acceptance; Setapp Mobile shut 2026-02-16.
- [S] Chrome Web Store: no native payments since 2020; ExtensionPay/Stripe; most extensions <100 users.
- [F] Roblox Creator Store: plugins/models sold in USD, ~100% minus processing/tax (18+, region limits).
- [F] Fab: 2025 creator earnings >$24M, >20,000 publishers, >420,000 listings (Epic YIR via strayspark) → avg ≈ $1,200/publisher/yr. Event sales ≈50% of monthly revenue; refunds 3–5%; AI must be labeled, buyers can hide AI.
- [S] Unity Asset Store: AI allowed with disclosure; no AI filter; 70/30 (publisher 70%) [A, standard historic].

## Creative marketplaces
- [S] Envato Market (ThemeForest/CodeCanyon): flat 50% author fee from 2026-07-01, exclusivity dropped. Elements: 50% subscription pool.
- [S] Gumroad: 10% + $0.50 direct; 30% on Discover sales; payout minimum raised to $100 (Mar-2026).
- [F] Canva contributor agreement Jan-2026: AI-generated content not permitted. Shutterstock: no AI submissions from contributors.
- [F] Adobe Stock accepts genAI (labelled); tiered royalties; per-download income low [S].
- [S] Cults3D: designer gets 80% net of VAT.
- [S] KDP: 3 new titles/day cap; AI-generated disclosure checkbox; enforcement rising.

## Internet assets
- [S] Content sites: Flippa 2025 content-site deals −33.5%; AIO-driven traffic losses (some publishers −90% Google referrals); multiples ~25–34x monthly profit only for stable traffic. Capital requirement >> €1k.

## AI-agent economy
- [S] x402: ~140–165M cumulative tx, ~$40–50M settled, avg ≈ $0.30/tx; TRM: genuine agentic spend only 0.6–7.5% of volume; CoinDesk Mar-2026 ~$28k/day. → real but tiny, early.
- [S] Paid MCP servers: <5% earn anything; marketplaces (MCPize 15%, Agent Bazaar 18%) tiny. Apify is the only agent-tool marketplace with proven payouts at scale.
- [F] ChatGPT App Directory (Dec-2025): no built-in digital goods payments announced.
- [S] RapidAPI (Nokia since Nov-2024): 20% fee, low organic discovery, reputation of declining marketplace.

## Extra evidence (batch 3–4)
- [F] Apify Store page (fetched 2026-11-03): 108k+ Actors; Google Maps Scraper 680K users, Instagram Scraper 465K, TikTok 379K, Google SERP 226K; long tail of category leaders 2.7K–37K users. Nearly all leaders use pay-per-event.
- [F] Apify docs: daily automated test (default input must succeed < 5 min); failing 3 days → maintenance flag + lower ranking; 30 days failing → auto-deprecated. Public Issues tab; response time shown as reliability metric. Store ranking ≈ quality score; same ranking feeds the Apify MCP server `search-actors` tool (agent distribution).
- [F] Apify x402 agentic payments (experimental): PPE Actors only, USDC on Base, min $1.
- [S] New-developer reality on Apify: 13 actors → ~$110–128 in first 15 days, 22 external accounts, Store search the dominant channel; 42 actors → first payout after 41 days; 1 Vinted actor → 64 lifetime users, ~$200/month net after 3 months; 35 scrapers → $0 after 90 days. Churn from silent failures.
- [F] Atlassian: Marketplace ≈ $1.8B sales 2024 (Aventis), ~19% CAGR since 2021, 8,000+ apps, ~1,800 partners. Data Center EOL 2029-03-28 (new DC sales stop ~2028-03-30) → forced cloud migration of enterprise customers. Support: "commercially reasonable efforts"; Cloud Fortified / Runs-on-Atlassian badge → 24h response SLA on weekdays. Forge paid apps only "Paid via Atlassian". Security requirements (EcoScanner, security bug-fix SLA).
- [S] Indie Atlassian evidence: Agile Docs $4,149 MRR after 18 months; Lizard Brain $1M lifetime by 2019 (solo start). Roll-ups (Appfire ~200 apps, Tempo) dominate top.
- [F] Booth.pm 3D-model category 2025: ¥10.4B GMV (+79% YoY), 7.74M orders, 281k buyers (Pixiv white paper via Real Sound/SBBIT).
- [S] CGTrader 2026: AI-generated items ≈ 1 in 6 new uploads but ≈ $1 of every $90 earned. TurboSquid does not accept AI-generated content. → Pure-AI 3D assets barely sell.
- [S] Etsy digital printables: human sellers lost ~40% monthly views Jan-2025→Jan-2026 as AI listings surged (Digital Commerce 360 via secondary). "laser cut svg": ~130,805 competing listings.
- [F] Framer Marketplace: creators keep 100% of paid template revenue; $537k paid out to creators in one month (Framer). [F] Notion Marketplace: Notion is merchant of record; waitlist.
- [S] Google Sheets add-ons: Sync2Sheets $9k MRR / 400+ payers (marketing-driven early); forecasting add-on 3,000 installs, $0 revenue → installs ≠ revenue.
- [S] iOS ASO-only utilities: typical tens–hundreds $/month; 97% of App Store revenue from IAP/subscriptions.
- [S] Civitai 2026 creator pool only $26.9k for June 2026 across all creators → reject.
- [S] Spotify removed 75M spam tracks; 1,000-stream threshold → AI music streaming reject.
- [S] Amazon launched AI merch designer for shoppers (2026-06-08) → POD designers get disintermediated.
- [S] Domain aftermarket sell-through 1–4%/yr; needs capital and holding fees → reject for €0–1k.
- [F] Meta v. Bright Data (N.D. Cal., Jan-2024): logged-off scraping of public data not a ToS breach; GDPR still applies to personal data in the EU → avoid personal-data scrapers.
