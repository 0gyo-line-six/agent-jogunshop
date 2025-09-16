import dspy

class GeneralResponseRefiner(dspy.Signature):
    """일반 문의 응답을 자연스럽고 간결하게 정리하는 도우미입니다.
    
    일반 문의에 대한 응답을 받아서 상담원처럼 친절하면서도 
    간결하게 정리합니다. 과도한 인사말이나 불필요한 부가 설명은 
    제거하고 핵심 내용만 전달합니다.
    
    정리 원칙:
    - 고객의 질문에 직접적으로 답변
    - 친절하지만 간결한 톤
    - 불필요한 추가 질문 유도 제거
    """
    
    original_response: str = dspy.InputField(desc="원본 일반 문의 응답")
    refined_response: str = dspy.OutputField(desc="정리된 친절하고 간결한 응답")

class GeneralAgent(dspy.Signature):
    """일반적인 문의를 처리하는 상담원입니다.
    
    상품이나 배송 관련이 아닌 일반적인 고객 문의를 처리합니다.
    친절하고 도움이 되는 답변을 제공하되, 간결하게 응답합니다.
    """

    user_request: str = dspy.InputField()
    general_result: str = dspy.OutputField(desc="일반 문의에 대한 친절하고 간결한 응답")

general_agent = dspy.ChainOfThought(GeneralAgent)
general_response_refiner = dspy.ChainOfThought(GeneralResponseRefiner)

def run_general_agent(user_request: str, chat_history: str):
    """일반 에이전트를 실행합니다."""
    try:
        prediction = general_agent(user_request=user_request)
        
        # 응답 정리 적용
        if hasattr(prediction, 'general_result') and prediction.general_result:
            original_result = prediction.general_result
            try:
                refined_prediction = general_response_refiner(original_response=original_result)
                refined_result = getattr(refined_prediction, 'refined_response', original_result)
                prediction.general_result = refined_result
            except Exception as e:
                print(f"⚠️ 일반 응답 정리 중 오류: {e}")
                # 오류 시 원본 사용
        
        return prediction
    except Exception as e:
        print(f"일반 에이전트 오류: {e}")
        # 에러 시 기본 응답 반환
        class DefaultResponse:
            def __init__(self):
                self.general_result = "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."
        return DefaultResponse()
