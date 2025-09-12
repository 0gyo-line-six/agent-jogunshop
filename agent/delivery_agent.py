import dspy
import os

def load_delivery_policy():
    """배송 정책 파일을 로드합니다."""
    try:
        # 현재 파일의 디렉토리를 기준으로 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        policy_path = os.path.join(project_root, "data", "delivery_policy.txt")
        
        with open(policy_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("⚠️ 배송 정책 파일을 찾을 수 없습니다.")
        return "배송 정책 정보를 불러올 수 없습니다."
    except Exception as e:
        print(f"⚠️ 배송 정책 파일 로드 오류: {e}")
        return "배송 정책 정보를 불러올 수 없습니다."

class DeliveryAgent(dspy.Signature):
    """배송 관련 문의를 처리하는 전문 상담원입니다.
    
    배송 정책, 배송비, 배송 시간, 택배사 정보, 교환/반품 등 
    배송과 관련된 모든 문의에 대해 정확하고 친절한 답변을 제공합니다.
    """

    user_request: str = dspy.InputField(desc="사용자의 배송 관련 문의")
    delivery_policy: str = dspy.InputField(desc="조건샵의 배송 정책 및 택배사 정보")
    delivery_result: str = dspy.OutputField(desc="배송 정책을 바탕으로 한 정확하고 친절한 답변")

delivery_agent = dspy.ChainOfThought(DeliveryAgent)

def run_delivery_agent(user_request: str):
    """배송 에이전트를 실행합니다."""
    try:
        # 배송 정책 정보 로드
        delivery_policy = load_delivery_policy()
        
        print(f"🚚 배송 문의 처리 중: {user_request}")
        
        # DSPy 에이전트 실행
        prediction = delivery_agent(
            user_request=user_request,
            delivery_policy=delivery_policy
        )
        
        print(f"✅ 배송 문의 처리 완료")
        return prediction
        
    except Exception as e:
        print(f"❌ 배송 에이전트 오류: {e}")
        # 에러 시 기본 응답 반환
        class DefaultResponse:
            def __init__(self):
                self.delivery_result = "죄송합니다. 배송 관련 문의 처리 중 오류가 발생했습니다. 고객센터(1588-1234)로 문의해주시기 바랍니다."
        return DefaultResponse()

if __name__ == "__main__":
    """배송 에이전트 테스트"""
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

    print("🚚 조건샵 배송 에이전트 테스트")
    print("=" * 50)
    
    # DSPy 설정
    if not setup_dspy():
        print("❌ DSPy 설정 실패로 테스트를 중단합니다.")
        exit(1)
    
    # 테스트 케이스들
    test_cases = [
        "배송비가 얼마인가요?",
        "무료배송 조건이 어떻게 되나요?",
        "언제 발송되나요?",
        "배송 조회는 어떻게 하나요?",
        "제주도 배송 가능한가요?",
        "교환하고 싶은데 배송비가 얼마인가요?",
        "당일배송 가능한가요?",
        "주말에도 배송되나요?",
        "배송지 변경하고 싶어요",
        "CJ택배 연락처 알려주세요"
    ]
    
    for i, test_request in enumerate(test_cases, 1):
        print(f"\n🧪 테스트 {i}: {test_request}")
        print("-" * 40)
        
        try:
            result = run_delivery_agent(test_request)
            if result:
                print(f"✅ 답변: {result.delivery_result}")
            else:
                print("❌ 응답을 받지 못했습니다.")
        except Exception as e:
            print(f"❌ 테스트 실행 중 오류: {e}")
        
        print("=" * 50)
    
    print("\n🎯 배송 에이전트 테스트 완료!")