"""Heuristic extraction of external-service and pricing metadata."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from loom.models.service_metadata import (
    PricingFactWrite,
    ServiceDependencyWrite,
    ServiceSetupRequirementWrite,
)

URL_RE = re.compile(r"https?://[^\s)>\"]+")
ENV_VAR_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
PRICE_RE = re.compile(r"~?\$([0-9]+(?:\.[0-9]+)?)")


def _root_domain(hostname: str) -> str:
    host = hostname.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def extract_service_metadata(
    *,
    skill_content: str,
    source_uri: str | None,
) -> tuple[
    list[ServiceDependencyWrite], list[PricingFactWrite], list[ServiceSetupRequirementWrite]
]:
    """Heuristically extract external-service and pricing metadata from content."""
    urls = [url.rstrip(".,)") for url in URL_RE.findall(skill_content)]
    if source_uri:
        urls.append(source_uri)

    lines = [line.strip() for line in skill_content.splitlines() if line.strip()]
    source_domain = _root_domain(urlparse(source_uri).netloc) if source_uri else None
    domain_scores: dict[str, int] = {}
    domains: list[str] = []
    docs_urls: dict[str, str] = {}
    for url in urls:
        parsed = urlparse(url)
        if not parsed.netloc:
            continue
        domain = _root_domain(parsed.netloc)
        if not domain or domain == "github.com":
            continue
        if domain not in domains:
            domains.append(domain)
        docs_urls.setdefault(domain, url)
        score = 0
        if source_domain and domain == source_domain:
            score += 3
        for line in lines:
            if url not in line and domain not in line:
                continue
            if re.search(
                (
                    r"\bsign up\b|\bcreate account\b|\bapi key\b|"
                    r"\bpricing\b|\bcost\b|\bcredits?\b|\bpay-as-you-go\b"
                ),
                line,
                flags=re.IGNORECASE,
            ):
                score += 3
            if "youtube" in line.lower():
                score += 1
        domain_scores[domain] = domain_scores.get(domain, 0) + score

    env_vars = sorted(
        {
            match
            for match in ENV_VAR_RE.findall(skill_content)
            if any(token in match for token in ("API_KEY", "TOKEN", "SECRET", "CLIENT_ID"))
        }
    )
    has_signup = bool(
        re.search(r"\bsign up\b|\bcreate account\b", skill_content, flags=re.IGNORECASE)
    )
    has_billing = bool(
        re.search(
            r"\bcredits?\b|\bbilling\b|\bpay-as-you-go\b|\bpaid\b",
            skill_content,
            flags=re.IGNORECASE,
        )
    )

    price_lines: list[str] = []
    explicit_price_lines: list[str] = []
    for line in lines:
        if PRICE_RE.search(line) or re.search(
            r"\bpricing\b|\bcost\b|\bcredits?\b", line, flags=re.IGNORECASE
        ):
            price_lines.append(line)
        if PRICE_RE.search(line):
            explicit_price_lines.append(line)

    if domain_scores:
        top_score = max(domain_scores.values())
        if top_score > 0:
            domains = [domain for domain in domains if domain_scores.get(domain, 0) == top_score]

    indicative_cost: float | None = None
    price_text: str | None = None
    pricing_facts: list[PricingFactWrite] = []
    descriptive_price_lines = [line for line in price_lines if not line.lstrip().startswith("#")]
    if explicit_price_lines:
        price_text = explicit_price_lines[0]
    elif descriptive_price_lines:
        price_text = descriptive_price_lines[0]
    if price_text:
        match = PRICE_RE.search(price_text)
        if match:
            indicative_cost = float(match.group(1))
        pricing_facts.append(
            PricingFactWrite(
                fact_type="unit_cost" if indicative_cost is not None else "billing_model",
                pricing_model="credits" if "credit" in price_text.lower() else "usage_based",
                operation_name="youtube_search" if "youtube search" in price_text.lower() else None,
                unit_name="request" if "search" in price_text.lower() else None,
                unit_cost_usd=indicative_cost,
                currency="USD" if "$" in price_text else None,
                price_text_raw=price_text,
                price_structured={"raw_line": price_text},
                source_kind="artifact",
                source_uri=docs_urls[domains[0]] if domains else source_uri,
                evidence_snippet=price_text,
                confidence=0.75 if indicative_cost is not None else 0.5,
            )
        )

    dependencies: list[ServiceDependencyWrite] = []
    setup_requirements: list[ServiceSetupRequirementWrite] = []

    for domain in domains:
        dependency = ServiceDependencyWrite(
            service_key=domain,
            display_name=domain,
            vendor_name=domain,
            service_type="api" if env_vars or "api" in skill_content.lower() else "saas",
            homepage_url=f"https://{domain}",
            docs_url=docs_urls.get(domain),
            pricing_url=next(
                (url for url in urls if domain in url and "pricing" in url.lower()), None
            ),
            default_auth_methods=["api_key"] if env_vars else [],
            default_env_vars=env_vars,
            required=True,
            dependency_role="primary_runtime",
            operations=["youtube_search"] if "youtube search" in skill_content.lower() else [],
            pricing_summary={
                "pricing_model": "credits"
                if has_billing
                else ("usage_based" if price_text else "unknown"),
                "requires_paid_account": has_billing or has_signup,
                "indicative_unit_cost_usd": indicative_cost,
                "price_text": price_text,
            },
            evidence_summary={
                "detected_from": "skill_content",
                "matched_urls": [url for url in urls if domain in url],
                "env_vars": env_vars,
            },
        )
        dependencies.append(dependency)

        if has_signup:
            setup_requirements.append(
                ServiceSetupRequirementWrite(
                    service_key=domain,
                    requirement_type="account",
                    instructions=f"Create an account with {domain} before using this skill.",
                    evidence_summary={"source": "skill_content", "signal": "sign up"},
                )
            )
        if has_billing:
            setup_requirements.append(
                ServiceSetupRequirementWrite(
                    service_key=domain,
                    requirement_type="billing",
                    instructions="Add credits or enable billing before running the skill.",
                    evidence_summary={"source": "skill_content", "signal": "credits_or_billing"},
                )
            )
        for env_var in env_vars:
            setup_requirements.append(
                ServiceSetupRequirementWrite(
                    service_key=domain,
                    requirement_type="env_var",
                    key=env_var,
                    value_hint="api_key",
                    instructions=f"Set the {env_var} environment variable.",
                    evidence_summary={"source": "skill_content", "signal": env_var},
                )
            )
            setup_requirements.append(
                ServiceSetupRequirementWrite(
                    service_key=domain,
                    requirement_type="api_key",
                    key=env_var,
                    value_hint="api_key",
                    instructions=(
                        "Acquire an API key from the provider and configure it for this skill."
                    ),
                    evidence_summary={"source": "skill_content", "signal": env_var},
                )
            )

    return dependencies, pricing_facts, setup_requirements
