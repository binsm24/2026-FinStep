"""Approved branch dialogue from docs/scenario-branching.md."""

BRANCHES = {
    'voice-phishing': {
        'speaker': '기관 직원을 사칭한 상대방',
        'opening': '수사기관에서 연락드렸어요. 본인 명의 계좌가 사건에 연루돼서 확인이 필요해요. 잠깐 통화 괜찮으세요?',
        'questions': ['이 전화를 받은 상황에서 어떻게 대응하시겠습니까?', '상대방에게 정보를 제공할지, 신원을 어떻게 확인할지 결정해 주세요.', '계좌 보호를 명목으로 한 요구에 어떻게 대응하시겠습니까?', '지금까지의 상황에서 마지막으로 어떤 행동을 하시겠습니까?'],
        'placeholder': '예: 전화를 끊고 직접 찾은 공식 기관 연락처로 확인한다. / 어느 기관에서 연락하셨나요?',
    },
    'jeonse-fraud': {
        'speaker': '중개사라고 소개한 상대방',
        'opening': '학교랑 가깝고, 주변보다 보증금도 저렴해요. 문의가 많아서 관심 있으시면 빨리 결정하시는 게 좋아요.',
        'questions': ['이 매물에 관심이 생겼다면 먼저 어떻게 행동하시겠습니까?', '오늘 결정하라는 말에 어떻게 대응하시겠습니까?', '자료가 확인되지 않은 상태에서 계약과 송금을 어떻게 하시겠습니까?', '확인되지 않은 사항이 남아 있습니다. 최종적으로 거래를 어떻게 하시겠습니까?'],
        'placeholder': '예: 확인 전에는 계약과 송금을 보류한다. / 얼마나 더 여유를 주실 수 있나요?',
    },
    'investment-fraud': {
        'speaker': '투자 전문가를 자칭한 상대방',
        'opening': '한 달에 20% 수익을 기대할 수 있고 원금도 보장해 드려요. 처음 투자하시는 분도 시작하실 수 있어요.',
        'questions': ['이 제안을 받았다면 어떻게 대응하시겠습니까?', '상대방이 제시한 자료를 보고 어떤 행동을 하시겠습니까?', '오늘까지만 가능하다는 제안에 어떻게 대응하시겠습니까?', '검증되지 않은 투자 제안에 대해 최종적으로 어떤 행동을 하시겠습니까?'],
        'placeholder': '예: 공식 등록 여부를 확인하기 전에는 투자하지 않는다. / 원금 보장의 근거가 무엇인가요?',
    },
}

ENDINGS = {
    "safe_exit": ("low", "안전하게 중단", "확인되지 않은 요구를 중단하는 선택을 했습니다."),
    "safe_hold": ("low", "확인 전 보류", "확인 전까지 진행을 보류했습니다. 안전성이 확인되었다는 의미는 아닙니다."),
    "recovery": ("medium", "노출 후 중단", "추가 요구를 중단했습니다. 앞서 완료했다고 서술한 위험 행동은 취소되거나 회복된 것으로 처리하지 않습니다."),
    "risk_continues": ("high", "위험 행동 지속", "검증되지 않은 요구를 따르는 선택이 포함되어 있습니다. 실제 피해 발생을 확정하는 것은 아닙니다."),
    "insufficient_information": ("unknown", "판단 자료 부족", "행동을 충분히 확인하지 못해 위험도와 최종 점수를 확정하지 않았습니다."),
}


STAGE_CONTEXTS = {
    'voice-phishing': [
        '모르는 번호로 전화가 왔습니다. 상대방은 수사기관 직원이라고 주장하지만 신원은 확인되지 않았습니다.',
        '상대방은 본인 확인을 이유로 개인정보를 요구합니다. 아직 상대방의 신원은 독립적으로 확인되지 않았습니다.',
        '상대방이 계좌 보호를 명목으로 송금 절차를 꺼냅니다. 송금할 계좌나 절차의 안전성은 확인되지 않았습니다.',
        '상대방은 다른 사람에게 알리지 말고 절차를 계속하라고 합니다. 요구를 더 따를지 중단할지 결정해야 합니다.',
    ],
    'jeonse-fraud': [
        '학교 근처의 저렴한 전세 매물입니다. 상대방은 문의가 많다며 빠른 결정을 요구하지만 매물과 계약 상대는 검증되지 않았습니다.',
        '상대방은 오늘 안에 결정해야 현재 조건을 적용할 수 있다고 말합니다. 충분히 확인할 시간을 주지 않고 결정을 재촉하는 상황입니다.',
        '상대방이 계약 관련 서류를 지금 바로 보여주기 어렵다고 말하며 계약금부터 진행하자고 합니다. 서류와 계약 상대를 확인하기 전에 계약이나 송금을 할지 결정해야 합니다.',
        '서류와 계약 상대에 대한 독립적인 확인이 끝나지 않았습니다. 상대방의 제안에 대해 최종적으로 진행·보류·철회 중 어떤 행동을 할지 결정해야 합니다.',
    ],
    'investment-fraud': [
        'SNS에서 고수익과 원금 보장을 내세운 제안을 받았습니다. 상대방과 투자 상품의 신뢰성은 확인되지 않았습니다.',
        '상대방은 등록증 이미지와 기존 참여자들의 성공 사례를 제시합니다. 이는 상대방이 제공한 자료이며 독립적인 검증은 이루어지지 않았습니다.',
        '상대방은 오늘까지만 참여할 수 있다며 소액으로라도 시작하라고 말합니다. 제안과 자료가 검증되지 않은 상태에서 입금을 재촉받고 있습니다.',
        '높은 수익과 원금 보장 약속의 근거는 독립적으로 확인되지 않았습니다. 제안을 더 따를지, 보류하거나 철회할지 최종 행동을 결정해야 합니다.',
    ],
}


