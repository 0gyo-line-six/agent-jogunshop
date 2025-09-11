"""
AWS Lambda 핸들러 진입점
"""
import json
import uuid
from core.webhook import webhook_main_handler
from core.config import initialize

def lambda_handler(event, context):
    """AWS Lambda 핸들러 함수"""
    # 요청 ID 생성
    request_id = str(uuid.uuid4())[:16]
    
    try:
        # 애플리케이션 초기화
        initialize()
        
        # 웹훅 이벤트 처리
        result, status_code = webhook_main_handler(event, request_id)
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(result, ensure_ascii=False)
        }
    
    except Exception as e:
        print(f"Lambda 핸들러 오류: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'ERROR',
                'message': 'Internal server error'
            }, ensure_ascii=False)
        }
