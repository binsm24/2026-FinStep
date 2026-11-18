import re
from copy import deepcopy
from uuid import uuid4

from data.scenarios import MULTI_STAGE_SCENARIOS
from data.branches import BRANCHES, ENDINGS, STAGE_CONTEXTS, next_dialogue
from services.branch_analysis import RISK_TYPES, decide, labels, resolve_analysis
from services.llm_service import analyze_answer_with_llm, generate_next_response
from services.simulator_service import is_negated
from services.scoring import SCORING_VERSION, calculate_score, clamp_score
from services.question_dialogue import call_permission_reply, detect_question_topic, offline_question_only, question_reply

from services.session_store import create_session_snapshot, get_session, load_session, save_session
CLARIFICATION = '이 상황에서 실제로 어떻게 행동할지 적어주세요. 돈이나 정보를 제공할지, 확인하거나 대화를 중단할지 구체적으로 알려주세요.'


def find_scenario(scenario_id):
    return next((s for s in MULTI_STAGE_SCENARIOS if s['id'] == scenario_id), None)


def create_session(scenario_id, owner=None):
    scenario = find_scenario(scenario_id)
    if scenario is None:
        raise ValueError('존재하지 않는 시나리오입니다.')
    sid = str(uuid4())
    data = BRANCHES[scenario_id]
    session = {
        'owner': owner,
        'session_id': sid, 'scenario_id': scenario_id, 'current_stage': 1,
        'scoring_version': SCORING_VERSION,
        'total_score': None, 'stage_results': [], 'action_history': [],
        'conversation_history': [], 'clarification_count': 0,
        'branch': None, 'ending_type': None, 'is_finished': False,
        'description': STAGE_CONTEXTS[scenario_id][0], 'question': data['questions'][0],
        'messages': [{'speaker': data['speaker'], 'message': data['opening']},
                     {'speaker': '상황', 'message': STAGE_CONTEXTS[scenario_id][0], 'kind': 'situation'}],
        'request_cache': {},
    }
    _record_messages(session)
    create_session_snapshot(session)
    return _response(session)


def _record_messages(session):
    session['conversation_history'].extend(
        {**message, 'stage': session['current_stage']} for message in session['messages']
    )


def _response(session, status='advanced'):
    scenario = find_scenario(session['scenario_id'])
    stage = scenario['stages'][session['current_stage'] - 1]
    return {
        'session_id': session['session_id'], 'scenario_id': scenario['id'],
        'scenario_title': scenario['title'], 'stage': stage['stage'],
        'stage_title': stage['title'], 'description': session['description'],
        'question': session['question'], 'messages': deepcopy(session['messages']),
        'answer_placeholder': BRANCHES[scenario['id']]['placeholder'],
        'total_stages': scenario['total_stages'],
        'total_score': (session['total_score'] if session.get('scoring_version') == SCORING_VERSION
                        else clamp_score(session['total_score']) if session['is_finished']
                        else session['total_score']),
        'scoring_version': session.get('scoring_version', 'legacy-v0'),
        'branch': session['branch'], 'status': status,
        'completed_stage_count': len(session['stage_results']),
        'ending_type': session['ending_type'], 'is_finished': session['is_finished'],
        'safe_actions': labels(session['action_history'], False),
        'risky_actions': labels(session['action_history'], True),
    }


def submit_stage_answer(session_id, answer, request_id=None, expected_stage=None, completed_by=None):
    session, version = load_session(session_id)
    if session is None:
        raise ValueError('존재하지 않는 시뮬레이션 세션입니다.')
    answer = answer.strip()
    if request_id and request_id in session['request_cache']:
        cached_answer, response = session['request_cache'][request_id]
        if cached_answer != answer:
            raise ValueError('같은 요청 ID에 다른 답변을 사용할 수 없습니다.')
        return deepcopy(response)
    if session['is_finished']:
        raise ValueError('이미 종료된 시뮬레이션입니다.')
    if expected_stage is not None and expected_stage != session['current_stage']:
        raise ValueError('현재 단계와 요청 단계가 다릅니다.')
    if not 1 <= len(answer) <= 500:
        raise ValueError('답변은 1~500자로 작성해 주세요.')
    response = _submit(session, answer, completed_by)
    if response['status'] == 'analysis_unavailable':
        return response
    if request_id:
        session['request_cache'][request_id] = (answer, deepcopy(response))
    if not save_session(session, version):
        latest = get_session(session_id)
        cached = latest['request_cache'].get(request_id) if latest and request_id else None
        if cached and cached[0] == answer:
            return deepcopy(cached[1])
        raise ValueError('다른 요청이 먼저 처리되었습니다. 현재 결과를 확인한 뒤 다시 시도해 주세요.')
    return response