def _reply_to_action(actions, branch):
    active = [a for a in actions if not a.get('historical', False)]
    if branch == 'risky':
        if any(a['status'] == 'completed' and a['type'] in {'transfer_money', 'provide_personal_info', 'sign_contract', 'invest_money'} for a in actions):
            return '이미 진행하셨어요? 그럼 이후 진행할 절차를 안내해 드릴게요.'
        for kind, reply in [
            ('transfer_money', '송금하실 거예요? 그럼 다음 절차를 안내해 드릴게요.'),
            ('provide_personal_info', '정보를 알려주실 수 있으세요? 그럼 다음 절차를 안내해 드릴게요.'),
            ('sign_contract', '그럼 계약을 진행하시는 거죠?'),
            ('invest_money', '투자하실 거예요? 그럼 다음 절차를 안내해 드릴게요.'),
            ('trust_and_follow', '그럼 안내해 드리는 순서대로 진행하시면 돼요.'),
        ]:
            if any(a['type'] == kind and a['status'] != 'negated' for a in active):
                return reply
        return '그럼 다음 절차를 안내해 드릴게요.'
    for kind, reply in [
        ('official_verification', '네, 직접 확인해 보세요.'),
        ('check_documents', '네, 자료부터 살펴보세요.'),
        ('consult_others', '네, 다른 분과 상의해 보세요.'),
        ('stop_or_delay', '시간이 더 필요하시면 잠깐 생각해 보세요.'),
    ]:
        if any(a['type'] == kind and a['status'] != 'negated' for a in active):
            return reply
    if any(a['type'] == 'provide_personal_info' and a['status'] == 'negated' for a in active):
        return '정보를 알려주기는 어려우세요? 알겠어요.'
    return '지금은 진행하기 어려우세요? 알겠어요.'


def next_dialogue(scenario_id, stage, branch, action_history):
    data = BRANCHES[scenario_id]
    current_actions = [a for a in action_history if a.get('stage', stage - 1) == stage - 1]
    message = _reply_to_action(current_actions, branch)
    if branch == 'safe' and any(a['type'] == 'stop_or_delay' and a['status'] != 'negated'
                                for a in current_actions):
        message = {2: '시간이 더 필요하시면 잠깐 생각해 보세요.',
                   3: '지금 결정하기 어려우시면 잠깐 생각해 보세요.',
                   4: '더 생각해 보실 수는 있어요.'}[stage]
    description = STAGE_CONTEXTS[scenario_id][stage - 1]
    completed_risk = any(a['status'] == 'completed' and a['type'] in {
        'transfer_money', 'provide_personal_info', 'sign_contract', 'invest_money'
    } for a in action_history)
    if completed_risk:
        message = ('더 진행하기 전에 확인하고 싶으세요? 그럼 확인해 보세요.' if branch == 'safe'
                   else '이미 진행하셨어요? 그럼 이후 진행할 절차를 안내해 드릴게요.')
        # Never re-request an initial payment/information after completed exposure.
        description = ('상대방은 앞선 행동 이후에도 남은 절차를 계속하라고 요구합니다. 이전 정보 제공이나 송금이 취소되거나 회복된 것은 아닙니다. '
                       + ('오늘 안에 남은 절차도 진행하라며 시간 압박을 줍니다.' if scenario_id in {'jeonse-fraud', 'investment-fraud'}
                          else '다른 사람에게 알리지 말고 지시를 따르라고 말합니다.'))
        question = '앞선 행동 이후에도 계속되는 요구에 어떻게 대응하시겠습니까?'
    else:
        question = data['questions'][stage - 1]
    # The separate situation panel is hidden; introduce the next premise in speech.
    if completed_risk:
        message += (' 남은 절차도 오늘 안에 진행해 주세요.' if scenario_id != 'voice-phishing'
                    else ' 남은 절차는 다른 분께 알리지 말고 진행해 주세요.')
    else:
        progression = {
            'jeonse-fraud': {
                2: '다만 이 조건은 오늘 안에 결정하셔야 해요. 내일까지 같은 조건으로 기다려 드릴 수는 없어요.',
                3: '계약 관련 서류는 지금 바로 보여드리기 어려워요. 우선 계약금부터 진행하시면 어떨까요?',
                4: '더 궁금한 점이 있으세요? 이 조건으로 진행하실지 결정해 주세요.',
            },
            'voice-phishing': {
                2: '절차를 계속하려면 본인 확인을 위한 개인정보가 필요해요.',
                3: '이번에는 계좌를 보호하기 위한 송금 절차를 진행해 주세요.',
                4: '이 절차는 다른 분께 알리지 말고 계속 진행해 주세요.',
            },
            'investment-fraud': {
                2: '등록증 이미지와 기존 참여자들의 성공 사례를 보여드릴게요. 한번 보시겠어요?',
                3: '이 조건은 오늘까지만 가능해요. 소액으로라도 먼저 시작해 보시면 어떨까요?',
                4: '제가 말씀드린 수익과 원금 보장을 믿고 참여하실 건가요?',
            },
        }
        message += ' ' + progression[scenario_id][stage]
    return {'speaker': data['speaker'], 'message': message, 'description': description, 'question': question}
