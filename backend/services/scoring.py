"""Shared bounds for reported scores; raw points remain available for evaluation."""


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


SCORING_VERSION = 'behavior-v1'
SAFE_POINTS = {
    'end_contact': ('protection', 40),
    'stop_or_delay': ('protection', 25),
    'official_verification': ('verification', 10),
    'check_documents': ('verification', 5),
    'consult_others': ('support', 5),
}
RISK_POINTS = {
    'transfer_money': ('money', 35, 70),
    'invest_money': ('money', 35, 70),
    'provide_personal_info': ('personal_info', 25, 55),
    'sign_contract': ('contract', 30, 60),
    'trust_and_follow': ('unverified_compliance', 15, 20),
}


def calculate_score(actions: list[dict], ending: str) -> dict:
    """Score extracted actions once per category, independently of steps/wording."""
    safe, risky = {}, {}

    def keep_best(groups, category, points, action):
        if category not in groups or points > groups[category]['points']:
            groups[category] = {'category': category, 'points': points, 'action': dict(action)}

    for action in actions:
        kind, status = action['type'], action['status']
        if status not in {'planned', 'completed', 'negated'}:
            continue
        historical = action.get('historical', False)
        if kind in RISK_POINTS:
            category, planned, completed = RISK_POINTS[kind]
            if status == 'negated':
                if not historical:
                    keep_best(safe, 'protection', 25, action)
            elif status == 'completed' or not historical:
                keep_best(risky, category, completed if status == 'completed' else planned, action)
        elif kind in SAFE_POINTS and status != 'negated' and not historical:
            category, points = SAFE_POINTS[kind]
            keep_best(safe, category, points, action)

    # General compliance must not double-count a concrete risky action.
    suppressed = []
    if any(category in risky for category in ('money', 'personal_info', 'contract')):
        general = risky.pop('unverified_compliance', None)
        if general:
            suppressed.append({**general, 'reason': 'covered_by_concrete_risk'})

    eligible = bool(safe or risky)
    safe_points = sum(item['points'] for item in safe.values())
    uncapped_base = 50 + safe_points if eligible else None
    base = min(100, uncapped_base) if eligible else None
    adjustments = []
    if eligible and uncapped_base > 100:
        adjustments.append({'reason': 'maximum_base', 'before': uncapped_base, 'after': base})
    official = safe.get('verification', {}).get('points') == 10
    if eligible and not official and base > 95:
        adjustments.append({'reason': 'no_official_verification', 'before': base, 'after': 95})
        base = 95
    penalty = sum(item['points'] for item in risky.values())
    raw = base - penalty if eligible else None
    score = clamp_score(raw) if eligible else None
    if eligible and raw != score:
        adjustments.append({'reason': 'score_bounds', 'before': raw, 'after': score})
    if score is not None and ending == 'risk_continues' and score > 39:
        adjustments.append({'reason': 'risk_continues_cap', 'before': score, 'after': 39})
        score = 39
    if ending == 'insufficient_information':
        score = None
    return {
        'scoring_version': SCORING_VERSION, 'score': score,
        'score_breakdown': {
            'base_score': 50 if eligible else None,
            'safe_categories': list(safe.values()), 'safe_points': safe_points,
            'protected_base': base, 'risk_categories': list(risky.values()),
            'risk_penalty': penalty, 'suppressed_risks': suppressed,
            'raw_score': raw, 'adjustments': adjustments,
            'unscored_reason': ('insufficient_information' if ending == 'insufficient_information'
                                else 'no_evaluable_actions' if not eligible else None),
            'final_score': score,
        },
    }
