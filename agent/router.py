import dspy
from typing import Dict, List
from agent.product_agent import run_product_agent
from agent.delivery_agent import run_delivery_agent
from agent.general_agent import run_general_agent

class UserInfoExtractor(dspy.Signature):
    """채팅 기록에서 사용자의 개인정보를 추출하는 분석기입니다."""
    
    chat_history: str = dspy.InputField(desc="전체 채팅 기록")
    buyer_name: str = dspy.OutputField(desc="구매자명 (없으면 '없음')")
    contact_info: str = dspy.OutputField(desc="전화번호 (없으면 '없음')")
    inquiry_content: str = dspy.OutputField(desc="문의 내용 요약 (없으면 '없음')")

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

def extract_user_info(chat_history: str) -> Dict[str, str]:
    """채팅 기록에서 사용자 정보를 추출합니다."""
    extractor = dspy.ChainOfThought(UserInfoExtractor)
    result = extractor(chat_history=chat_history)
    
    return {
        'buyer_name': result.buyer_name.strip() if result.buyer_name.strip() != '없음' else None,
        'contact_info': result.contact_info.strip() if result.contact_info.strip() != '없음' else None,
        'inquiry_content': result.inquiry_content.strip() if result.inquiry_content.strip() != '없음' else None
    }

def validate_required_info(user_info: Dict[str, str]) -> List[str]:
    """필수 정보가 누락되었는지 확인하고 누락된 항목 리스트를 반환합니다."""
    missing_info = []
    
    if not user_info.get('buyer_name'):
        missing_info.append('구매자명')
    if not user_info.get('contact_info'):
        missing_info.append('연락처')
    if not user_info.get('inquiry_content'):
        missing_info.append('문의내용')
    
    return missing_info

def generate_info_request_message(missing_info: List[str]) -> str:
    """누락된 정보 요청 메시지를 생성합니다."""
    if len(missing_info) == 1:
        return f'안녕하세요 고객님~\n원활한 상담을 위해 {missing_info[0]} 말씀 부탁드립니다.'
    elif len(missing_info) == 2:
        return f'안녕하세요 고객님~\n원활한 상담을 위해 {missing_info[0]}, {missing_info[1]} 말씀 부탁드립니다.'
    else:
        return f'안녕하세요 고객님~\n원활한 상담을 위해 구매자명, 연락처, 문의내용 말씀 부탁드립니다.'

def classify_user_request(user_request: str) -> tuple[str, str]:
    """사용자 요청을 분류하여 카테고리와 근거를 반환합니다."""
    classifier = dspy.ChainOfThought(RequestClassifier)
    result = classifier(user_request=user_request)
    return result.category.lower().strip(), result.reasoning

def route_request(user_request: str, chat_history: str = None) -> dict:
    """사용자 요청을 적절한 에이전트로 라우팅합니다."""
    try:
        print(f"📝 사용자 요청:\n{user_request}")
        
        if chat_history:
            user_info = extract_user_info(chat_history)
            missing_info = validate_required_info(user_info)
            
            if missing_info:
                return {
                    'category': 'info_request',
                    'reasoning': f'필수 정보 누락: {", ".join(missing_info)}',
                    'user_request': user_request,
                    'response': generate_info_request_message(missing_info),
                    'agent_used': 'info_validator',
                    'success': True,
                    'missing_info': missing_info,
                    'extracted_info': user_info,
                    'tags': ['필수정보누락']
                }
            else:
                print("✅ 모든 필수 정보가 확인되었습니다.")
                print(f"   구매자명: {user_info['buyer_name']}")
                print(f"   연락처: {user_info['contact_info']}")
                print(f"   문의내용: {user_info['inquiry_content']}")
        
        category, reasoning = classify_user_request(user_request)
                
        result = {
            'category': category,
            'reasoning': reasoning,
            'user_request': user_request,
            'response': None,
            'agent_used': None,
            'success': False,
            'tags': []
        }
        
        if chat_history:
            result['user_info'] = user_info
        
        if category == 'product':
            print("🛍️ 상품 에이전트로 전달...")
            result['agent_used'] = 'product_agent'
            result['tags'] += ['상품문의']
            agent_result = run_product_agent(user_request, chat_history)
            if agent_result:
                result['response'] = getattr(agent_result, 'query_result', '보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다.')
                result['success'] = True
            else:
                result['response'] = "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다."
                result['tags'] += ['상담원전환']
        elif category == 'delivery':
            print("🚚 배송 에이전트로 전달...")
            result['agent_used'] = 'delivery_agent'
            result['tags'] += ['배송문의']
            agent_result = run_delivery_agent(user_request, chat_history)
            if agent_result:
                result['response'] = getattr(agent_result, 'delivery_result', '보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다.')
                result['success'] = True
            else:
                result['response'] = "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다."
                result['tags'] += ['상담원전환']
        elif category == 'general':
            print("💬 일반 에이전트로 전달...")
            result['agent_used'] = 'general_agent'
            result['tags'] += ['일반문의']
            agent_result = run_general_agent(user_request, chat_history)
            if agent_result:
                result['response'] = getattr(agent_result, 'general_result', '보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다.')
                result['success'] = True
            else:
                result['response'] = "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다."
                result['tags'] += ['상담원전환']
        else:
            print("❓ 알 수 없는 카테고리...")
            result['agent_used'] = 'general_agent'
            result['tags'] += ['상담원전환']
            agent_result = run_general_agent(user_request)
            if agent_result:
                result['response'] = getattr(agent_result, 'general_result', '보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다.')
                result['success'] = True
            else:
                result['response'] = "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다."
                result['tags'] += ['상담원전환']
            
        return result
        
    except Exception as e:
        print(f"❌ 라우터 오류: {e}")
        return {
            'category': 'error',
            'reasoning': f'처리 중 오류 발생: {e}',
            'user_request': user_request,
            'response': "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다.",
            'agent_used': 'error_handler',
            'success': False,
            'tags': ['상담원전환']
        }

if __name__ == "__main__":
    from core.config import config
    
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

    def create_chat_history_from_messages(messages: List[Dict]) -> str:
        """webhook.py와 동일한 방식으로 채팅 기록을 문자열로 변환"""
        if not messages:
            return ""
        
        history_lines = []
        for msg in messages:
            person_type = "고객" if msg.get("personType") == "user" else "상담원"
            text = msg.get("plainText", "")
            if text:
                history_lines.append(f"{person_type}: {text}")
        
        return "\n".join(history_lines)

    print("🚀 에이전트 테스트")
    print("=" * 100)
    
    if not setup_dspy():
        print("❌ DSPy 설정 실패로 테스트를 중단합니다.")
        exit(1)

    test_cases = [
        {
            "request": "저 계정 탈퇴 어떻게 하나요?",
            "messages": [
                {"personType": "user", "plainText": "안녕하세요!"},
                {"personType": "user", "plainText": "김철수입니다."},
                {"personType": "user", "plainText": "010-1234-5678"},
            ]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):        
        chat_history = create_chat_history_from_messages(test_case['messages'])
        full_chat_history = f"{chat_history}\n고객: {test_case['request']}" if chat_history else f"고객: {test_case['request']}"
        
        print(f"📱 채팅 기록:\n{full_chat_history}")
        print("=" * 100)
        
        try:
            result = route_request(test_case['request'], full_chat_history)
            print(f"🎯 응답:\n{result['response']}")
        except Exception as e:
            print(f"❌ 테스트 실행 중 오류: {e}")