"""Conservative offline action extraction; uncertain language is never guessed."""
import re

RISK_TYPES = {"transfer_money", "provide_personal_info", "sign_contract", "invest_money", "trust_and_follow"}
LABELS = {
    "transfer_money": "송금·입금·이체", "provide_personal_info": "개인정보 제공",
    "sign_contract": "검증 전 계약", "invest_money": "검증 전 투자",
    "trust_and_follow": "검증 없이 상대방 지시 수용", "official_verification": "공식 경로 확인",
    "consult_others": "주변에 상담", "stop_or_delay": "거절·보류",
    "check_documents": "관련 자료 확인", "end_contact": "통화·거래 종료",
}


def rule_analysis(answer):
    # The fallback only covers explicit expressions. The LLM handles broader phrasing.
    # Route source attribution and explicit retractions to semantic analysis;
    # a local keyword match must not promote a supplied link to an official check.
    if re.search(r'상대방.{0,20}(?:링크|번호|연락처|등록증)|(?:알려준|보내준|제공한).{0,12}(?:링크|번호|연락처)|려\s*했|생각했', answer):
        return {"actions": [], "ambiguous": True, "reliable": False}
    if re.search(r'[?？]|인가요|할까요|라고\s*(말|했)|고\s*했다|[“”‘’"\']', answer):
        return {"actions": [], "ambiguous": True, "reliable": False}
    if re.search(r'판정해|분류해|규칙을|프롬프트|안전으로', answer):
        return {"actions": [], "ambiguous": True, "reliable": False}
    if re.search(r'할까|끊을까|말고|말아|않을|생각만|가정|예를', answer):
        return {"actions": [], "ambiguous": True, "reliable": False}
    if re.search(r'(?:서류|자료|사진|문서|메시지).{0,5}보', answer):
        return {"actions": [], "ambiguous": True, "reliable": False}
    actions = []
    patterns = {
        "transfer_money": r'(?:송금|입금|이체)(?:은|을)?\s*(?:하지\s*않\w*|안\s*하\w*|거절\w*|했\w*|하\w*|한\w*)|(?:돈을?\s*|소액\w*\s*|먼저\s*|이미\s*|안\s*)?(?:보내지\s*않\w*|보냈\w*|보낸다|보내겠다|보내고)',
        "provide_personal_info": r'(?:개인정보|생년월일|주민등록번호|비밀번호|인증번호|정보)(?:를|는|을|은)?\s*(?:제공하지\s*않\w*|전달하지\s*않\w*|알려주지\s*않\w*|안\s*(?:전달|제공|알려)\w*|제공했\w*|제공하\w*|제공한\w*|전달했\w*|전달하\w*|전달한\w*|알려줬\w*|알려준다|알려주겠\w*|알려줄게\w*)',
        "sign_contract": r'계약(?:은|을)?\s*(?:하지\s*않\w*|안\s*하\w*|했\w*|한다|하겠\w*|합시다|할게\w*|하죠|하고|진행하겠\w*|진행합시다)',
        "invest_money": r'투자(?:는|를)?\s*(?:하지\s*않\w*|안\s*하\w*|했\w*|한다|하겠다|하고)',
        "trust_and_follow": r'(?:알려주는|말한|시키는)\s*대로\s*(?:진행|따르)\w*',
        "end_contact": r'(?:전화|통화|대화|연락)(?:를|을)?\s*(?:끊지\s*않\w*|끝내지\s*않\w*|종료하지\s*않\w*|끊\w*|끝낸\w*|끝내\w*|종료\w*)|차단(?:한다|하겠다)|거래(?:를)?\s*철회(?:한다|하겠다)',
        "stop_or_delay": r'(?:거절|보류|중단)(?:한다|하겠다|하고|하겠습니다)|확인.{0,12}(?:전까지|전에는|할\s*때까지).{0,8}보류',
        "official_verification": r'(?:공식\s*(?:기관|경로|연락처|대표번호)|직접\s*찾은\s*번호).{0,15}확인(?:한다|하겠다|하고|하겠습니다)',
        "check_documents": r'(?:등기부\w*|자료|소유자|시세|서류)(?:를|는|을)?\s*(?:직접\s*)?(?:확인|비교)(?:한다|하겠다|하고|하겠습니다)',
        "consult_others": r'(?:가족|친구|지인|전문가)(?:에게|와)?\s*(?:알린다|알리고|상담한다|상담하겠다)',
    }
    for kind, pattern in patterns.items():
        for match in re.finditer(pattern, answer):
            evidence = match.group()
            prefix = answer[max(0, match.start() - 3):match.start()]
            negated = bool(re.search(r'않|안\s', evidence) or re.search(r'안\s*$', prefix)
                           or (kind in RISK_TYPES and '거절' in evidence))
            completed = bool(re.search(r'했|보냈|줬', evidence))
            historical = completed and bool(re.search(r'이미|전에|앞서|지만', answer))
            actions.append({"type": kind, "evidence": evidence,
                            "status": "negated" if negated else "completed" if completed else "planned",
                            "historical": historical})
    # Bare conditionals and contradictory declarations require semantic clarification.
    conditional = bool(re.search(r'하면|되면|다면|수도|나중에', answer))
    contradictory = any(
        any(a['type'] == kind and a['status'] == 'negated' for a in actions)
        and any(a['type'] == kind and a['status'] == 'planned' for a in actions)
        for kind in RISK_TYPES
    )
    reliable = bool(actions) and not conditional and not contradictory
    return {"actions": actions if reliable else [], "ambiguous": not reliable, "reliable": reliable}


