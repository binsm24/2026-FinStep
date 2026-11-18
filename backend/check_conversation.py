"""Manual live dialogue regression using synthetic text and a temporary local DB."""
import json
import os
from pathlib import Path
import tempfile
import time


FLOWS = [
    ('jeonse-fraud', 95, [
        ('주변 시세를 확인하고 오늘 계약은 보류한다.', 'advanced', 2),
        ('얼마나 더 여유를 주실 수 있나요?', 'question_answered', 2),
        ('그럼 내일까지 기다려 주실 수 있나요?', 'question_answered', 2),
        ('오늘 안으로는 힘들 것 같습니다.', 'advanced', 3),
        ('등기부등본을 볼 수 있나요?', 'question_answered', 3),
        ('이 거래를 철회하고 연락을 끝낸다.', 'finished', 3),
    ]),
    ('voice-phishing', 100, [
        ('개인정보를 제공하지 않고 공식 기관에 직접 확인한다.', 'advanced', 2),
        ('어느 기관에서 연락하셨나요?', 'question_answered', 2),
        ('전화를 끊는다.', 'finished', 2),
    ]),
    ('investment-fraud', 100, [
        ('원금 보장의 근거가 무엇인가요?', 'question_answered', 1),
        ('금융감독원 공식 조회 경로에서 업체 등록 여부를 확인하고 확인 전에는 투자를 보류한다.', 'advanced', 2),
        ('내일까지 기다려 주실 수 있나요?', 'question_answered', 2),
        ('이 제안을 거절하고 연락을 끝낸다.', 'finished', 2),
    ]),
]


def main():
    root = Path(__file__).resolve().parents[1]
    (root / 'tmp').mkdir(exist_ok=True)
    rows, calls = [], []
    # Set a fresh SQLite URL before importing settings or touching the DB.
    with tempfile.TemporaryDirectory(prefix='dialogue-check-', dir=root / 'tmp') as folder:
        os.environ['DATABASE_URL'] = f"sqlite:///{(Path(folder) / 'test.db').as_posix()}"
        from database import get_engine, init_db
        from services import multi_stage_service as svc, llm_service as llm
        from services.session_store import get_session
        if llm.provider != 'gateway' or not llm.is_configured():
            raise RuntimeError('School Gateway is not configured')
        real_analysis = svc.analyze_answer_with_llm
        real_generation = svc.generate_next_response

        def analysis(**kwargs):
            result = real_analysis(**kwargs)
            calls.append({'kind': 'analysis', 'available': result['llm_available'],
                          'question_topic': result.get('question_topic')})
            return result

        def generation(**kwargs):
            result = real_generation(**kwargs)
            calls.append({'kind': 'generation', 'available': result['llm_available']})
            return result

        svc.analyze_answer_with_llm = analysis
        svc.generate_next_response = generation
        init_db()
        try:
            for scenario, score, turns in FLOWS:
                sid = svc.create_session(scenario)['session_id']
                for index, (text, status, stage) in enumerate(turns):
                    before = get_session(sid)
                    start = time.perf_counter()
                    response = svc.submit_stage_answer(sid, text, f'{scenario}-{index}')
                    after = get_session(sid)
                    errors = []
                    if (response['status'], response['stage']) != (status, stage):
                        errors.append('status_or_stage')
                    if status == 'question_answered':
                        for field in ['stage_results', 'action_history', 'clarification_count', 'total_score']:
                            if after[field] != before[field]:
                                errors.append('question_changed_' + field)
                    if response['is_finished'] and svc.get_session_result(sid)['score'] != score:
                        errors.append('final_score')
                    row = {'scenario': scenario, 'text': text, 'status': response['status'],
                           'stage': response['stage'], 'messages': response['messages'],
                           'seconds': round(time.perf_counter() - start, 3), 'errors': errors}
                    rows.append(row)
                    print(f"{len(rows)}/13 {scenario} {status}: {'PASS' if not errors else 'FAIL'} {row['seconds']}s", flush=True)
                    if response['is_finished']:
                        break
        finally:
            get_engine().dispose()
            get_engine.cache_clear()
    success = len(rows) == 13 and not any(row['errors'] for row in rows) and all(c['available'] for c in calls)
    report = {'prompt_version': llm.ANALYSIS_PROMPT_VERSION, 'model': llm.gateway_model,
              'passed': success, 'turns': rows, 'calls': calls}
    output = root / 'output' / 'conversation-validation.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"RESULT: {'PASS' if success else 'FAIL'}; {len(rows)} turns, {len(calls)} live calls", flush=True)
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
