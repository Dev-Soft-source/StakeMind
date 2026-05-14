# Growth (post-MVP)

Plan for **public presence**, **education**, and **community** once core product trust signals are in place. This is intentionally lightweight so execution stays aligned with shipping, not vanity metrics.

## Landing and public docs

| Track | Goal | Concrete steps |
|-------|------|----------------|
| **Landing** | Explain value in one screen, route to app or waitlist | Hero (validator intelligence + staking context), 3 benefit bullets, screenshot or short loop, primary CTA (open app / join waitlist), secondary CTA (docs), footer with legal + GitHub |
| **SEO / share** | Discoverability for “BitTensor staking” / “TAO validator” queries | Stable page titles, meta description, Open Graph image, one canonical URL per page |
| **Docs site** | Self-serve for integrators and researchers | Public API overview (link to OpenAPI), glossary (hotkey, subnet, RAO), “How scoring works” (link to `docs/phase4/scoring-and-risk.md` or successor), FAQ on non-custodial model (`docs/security-and-trust.md`) |

Reuse existing repo docs where possible; add a small **public** `/docs` or marketing site only when you are ready to maintain it.

## Validator research content

Aim for **trust** and **originality**, not volume.

| Content type | Audience | Notes |
|--------------|----------|--------|
| **Subnet snapshot** (monthly) | Delegators | 1–2 pages: notable subnet themes, risks, no investment advice |
| **Methodology deep-dive** | Technical users | How rollups and scores are built; limitations front and center |
| **Release notes** tied to product | Everyone | What changed in explorer, risk bands, automation—honest limitations |

**Template for a research note**

1. Context (subnet / time window, data source).  
2. What we measured (metrics from the app).  
3. What we did *not* measure.  
4. How to verify (links to chain explorers, RPC).  
5. Disclaimer (not financial advice; past performance ≠ future results).

Store drafts in-repo (e.g. `docs/content/drafts/`) or in CMS later.

## Community channels

| Channel | Purpose | Launch checklist |
|---------|---------|------------------|
| **GitHub** (`github.com/<org>/StakeMind` or public fork) | Issues, discussions, transparency | README badges, `CONTRIBUTING.md`, issue templates (bug / feature), security contact |
| **Discord** | Support, power users, announcements | Rules channel, mod bot basics, bridge from GitHub releases |
| **X (Twitter)** | Short updates, links to posts | Bio → canonical site; pin roadmap or safety thread |
| **BitTensor ecosystem** | Alignment with subnet and validator culture | Participate in relevant Discords / forums; avoid spamming links; lead with education |

**Cadence (suggested):** ship notes when the product changes; avoid empty “we’re building” threads unless paired with a demo or doc.

## Related

- [BUILD_TODO.md](BUILD_TODO.md) — Growth section tracks this bucket.  
- [security-and-trust.md](security-and-trust.md) — Messaging must stay consistent with custody and data claims.  
- [deployment-and-operations.md](deployment-and-operations.md) — When growth traffic arrives, staging and monitoring should already be in place.
