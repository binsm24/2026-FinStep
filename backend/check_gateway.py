"""Manual Gateway check. Never runs during unittest discovery."""
import argparse
import sys

import httpx
from services import llm_service as llm


def main():
    parser = argparse.ArgumentParser(description='학교 Gateway 연결 확인')
    parser.add_argument('--list-models', action='store_true', help='모델 목록만 조회 (생성 요청 없음)')
    args = parser.parse_args()
    if llm.provider != 'gateway' or not llm.gateway_api_key:
        print('backend/.env에 LLM_PROVIDER=gateway와 BAZE_API_KEY를 설정하세요.')
        return 1
    if args.list_models:
        try:
            endpoint = llm.gateway_endpoint().removesuffix('chat/completions/') + 'models/'
            response = httpx.get(endpoint, headers={'Authorization': f'Bearer {llm.gateway_api_key}'},
                                 timeout=20, follow_redirects=False)
            response.raise_for_status()
            for item in response.json()['data']:
                print(item['id'])
            return 0
        except Exception:
            print('모델 조회 실패: API 키, 주소, 네트워크 및 학교 이용 권한을 확인하세요.')
            return 1
    result = llm.analyze_answer_with_llm('보이스피싱', '기관 사칭', '정보 제공을 요구받음', '전화를 끊는다')
    if not result['llm_available']:
        print('Gateway 분석 실패: API 키, 모델 접근 권한, JSON Schema 지원을 확인하세요.')
        return 1
    from services.branch_analysis import decide
    if decide(result) != ('safe', True):
        print('연결은 성공했으나 통화 종료 판정이 예상과 다릅니다. 모델 분석을 점검하세요.')
        return 1
    print('Gateway 연결 및 JSON 검증 성공: 전화를 끊는다 → 안전 분기 / 종료')
    return 0


if __name__ == '__main__':
    sys.exit(main())
