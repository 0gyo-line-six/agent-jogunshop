import dspy
from agent.product_agent import run_product_agent
from agent.delivery_agent import run_delivery_agent
from agent.general_agent import run_general_agent

class RequestClassifier(dspy.Signature):
    """사용자 요청을 분석하여 적절한 에이전트를 선택하는 분류기입니다.
    
    분류 기준:
    - product: 상품 정보, 가격, 색상, 사이즈, 재고, 상품 검색 등
    - delivery: 배송 상태, 배송 정책, 배송 시간, 주문 조회 등  
    - general: 일반적인 문의, 인사, 기타 등
    """
    
    user_request: str = dspy.InputField(desc="사용자의 원본 요청")
    category: str = dspy.OutputField(desc="product, delivery, general 중 하나")
    reasoning: str = dspy.OutputField(desc="분류 근거에 대한 간단한 설명")

def classify_user_request(user_request: str) -> tuple[str, str]:
    """사용자 요청을 분류하여 카테고리와 근거를 반환합니다."""
    classifier = dspy.ChainOfThought(RequestClassifier)
    result = classifier(user_request=user_request)
    return result.category.lower().strip(), result.reasoning

def route_request(user_request: str) -> dict:
    """사용자 요청을 적절한 에이전트로 라우팅합니다."""
    try:
        print(f"📝 사용자 요청: {user_request}")
        print("🔍 요청 분류 중...")
        
        category, reasoning = classify_user_request(user_request)
        
        print(f"📋 분류 결과: {category}")
        print(f"💭 분류 근거: {reasoning}")
        
        result = {
            'category': category,
            'reasoning': reasoning,
            'user_request': user_request,
            'response': None,
            'agent_used': None,
            'success': False
        }
        
        if category == 'product':
            print("🛍️ 상품 에이전트로 전달...")
            result['agent_used'] = 'product_agent'
            agent_result = run_product_agent(user_request)
            if agent_result:
                result['response'] = getattr(agent_result, 'query_result', '상품 정보 조회를 완료했습니다.')
                result['success'] = True
            else:
                result['response'] = "상품 정보 조회 중 오류가 발생했습니다."
        elif category == 'delivery':
            print("🚚 배송 에이전트로 전달...")
            result['agent_used'] = 'delivery_agent'
            agent_result = run_delivery_agent(user_request)
            if agent_result:
                result['response'] = getattr(agent_result, 'delivery_result', '배송 정보 조회를 완료했습니다.')
                result['success'] = True
            else:
                result['response'] = "배송 정보 조회 중 오류가 발생했습니다."
        elif category == 'general':
            print("💬 일반 에이전트로 전달...")
            result['agent_used'] = 'general_agent'
            agent_result = run_general_agent(user_request)
            if agent_result:
                result['response'] = getattr(agent_result, 'general_result', '일반 문의 처리를 완료했습니다.')
                result['success'] = True
            else:
                result['response'] = "일반 문의 처리 중 오류가 발생했습니다."
        else:
            print("❓ 알 수 없는 카테고리...")
            result['agent_used'] = 'general_agent'
            agent_result = run_general_agent(user_request)
            if agent_result:
                result['response'] = getattr(agent_result, 'general_result', '문의 처리를 완료했습니다.')
                result['success'] = True
            else:
                result['response'] = "문의 처리 중 오류가 발생했습니다."
            
        return result
        
    except Exception as e:
        print(f"❌ 라우터 오류: {e}")
        return {
            'category': 'error',
            'reasoning': f'처리 중 오류 발생: {e}',
            'user_request': user_request,
            'response': "죄송합니다. 요청 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
            'agent_used': 'error_handler',
            'success': False
        }

if __name__ == "__main__":
    from core.config import config

    # DSPy 설정
    def setup_dspy():
        """DSPy 언어 모델 설정"""
        try:
            if config.is_azure_openai_ready:
                lm = dspy.LM(
                    model=f"azure/{config.AZURE_OPENAI_DEPLOYMENT_ID}",
                    api_base=config.AZURE_OPENAI_ENDPOINT,
                    api_version=config.AZURE_OPENAI_API_VERSION,
                    api_key=config.AZURE_OPENAI_API_KEY,
                    cache=True
                )
                dspy.configure(lm=lm)
                print("✅ DSPy Azure OpenAI 설정 완료")
                return True
            else:
                print("❌ Azure OpenAI 설정이 없습니다")
                return False
        except Exception as e:
            print(f"❌ DSPy 설정 오류: {e}")
            return False

    print("🚀 조건샵 에이전트 라우터 테스트")
    print("=" * 50)
    
    # DSPy 설정
    if not setup_dspy():
        print("❌ DSPy 설정 실패로 테스트를 중단합니다.")
        exit(1)
    
    # 테스트 케이스들
    test_cases = [        
        "washable signature cash viscose 니트 색상 어떤거 있나요?"
        "washable signature cash viscose 니트 가격 얼마인가요?"
        "washable signature cash viscose 니트 L사이즈 저한테 맞을까요?",
        "washable signature cash viscose 니트랑 치노팬츠 L사이즈 블랙 저한테 괜찮을까요?"
    ]
    
    for i, test_request in enumerate(test_cases, 1):
        print(f"\n🧪 테스트 {i}: {test_request}")
        print("-" * 40)
        
        result = route_request(test_request)
        
        print(f"✅ 최종 결과:")
        print(f"   카테고리: {result['category']}")
        print(f"   사용된 에이전트: {result['agent_used']}")
        print(f"   성공 여부: {result['success']}")
        print(f"   응답: {result['response']}")
        
        print("=" * 50)