def _submit(session, answer, completed_by=None):
    scenario = find_scenario(session['scenario_id'])
    stage = scenario['stages'][session['current_stage'] - 1]
    last_message = next((m['message'] for m in reversed(session['conversation_history'])
                         if m['speaker'] not in {'나', '진행 안내', '상황'}), '')
    reply = call_permission_reply(scenario['id'], last_message, answer)
    if reply:
        session['conversation_history'].append({'speaker': '나', 'message': answer,
                                                'stage': session['current_stage']})
        session['messages'] = [{'speaker': BRANCHES[scenario['id']]['speaker'], 'message': reply}]
        _record_messages(session)
        return _response(session, 'dialogue_continued')
    model_analysis = analyze_answer_with_llm(
        scenario_title=scenario['title'], stage_title=stage['title'],
        situation=session['description'], answer=answer,
        conversation_history=session['conversation_history'],
    )
    detected_topic = detect_question_topic(answer)
    topic = (model_analysis.get('question_topic') or detected_topic) if detected_topic else None
    analysis = resolve_analysis(answer, model_analysis)
    if model_analysis['llm_available'] and analysis is not model_analysis:
        topic = None  # A model/rule conflict still requires clarification.
    if analysis is None and topic and offline_question_only(answer):
        analysis = {'actions': [], 'ambiguous': True}
    if analysis is None:
        response = _response(session, 'analysis_unavailable')
        response['messages'] = [{'speaker': '진행 안내', 'message': '지금은 답변을 분석할 수 없습니다. 잠시 후 다시 제출해 주세요.'}]
        return response
    branch, end_contact = decide(analysis)
    session['conversation_history'].append({'speaker': '나', 'message': answer, 'stage': session['current_stage']})
    # Preserve grounded completed exposure even when current intent needs clarification.
    for action in analysis['actions']:
        if branch != 'unclear' or (action['type'] in RISK_TYPES and action['status'] == 'completed'):
            record = {**action, 'stage': session['current_stage']}
            if record not in session['action_history']:
                session['action_history'].append(record)
    if branch == 'unclear':
        # Questions are dialogue turns, not unanswered assessment attempts.
        # Keep any already grounded past exposure but never invent a decision.
        if topic and not any(not a.get('historical', False) and a['status'] != 'negated'
                             for a in analysis['actions']):
            session['messages'] = [
                {'speaker': BRANCHES[scenario['id']]['speaker'],
                 'message': question_reply(scenario['id'], session['current_stage'], topic,
                                           session['action_history'])},
                {'speaker': '상황', 'kind': 'situation',
                 'message': session['description'] + ' 상대방의 답변을 들었습니다. 같은 상황에서 질문을 더 하거나 행동을 결정할 수 있습니다.'},
            ]
            _record_messages(session)
            return _response(session, 'question_answered')
        if session['clarification_count'] >= 2:
            return _finish(session, 'insufficient_information', completed_by)
        session['clarification_count'] += 1
        session['messages'] = [{'speaker': '진행 안내', 'message': CLARIFICATION}]
        _record_messages(session)
        return _response(session, 'clarification')

    session['branch'] = branch
    session['clarification_count'] = 0
    safe = labels(analysis['actions'], False)
    risky = labels(analysis['actions'], True)
    # Legacy in-progress sessions retain their original rubric. New sessions
    # receive only a final behavior score; stage scores are not additive.
    score = None
    if session.get('scoring_version') != SCORING_VERSION:
        score = 0
        for rule in stage['rules']:
            keyword = next((word for word in rule['keywords'] if word in answer), None)
            if keyword is None:
                continue
            if rule['type'] == 'risky':
                if not risky or is_negated(answer, keyword):
                    continue
            elif not safe:
                continue
            score += rule['score']
        session['total_score'] += score
    session['stage_results'].append({'stage': session['current_stage'], 'answer': answer,
                                     'branch': branch, 'score': score, 'safe_actions': safe,
                                     'risky_actions': risky, 'actions': analysis['actions']})
    exposure = any(a['type'] in RISK_TYPES and a['status'] == 'completed' for a in session['action_history'])
    committed_risk = branch == 'risky' and any(
        a['type'] in {'sign_contract', 'provide_personal_info'}
        and a['status'] in {'planned', 'completed'} and not a.get('historical', False)
        for a in analysis['actions']
    )
    # A definite refusal of the transaction is a terminal choice, unlike a delay.
    transaction_refused = branch == 'safe' and any(
        a['type'] in {'sign_contract', 'invest_money'} and a['status'] == 'negated'
        and not a.get('historical', False) for a in analysis['actions']
    ) and not re.search(r'확인.{0,12}전|때까지|보류|오늘은|지금은|나중', answer)
    if end_contact or transaction_refused or committed_risk or session['current_stage'] >= scenario['total_stages']:
        ending = ('risk_continues' if branch == 'risky' else 'recovery' if exposure
                  else 'safe_exit' if end_contact or transaction_refused else 'safe_hold')
        return _finish(session, ending, completed_by)

    next_stage = session['current_stage'] + 1
    dialogue = next_dialogue(scenario['id'], next_stage, branch, session['action_history'])
    if topic:
        dialogue['message'] = question_reply(scenario['id'], session['current_stage'], topic,
                                            session['action_history']) + ' ' + dialogue['message']
    actual_message = next((m['message'] for m in reversed(session['conversation_history'])
                           if m['speaker'] not in {'나', '진행 안내', '상황'}), '')
    generated = generate_next_response(
        scenario_title=scenario['title'], current_stage_title=stage['title'],
        current_message=actual_message, user_answer=answer,
        next_stage_title=scenario['stages'][next_stage - 1]['title'],
        next_stage_description=dialogue['description'], next_stage_message=dialogue['message'],
        branch=branch, conversation_history=session['conversation_history'],
        action_history=session['action_history'],
        next_question=dialogue['question'],
    )
    session['current_stage'] = next_stage
    session['description'] = dialogue['description']
    session['question'] = dialogue['question']
    session['messages'] = [{'speaker': dialogue['speaker'], 'message': generated['message']},
                           {'speaker': '상황', 'message': dialogue['description'], 'kind': 'situation'}]
    _record_messages(session)
    return _response(session)


