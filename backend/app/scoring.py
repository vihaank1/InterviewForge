"""Transparent, configurable scoring and explicitly limited keyword checks."""
import re
from .schemas import Evaluation, DesignEvaluation

INTERVIEW_WEIGHTS = {'accuracy': .35, 'reasoning': .30, 'tradeoffs': .20, 'clarity': .15}
DESIGN_WEIGHTS = {'scalability': .35, 'reliability': .25, 'tradeoffs': .25, 'clarity': .15}


def weighted_score(rubric, weights: dict[str, float]) -> float:
    return round(sum(getattr(rubric, key) * weight for key, weight in weights.items()), 1)


def interview_score(evaluation: Evaluation) -> float:
    return weighted_score(evaluation.rubric, INTERVIEW_WEIGHTS)


def design_score(evaluation: DesignEvaluation) -> float:
    return weighted_score(evaluation.rubric, DESIGN_WEIGHTS)


# These are string-presence hints, NOT proof that a component is missing.
COMPONENT_PATTERNS = {
    'Caching not mentioned': r'\bcach(?:e|ing|ed)\b|\bredis\b|\bmemcached\b',
    'Load balancing not mentioned': r'\bload.balanc(?:e|er|ing)\b|\balb\b',
    'Replication/failover not mentioned': r'\breplicat(?:ion|ed|e)\b|\bfailover\b|\bmulti.region\b',
    'CDN not mentioned': r'\bcdn\b|\bcontent.delivery.network\b',
    'Async messaging not mentioned': r'\bqueue\b|\bkafka\b|\brabbitmq\b|\bpub.?sub\b|\bevent.bus\b'
}


def missing_component_hints(text: str) -> list[str]:
    return [label for label, pattern in COMPONENT_PATTERNS.items()
            if not re.search(pattern, text, flags=re.IGNORECASE)]


def progress_summary(rounds: list[dict]) -> dict:
    scores = [r['score'] for r in rounds]
    count = len(scores)
    recent = scores[-5:]
    first = scores[:5]
    weak_spots = []
    for r in rounds[-5:]:
        for spot in r.get('evaluation', {}).get('weak_spots', []):
            if spot not in weak_spots:
                weak_spots.append(spot)
    return {
        'completed_rounds': count,
        'average_score': round(sum(scores) / count, 1) if count else None,
        'recent_average': round(sum(recent) / len(recent), 1) if recent else None,
        'early_average': round(sum(first) / len(first), 1) if first else None,
        'weak_spots': weak_spots[:8]
    }
