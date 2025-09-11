from agent.router import route_request
from core.config import Config, initialize

if __name__ == "__main__":
    initialize()
    
    if not Config.validate_azure_config():
        missing_vars = Config.get_missing_vars()
        print(f"❌ 환경변수 누락: {', '.join(missing_vars)}")
        exit(1)
    
    user_input = "2type 카라 반팔티 M사이즈 집업 블랙 옵션 가격 얼마인가요?"
    print(f"🔍 단일 테스트: '{user_input}'\n")
    result = route_request(user_input)
    
    print("="*60)
    print("🤖 최종 응답:")
    if result.get('response'):
        print(result['response'])
    else:
        print("응답을 받지 못했습니다.")
    print("="*60)
    print(f"✅ 처리 결과: {'성공' if result['success'] else '실패'}")
    print(f"🔧 사용된 에이전트: {result.get('agent_used', '알 수 없음')}")
    print(f"📂 분류: {result.get('category', '알 수 없음')}")
    if result.get('reasoning'):
        print(f"💭 분류 근거: {result['reasoning']}")