def _finish(session, ending, completed_by=None):
    session['is_finished'] = True
    session['ending_type'] = ending
    session['completion_user_id'] = completed_by
    if session.get('scoring_version') == SCORING_VERSION:
        report = calculate_score(session['action_history'], ending)
        session['total_score'] = report['score']
        session['score_breakdown'] = report['score_breakdown']
    session['messages'] = [{'speaker': 'FinStep 결과 안내', 'message': ENDINGS[ending][2]}]
    _record_messages(session)
    return _response(session, 'finished')


def get_session_result(session_id):
    session = get_session(session_id)
    if session is None:
        raise ValueError('존재하지 않는 시뮬레이션 세션입니다.')
    if not session['is_finished']:
        raise ValueError('아직 종료되지 않은 시뮬레이션입니다.')
    scenario = find_scenario(session['scenario_id'])
    risk_level, risk_label, summary = ENDINGS[session['ending_type']]
    scoring = (calculate_score(session['action_history'], session['ending_type'])
               if session.get('scoring_version') == SCORING_VERSION else {
                   'scoring_version': 'legacy-v0', 'score_breakdown': None,
                   'score': None if risk_level == 'unknown' else clamp_score(session['total_score']),
               })
    return {
        **_response(session, 'finished'),
        **scoring,
        'risk_level': risk_level, 'risk_label': risk_label, 'summary': summary,
        'stage_results': deepcopy(session['stage_results']),
        'action_history': deepcopy(session['action_history']),
        'conversation_history': deepcopy(session['conversation_history']),
        'recommended_actions': scenario['stages'][-1]['recommended_actions'],
    }
