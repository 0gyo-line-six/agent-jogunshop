import dspy
import os

class ResponseStyleConverter(dspy.Signature):
    """
    - 배송/반품/환불 관련 응답을 상담원처럼 자연스럽게 변환.
    - 배송 정책 기반 응답을 받아 핵심만 간결하게 제공.
    - 친절하면서도 직접적인 안내 톤 유지.

    [규칙]
    - 과도한 인사말, 영업 멘트, 질문 유도 제거
    - 수치·기간·택배사명·비용 등은 빠짐없이 안내
    - '고객님께서 부담하셔야 합니다'와 같은 상담 톤 표현 사용
    - 불가/제한 시: "현재 불가한 점 양해 부탁드립니다."로 마무리
    - 신용카드 결제 환불하려는데 결제 대금이 청구된 경우: "신용카드 결제대금이 청구된 경우에는 익월 신용카드 대금청구시 카드사에서 환급처리 됩니다"

    [예시 변환]
    - "주문하시면 3~7일 이내에 CJ대한통운으로 배송됩니다."
      → "오늘 주문하시면 3~7일 이내에 CJ대한통운을 통해 배송됩니다."
    - "일부 도서산간 지역은 배송 불가합니다."
      → "도서산간 지역은 현재 배송이 제공되지 않습니다."
    - "단순 변심 반품 시 왕복 배송비 6,000원이 부과되며, 환불은 반품 확인 후 2~4 영업일 이내에 처리됩니다."
      → "단순 변심으로 반품하실 경우 고객님께서 왕복 배송비 6,000원을 부담하셔야 하며, 환불은 반품 확인 후 2~4 영업일 이내에 처리됩니다."
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
        print(converted_response)
        return converted_response.strip()
    except Exception as e:
        print(f"⚠️ 응답 스타일 변환 중 오류: {e}")
        return "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리겠습니다."

def load_delivery_policy():
    """배송 정책 파일을 로드합니다."""
    try:
        import boto3
        from core.config import config
        
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
    
    - 사용자의 질문에만 간결하고 정확하게 답변합니다.
    - 불필요한 인사말이나 추가 설명 없이 핵심 정보만 제공합니다.
    - 응답은 항상 친절하면서도 직접적인 톤을 유지합니다.
    - 배송 정책 기반 응답에서 필요한 정보만 간결히 안내합니다.
    """

    user_request: str = dspy.InputField(desc="사용자의 배송 관련 문의")
    delivery_policy: str = dspy.InputField(desc="배송 정책 및 택배사 정보")
    delivery_result: str = dspy.OutputField(desc="질문에 대한 간결하고 정확한 답변")

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
