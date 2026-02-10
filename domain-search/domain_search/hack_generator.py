"""Domain hack generator - find creative domain hacks where the TLD forms part of a word."""

from dataclasses import dataclass


@dataclass
class DomainHack:
    domain: str
    visual: str


def find_suffix_hacks(word: str, tlds: list[str]) -> list[DomainHack]:
    """Find TLDs that match the end of the word.

    For example, if word is "kostick" and "ck" is a TLD, returns "kosti.ck"
    which visually reads as "kostick".
    """
    word_lower = word.lower()
    hacks = []
    for tld in tlds:
        if word_lower.endswith(tld) and len(tld) < len(word_lower):
            prefix = word_lower[: len(word_lower) - len(tld)]
            if prefix:  # must have at least one char before the dot
                domain = f"{prefix}.{tld}"
                visual = f"{prefix}{tld}"
                hacks.append(DomainHack(domain=domain, visual=visual))
    return hacks


def find_interior_hacks(word: str, tlds: list[str]) -> list[DomainHack]:
    """Find TLDs that appear anywhere within the word for creative splits.

    For example, if word is "sasha" and "sh" is a TLD, returns "sa.sh"
    which visually reads as "sash". We exclude suffix matches (handled separately)
    and only include cases where the TLD is NOT at the very end.
    """
    word_lower = word.lower()
    hacks = []
    seen = set()
    for tld in tlds:
        # Find all positions where the TLD appears (excluding suffix position)
        start = 0
        while True:
            pos = word_lower.find(tld, start)
            if pos == -1:
                break
            # Skip if this is a suffix match (handled by find_suffix_hacks)
            if pos + len(tld) == len(word_lower):
                start = pos + 1
                continue
            # Must have at least one char before the dot
            if pos > 0:
                prefix = word_lower[:pos]
                domain = f"{prefix}.{tld}"
                if domain not in seen:
                    visual = f"{prefix}{tld}"
                    hacks.append(DomainHack(domain=domain, visual=visual))
                    seen.add(domain)
            start = pos + 1
    return hacks


def generate_domain_hacks(word: str, tlds: list[str]) -> list[DomainHack]:
    """Generate all domain hacks for a word: suffix matches and interior matches.

    Returns a deduplicated list sorted by domain name.
    """
    suffix = find_suffix_hacks(word, tlds)
    interior = find_interior_hacks(word, tlds)

    seen = set()
    combined = []
    for hack in suffix + interior:
        if hack.domain not in seen:
            seen.add(hack.domain)
            combined.append(hack)

    return sorted(combined, key=lambda h: h.domain)
