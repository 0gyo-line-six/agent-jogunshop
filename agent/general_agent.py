import dspy

class GeneralAgent(dspy.Signature):
    """일반적인 문의를 처리하는 상담원입니다."""

    user_request: str = dspy.InputField()
    general_result: str = dspy.OutputField(desc="일반 문의에 대한 응답")

general_agent = dspy.ChainOfThought(GeneralAgent)

def run_general_agent(user_request: str):
    """일반 에이전트를 실행합니다."""
    try:
        prediction = general_agent(user_request=user_request)
        return prediction
    except Exception as e:
        print(f"일반 에이전트 오류: {e}")
        return None
