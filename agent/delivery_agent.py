import dspy
import os

class ResponseStyleConverter(dspy.Signature):
    """배송 관련 응답을 간결하고 핵심적으로 정리하는 도우미입니다.
    
    배송 정책 기반 응답을 받아서 핵심 정보만 간결하게 전달합니다.
    불필요한 인사말, 부가 설명, 추가 질문 유도 등은 제거하고 
    질문에 대한 직접적인 답변만 제공합니다.
    
    정리 예시:
    - "안녕하세요. 조건샵 배송비는 2,500원이며, 7만원 이상 구매시 무료배송입니다. 감사합니다." 
      → "배송비는 2,500원, 7만원 이상 무료배송입니다."
    - "배송기간은 영업일 기준 최대 7일이내입니다. 지연시 부분배송 진행됩니다."
      → "최대 7일이내 배송, 지연시 부분배송."
    
    주의사항:
    - 핵심 정보는 누락하지 않음
    - 간결하지만 이해하기 쉽게
    - 정중한 톤은 유지하되 불필요한 표현 제거
    """
    
    original_response: str = dspy.InputField(desc="원본 배송 관련 응답")
    refined_response: str = dspy.OutputField(desc="간결하게 정리된 핵심 응답")

response_converter = dspy.ChainOfThought(ResponseStyleConverter)

def adjust_response_style(response: str) -> str:
    if not response or not isinstance(response, str):
        return response
    
    try:
        prediction = response_converter(original_response=response)
        converted_response = getattr(prediction, 'refined_response', response)
        return converted_response.strip()
    except Exception as e:
        print(f"⚠️ 응답 스타일 변환 중 오류: {e}")
        return "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다."

def load_delivery_policy():
    """배송 정책 파일을 로드합니다."""
    try:
        import boto3
        from core.config import config
        
        # S3에서 배송 정책 파일 다운로드 시도
        try:
            s3_client = boto3.client('s3', region_name=config.AWS_REGION)
            response = s3_client.get_object(
                Bucket=config.S3_BUCKET_NAME,
                Key='policy.txt'
            )
            content = response['Body'].read().decode('utf-8')
            print("✅ S3에서 정책 파일 로드 성공")
            return content
        except Exception as s3_error:
            print(f"❌ S3에서 배송 정책 파일 로드 실패: {s3_error}")
            return "배송 정책 정보를 불러올 수 없습니다."
                
    except Exception as e:
        print(f"⚠️ 배송 정책 파일 로드 오류: {e}")
        return "배송 정책 정보를 불러올 수 없습니다."

class DeliveryAgent(dspy.Signature):
    """배송 관련 문의를 처리하는 전문 상담원입니다.
    
    사용자의 질문에만 간결하고 정확하게 답변합니다.
    불필요한 인사말이나 추가 설명 없이 핵심 정보만 제공합니다.
    """

    user_request: str = dspy.InputField(desc="사용자의 배송 관련 문의")
    delivery_policy: str = dspy.InputField(desc="조건샵의 배송 정책 및 택배사 정보")
    delivery_result: str = dspy.OutputField(desc="질문에 대한 간결하고 정확한 답변 (핵심 정보만)")

delivery_agent = dspy.ChainOfThought(DeliveryAgent)

def run_delivery_agent(user_request: str, chat_history: str):
    """배송 에이전트를 실행합니다."""
    try:
        delivery_policy = load_delivery_policy()
        
        print(f"🚚 배송 문의 처리 중: {user_request}")
        
        prediction = delivery_agent(
            user_request=user_request,
            delivery_policy=delivery_policy
        )
        
        if hasattr(prediction, 'delivery_result') and prediction.delivery_result:
            original_result = prediction.delivery_result
            concise_result = adjust_response_style(original_result)
            prediction.delivery_result = concise_result
        return prediction
        
    except Exception as e:
        print(f"❌ 배송 에이전트 오류: {e}")
        class DefaultResponse:
            def __init__(self):
                self.delivery_result = "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."
        return DefaultResponse()
