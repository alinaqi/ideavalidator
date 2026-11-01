"""Business-category taxonomy. Classifying the idea's category up front fixes the comparison set
(which incumbents are real substitutes) and surfaces the category's normal business models — so
business-model innovation, not just product differences, is on the table. Used by the `classify` stage.
"""
from __future__ import annotations

from dataclasses import dataclass

# Generic business-model archetypes, so the classifier can propose model innovation, not only product.
MODELS = (
    "subscription (per-seat or flat)", "usage/metered (pay per unit)", "freemium / PLG",
    "open-core (OSS + paid)", "marketplace take-rate", "transaction/interchange fee",
    "licensing / OEM", "white-label / embedded B2B2C", "ads / sponsorship",
    "data monetization", "services / done-for-you", "outcome / performance-based",
    "credits / prepaid packs", "hardware + consumables", "community / membership",
)


@dataclass(frozen=True)
class Category:
    key: str
    name: str
    description: str
    incumbents: str          # the kind of players a real substitute would be
    models: tuple            # business models that commonly work in this category
    validation_note: str     # how to judge it / what regime applies


CATEGORIES = (
    Category("dev_tools_api", "Developer tools / API / SDK",
             "Tools, libraries, CLIs and APIs that developers build with.",
             "Stripe-style APIs, Postman, Vercel, Twilio, SDK vendors",
             ("usage/metered (pay per unit)", "freemium / PLG", "open-core (OSS + paid)", "per-seat"),
             "Judge on developer adoption funnel, time-to-first-call, docs, and usage expansion."),
    Category("infrastructure", "Infrastructure / platform / middleware",
             "Compute, storage, networking, data or orchestration layers others run on.",
             "AWS/GCP primitives, Cloudflare, Kafka/Confluent, Snowflake",
             ("usage/metered (pay per unit)", "subscription (per-seat or flat)", "open-core (OSS + paid)"),
             "Judge on reliability, switching cost, and gross margin at scale."),
    Category("ai_action_layer", "AI action-layer / agent connector (MCP, plugins, tools)",
             "Tools that give EXISTING AI assistants/agents new real-world abilities (BYO agent).",
             "MCP servers/connectors, ChatGPT/Claude plugins, agent tool vendors",
             ("usage/metered (pay per unit)", "credits / prepaid packs", "freemium / PLG",
              "white-label / embedded B2B2C"),
             "Distinct from standalone AI apps. Key risk: the host platform ships the ability natively "
             "(per-platform bundling). Judge on breadth of supported agents and defensibility vs bundling."),
    Category("vertical_saas", "Vertical SaaS",
             "Software for one industry's workflow end-to-end.",
             "Toast (restaurants), Procore (construction), vertical incumbents",
             ("subscription (per-seat or flat)", "transaction/interchange fee", "usage/metered (pay per unit)"),
             "Judge on workflow depth, industry ACV and sales motion fit."),
    Category("horizontal_saas", "Horizontal SaaS",
             "Cross-industry business software (CRM, PM, support, HR).",
             "Salesforce, Notion, Zendesk, HubSpot",
             ("subscription (per-seat or flat)", "freemium / PLG", "usage/metered (pay per unit)"),
             "Crowded; judge on wedge, differentiation and retention."),
    Category("plg_product", "PLG / freemium product",
             "Self-serve product that grows through usage and virality.",
             "Figma, Calendly, Loom",
             ("freemium / PLG", "subscription (per-seat or flat)", "usage/metered (pay per unit)"),
             "Judge on activation, free→paid conversion and viral/expansion loops, not outbound sales."),
    Category("marketplace", "Marketplace / two-sided network",
             "Matches supply and demand and takes a cut.",
             "Uber, Airbnb, Upwork, app stores",
             ("marketplace take-rate", "transaction/interchange fee", "subscription (per-seat or flat)",
              "ads / sponsorship"),
             "Judge on liquidity, cold-start, and take-rate vs disintermediation."),
    Category("directory_graph", "Directory / data graph / trust layer",
             "A catalog, graph or trust/reputation layer others rely on.",
             "Trustpilot, G2, Crunchbase, review/trust seals",
             ("subscription (per-seat or flat)", "ads / sponsorship", "data monetization",
              "freemium / PLG"),
             "Judge on coverage, data moat and the growth loop that compounds it."),
    Category("consumer_app", "Consumer app / subscription",
             "A standalone app people use directly (B2C).",
             "Duolingo, standalone AI apps, consumer subscriptions",
             ("subscription (per-seat or flat)", "freemium / PLG", "ads / sponsorship",
              "credits / prepaid packs"),
             "Judge on CAC vs LTV, retention and organic pull; emotional value counts."),
    Category("data_analytics", "Data / analytics product",
             "Data feeds, BI, or analytics as the product.",
             "Bloomberg, Databricks, BI vendors, data brokers",
             ("subscription (per-seat or flat)", "usage/metered (pay per unit)", "data monetization"),
             "Judge on data uniqueness, freshness and the decisions it changes."),
    Category("fintech_payments", "Fintech / payments",
             "Moving, lending, or managing money.",
             "Stripe, Plaid, Ramp, neobanks",
             ("transaction/interchange fee", "subscription (per-seat or flat)", "usage/metered (pay per unit)"),
             "Judge on regulation, unit economics of float/interchange and compliance."),
    Category("services_agency", "Services / agency / done-for-you",
             "Human-delivered (or human+AI) outcomes as a service.",
             "Agencies, consultancies, managed services",
             ("services / done-for-you", "outcome / performance-based", "subscription (per-seat or flat)"),
             "Judge on cash now, utilization and the path to a productized/repeatable offer."),
    Category("hardware", "Hardware / devices",
             "Physical products, possibly with software/consumables.",
             "Peloton, Oura, IoT device makers",
             ("hardware + consumables", "subscription (per-seat or flat)", "licensing / OEM"),
             "Judge on BOM/margin, supply chain and attach-rate of recurring revenue."),
    Category("open_core_oss", "Open-core / OSS",
             "Open-source core with paid hosting/enterprise.",
             "GitLab, HashiCorp, Elastic, Supabase",
             ("open-core (OSS + paid)", "usage/metered (pay per unit)", "subscription (per-seat or flat)"),
             "Judge on community adoption → paid conversion and the open/paid line."),
    Category("embedded_b2b2c", "Embedded / B2B2C / white-label",
             "Capability other companies embed and resell to their users.",
             "Twilio-in-apps, embedded finance, white-label vendors",
             ("white-label / embedded B2B2C", "usage/metered (pay per unit)", "licensing / OEM"),
             "Judge on partner distribution, integration depth and revenue share."),
    Category("content_media", "Content / media / creator",
             "Content, media or creator-economy products.",
             "Substack, YouTube, Patreon, media brands",
             ("subscription (per-seat or flat)", "ads / sponsorship", "community / membership"),
             "Judge on audience, cadence and monetization per subscriber."),
    Category("regtech_compliance", "RegTech / compliance",
             "Compliance, security attestation, and regulated workflows.",
             "Vanta, Drata, KYC/AML vendors",
             ("subscription (per-seat or flat)", "usage/metered (pay per unit)", "outcome / performance-based"),
             "Judge on regulatory tailwind, audit/attestation value and switching cost."),
)

_BY_KEY = {c.key: c for c in CATEGORIES}


def list_categories() -> tuple:
    return CATEGORIES


def get(key: str) -> Category:
    return _BY_KEY[key]


def catalog_for_prompt() -> str:
    """Compact catalogue to inject into the classify prompt: categories + model archetypes."""
    lines = ["CATEGORIES (pick the best primary + any secondary):"]
    for c in CATEGORIES:
        lines.append(f"- {c.key} — {c.name}: {c.description} Real incumbents: {c.incumbents}. "
                     f"Common models: {', '.join(c.models)}.")
    lines.append("\nBUSINESS MODEL ARCHETYPES (consider model innovation, not only product):")
    lines.append("- " + "; ".join(MODELS))
    return "\n".join(lines)
