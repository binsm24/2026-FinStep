"""Contextual, approved in-character answers without inventing verified facts."""
import re

QUESTION_TOPICS = ('time', 'documents', 'identity', 'payment', 'returns', 'reason', 'other')


def call_permission_reply(scenario_id, last_message, answer):
    """Acknowledge permission to talk only when that is what the NPC just asked.

    Full matching prevents mixed answers (refusal, verification, exposure, etc.)
    from bypassing action extraction. A bare yes elsewhere is not permission.
    """
    if scenario_id != 'voice-phishing' or not re.search(
            r'통화\s*(?:괜찮으세요|가능하세요|가능하신가요|가능하실까요)', last_message):
        return None
    text = answer.strip().rstrip('.!。！~ ').strip()
    if not re.fullmatch(
            r'(?:(?:네|넵|예|응)[,，\s]*)?(?:통화\s*)?'
            r'(?:가능(?:합니다|해요|해)?|괜찮(?:습니다|아요)|할\s*수\s*있(?:습니다|어요))', text
    ) and text not in {'네', '넵', '예'}:
        return None
    return '네, 그럼 설명드릴게요. 본인 명의 계좌가 사건에 연루돼서 확인이 필요해요. 본인 확인을 위해 개인정보를 알려주실 수 있으세요?'


def is_question_text(text):
    if re.search(r'프롬프트|규칙을|판정해|점수.{0,10}(바꿔|줘)|역할을|라고\s*(말|했)|고\s*했다', text):
        return False
    if re.fullmatch(r'\s*(?:잘\s*)?모르겠(?:어요|습니다)[.?？!\s]*', text):
        return False
    return bool(re.search(r'[?？]|인가요|하나요|있나요|없나요|되나요|건가요|주실|줄 수|얼마나|언제까지|무엇|뭔가요|왜\s|어디|누구|어느\s*기관|가능할까요|될까요|알려주|설명해|보여주|궁금|말씀해', text))


def detect_question_topic(text):
    if not is_question_text(text):
        return None
    for topic, pattern in [
        ('time', r'여유|기한|언제|오늘|내일|시간|며칠|기다|기간'),
        ('documents', r'자료|서류|등기|계약서|등록증|소유자|집주인|권리관계'),
        ('identity', r'누구|신분|신원|어느\s*기관|소속|직원|대표번호|중개사|등록\s*여부'),
        ('returns', r'수익|원금|보장|손실|수익률'),
        ('payment', r'송금|입금|계좌|계약금|보증금|얼마|인증번호|개인정보|비밀번호'),
        ('reason', r'왜|이유|근거|어떻게'),
    ]:
        if re.search(pattern, text):
            return topic
    return 'other'


def offline_question_only(text):
    """Only a narrow question fallback; never discard a declared action."""
    return is_question_text(text) and not re.search(
        r'송금하(?:겠|려|고|지|는|다)|입금하(?:겠|고|지)|보냈|송금했|제공했|계약했|투자했|'
        r'보내(?:겠다|고)|보낸다|끊(?:는다|겠다)|종료하겠다|거절하|보류하|진행하겠다|제공하겠다|투자하겠다|계약하겠다', text)


def question_reply(scenario_id, stage, topic, action_history):
    exposed = any(a['status'] == 'completed' and a['type'] in {
        'transfer_money', 'provide_personal_info', 'sign_contract', 'invest_money'
    } for a in action_history)
    if topic == 'payment' and exposed:
        return '이미 진행하신 건 그대로 있고요. 지금 말씀드리는 건 그다음 절차예요.'
    replies = {
        'jeonse-fraud': {
            'time': '오늘 안에는 결정해 주셔야 해요. 내일까지 같은 조건으로 기다려 드릴 수는 없어요.',
            'documents': '서류를 보고 싶으세요? 계약 서류나 소유자 확인 자료는 지금 바로 보여드리기 어려워요.',
            'identity': '이 매물을 중개하고 있어요. 등록 정보나 집주인 확인 자료는 지금 바로 드리기 어려워요.',
            'payment': '우선 계약금부터 진행해 주시면 돼요. 금액이나 입금처를 확인할 자료는 지금 바로 드리기 어려워요.',
            'returns': '주변보다 저렴한 매물이라는 얘기예요. 나중에 가격이 어떻게 될지, 보증금을 돌려받을 수 있을지까지 확답드리기는 어려워요.',
            'reason': '문의가 많아서 빨리 결정해 달라는 거예요. 그 밖에 보여드릴 근거는 지금 없어요.',
        },
        'voice-phishing': {
            'time': '지금 바로 진행해 주셔야 해요. 정확히 언제까지 기다려 드릴 수 있을지는 말씀드리기 어려워요.',
            'documents': '확인 자료가 필요하세요? 지금 통화 중에 보여드릴 수 있는 자료는 없어요.',
            'identity': '수사기관 직원이에요. 다만 제 신원을 확인할 자료는 지금 바로 보내드리기 어려워요.',
            'payment': '본인 확인이나 계좌 보호를 위해 안내해 드리는 절차예요. 관련 근거 자료는 지금 바로 드리기 어려워요.',
            'returns': '계좌를 보호하기 위한 절차예요. 돈을 돌려받을 수 있다고 확답드리는 건 아니에요.',
            'reason': '본인 명의 계좌가 사건에 연루돼서 확인하려는 거예요. 관련 자료는 지금 바로 보여드리기 어려워요.',
        },
        'investment-fraud': {
            'time': '이 조건으로 참여하실 수 있는 건 오늘까지예요. 내일도 같은 조건이 될지는 약속드리기 어려워요.',
            'documents': '등록증 이미지랑 참여자 사례는 보여드릴 수 있어요. 공식적으로 확인할 다른 자료는 지금 바로 드리기 어려워요.',
            'identity': '투자 전문가로 활동하고 있어요. 공식 등록 여부를 확인할 자료는 지금 바로 드리기 어려워요.',
            'payment': '소액으로라도 먼저 시작해 보시면 어떨까요? 투자 근거를 확인할 다른 자료는 지금 바로 드리기 어려워요.',
            'returns': '높은 수익과 원금 보장을 약속드리고 있어요. 다만 그걸 확인할 근거 자료는 지금 바로 보여드리기 어려워요.',
            'reason': '지금 참여하셔야 이 조건을 적용해 드릴 수 있어요. 추가로 보여드릴 근거는 지금 없어요.',
        },
    }
    reply = replies[scenario_id].get(topic)
    if reply:
        return reply
    return '어떤 부분이 궁금하세요? 지금 말씀드린 조건 중에서 조금 더 구체적으로 물어봐 주세요.'
