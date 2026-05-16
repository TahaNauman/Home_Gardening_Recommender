# ranker.py
# Takes the raw list of scored vegetables from scorer.py
# and organises them into "plant now", "avoid", and "borderline" groups.

from src.utils.config import SCORE_EXCELLENT, SCORE_GOOD, SCORE_MARGINAL
from src.utils.helpers import get_score_label


def rank_results(scored_list: list) -> dict:
    """
    Sorts and splits scored vegetables into three groups.

    Parameters:
        scored_list : list of dicts returned by score_all_vegetables()

    Returns a dict with keys:
        - 'recommended'  : score >= 60, sorted best first
        - 'borderline'   : score 40–59, sorted best first
        - 'avoid'        : score < 40,  sorted worst first
        - 'all_sorted'   : everything sorted best to worst
    """

    # Attach the display label to each result
    for item in scored_list:
        item['label'] = get_score_label(item['score'])

    # Sort all results from highest to lowest score
    all_sorted = sorted(scored_list, key=lambda x: x['score'], reverse=True)

    recommended = [v for v in all_sorted if v['score'] >= SCORE_GOOD]
    borderline  = [v for v in all_sorted if SCORE_MARGINAL <= v['score'] < SCORE_GOOD]
    avoid       = [v for v in all_sorted if v['score'] < SCORE_MARGINAL]

    return {
        'recommended' : recommended,
        'borderline'  : borderline,
        'avoid'       : sorted(avoid, key=lambda x: x['score']),  # worst first
        'all_sorted'  : all_sorted,
    }


def top_picks(ranked: dict, n: int = 5) -> list:
    """Returns the top N recommended vegetables."""
    return ranked['recommended'][:n]


def must_avoid(ranked: dict, n: int = 5) -> list:
    """Returns the N most unsuitable vegetables."""
    return ranked['avoid'][:n]