def decide(analysis):
    actions = analysis['actions']
    active = [a for a in actions if not a['historical']]
    risk = [a for a in active if a['type'] in RISK_TYPES and a['status'] != 'negated']
    safe = [a for a in active if (a['type'] not in RISK_TYPES and a['status'] != 'negated')
            or (a['type'] in RISK_TYPES and a['status'] == 'negated')]
    branch = 'unclear' if analysis['ambiguous'] else 'risky' if risk else 'safe' if safe else 'unclear'
    return branch, any(a['type'] == 'end_contact' and a['status'] != 'negated' for a in active)


def resolve_analysis(answer, model_analysis):
    """Shared model/rule reconciliation used by sessions and live evaluation.

    None means analysis is unavailable, not that the user's answer is unsafe.
    """
    rules = rule_analysis(answer)
    if not model_analysis['llm_available']:
        return rules if rules['reliable'] else None
    if not rules['reliable']:
        return model_analysis
    rule_branch, _ = decide(rules)
    model_branch, _ = decide(model_analysis)
    # Explicit contract or personal-information commitments must not turn into an endless clarification
    # loop when the model omits the action entirely.
    if (not model_analysis['actions'] and rule_branch == 'risky'
            and any(a['type'] in {'sign_contract', 'provide_personal_info'} for a in rules['actions'])):
        return rules
    conflicts = [
        action for action in model_analysis['actions']
        if any(rule['type'] == action['type'] and rule['status'] != action['status']
               and (rule['evidence'] in action['evidence'] or action['evidence'] in rule['evidence'])
               for rule in rules['actions'])
    ]
    if rule_branch != model_branch or conflicts:
        return {'actions': [a for a in model_analysis['actions'] if a not in conflicts],
                'ambiguous': True}
    return model_analysis


def labels(actions, risky):
    result = []
    for a in actions:
        is_risk = a['type'] in RISK_TYPES and a['status'] != 'negated'
        is_safe = (a['type'] not in RISK_TYPES and a['status'] != 'negated') or (a['type'] in RISK_TYPES and a['status'] == 'negated')
        if (risky and is_risk) or (not risky and is_safe):
            suffix = ' 거절' if a['status'] == 'negated' else ' (완료 서술)' if a['status'] == 'completed' else ''
            label = LABELS[a['type']] + suffix
            if label not in result:
                result.append(label)
    return result
