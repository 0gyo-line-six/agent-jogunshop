import dspy

class DeliveryAgent(dspy.Signature):
    """배송 관련 문의를 처리하는 상담원입니다."""

    user_request: str = dspy.InputField()
    delivery_result: str = dspy.OutputField(desc="배송 관련 문의에 대한 답변")

delivery_agent = dspy.ChainOfThought(DeliveryAgent)

def run_delivery_agent(user_request: str):
    """배송 에이전트를 실행합니다."""
    try:
        prediction = delivery_agent(user_request=user_request)
        return prediction
    except Exception as e:
        print(f"배송 에이전트 오류: {e}")
        return None