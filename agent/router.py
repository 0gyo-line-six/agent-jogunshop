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