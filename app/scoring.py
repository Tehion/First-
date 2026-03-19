from app.models import Lead


def compute_similarity(seed: dict, lead: Lead) -> float:
    """Compute similarity score (0.0-1.0) between a seed profile and a lead."""
    score = 0.0

    # Industry match: 0.3
    if seed.get("industry") and lead.industry:
        if seed["industry"].lower() == lead.industry.lower():
            score += 0.3

    # Location match: 0.2
    if seed.get("location") and lead.location:
        if seed["location"].lower() == lead.location.lower():
            score += 0.2

    # Company size proximity: 0.3
    seed_size = seed.get("company_size")
    if seed_size and lead.company_size:
        max_size = max(seed_size, lead.company_size, 1)
        proximity = 1 - min(abs(seed_size - lead.company_size) / max_size, 1.0)
        score += 0.3 * proximity

    # Tag overlap (Jaccard): 0.2
    seed_tags = set(t.lower() for t in seed.get("tags", []))
    lead_tags = set(t.lower() for t in lead.get_tags())
    if seed_tags and lead_tags:
        intersection = seed_tags & lead_tags
        union = seed_tags | lead_tags
        score += 0.2 * (len(intersection) / len(union))

    return round(score, 4)
