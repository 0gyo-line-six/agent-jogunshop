import json, requests, boto3, time, uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional
from core.config import config, log
from agent.router import route_request

dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')

class TimeUtils:
    """시간 관련 유틸리티 클래스"""
    KST = timezone(timedelta(hours=9))
    
    @classmethod
    def now_kst(cls) -> datetime:
        return datetime.now(cls.KST)
    
    @classmethod  
    def kst_timestamp(cls) -> int:
        return int(cls.now_kst().timestamp())

@dataclass
class ParseResult:
    """웹훅 파싱 결과"""
    chat_id: Optional[str]
    message: str
    is_valid: bool

class WebhookParser:
    """웹훅 페이로드 파싱 및 검증 담당"""
    def __init__(self, request_id: str):
        self.request_id = request_id
    
    def parse(self, payload: Dict[str, Any]) -> ParseResult:
        """페이로드를 파싱하고 유효성을 검사"""
        start_time = time.time()
        webhook_type = payload.get("type")
        entity = payload.get("entity", {})
        refers = payload.get("refers", {})
        chat_id, message, person_type = None, "", ""
        
        if webhook_type == "userChat":
            chat_id = entity.get("id")
            message = refers.get("message", {}).get("plainText", "")
            person_type = refers.get("message", {}).get("personType")
        elif webhook_type == "message":
            chat_id = entity.get("chatId")
            message = entity.get("plainText", "")
            person_type = entity.get("personType")

        end_time = time.time()
        log(self.request_id, "WEBHOOK", f"페이로드 파싱 완료: {end_time - start_time:.1f}초")
        log(self.request_id, "WEBHOOK", f"chat_id: {chat_id}, webhook_type: {webhook_type}, message: {message}, person_type: {person_type}")
        
        if not chat_id or not message or person_type != "user":
            log(self.request_id, "ERROR", "처리 대상이 아닌 메시지 (chat_id, message, personType 누락/불일치)")
            return ParseResult(None, "", False)

        return ParseResult(chat_id, message.strip(), True)

class MessageRepository:
    """DynamoDB를 사용한 채팅 상태 관리"""
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)
    
    def update_state(self, chat_id: str, new_message: str) -> bool:
        """DynamoDB 이용하여 상태를 안전하게 업데이트"""
        log(self.request_id, "DYNAMODB", f"상태 업데이트 시작: chat_id={chat_id}")
        start_time = time.time()
        try:
            self.table.update_item(
                Key={'chat_id': chat_id},
                UpdateExpression="SET #msgs = list_append(if_not_exists(#msgs, :empty_list), :new_vals), #ts = :ts",
                ExpressionAttributeNames={'#msgs': 'message_list', '#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':new_vals': [new_message],
                    ':empty_list': [],
                    ':ts': TimeUtils.kst_timestamp()
                }
            )
            end_time = time.time()
            log(self.request_id, "DYNAMODB", f"상태 업데이트 성공 ({end_time - start_time:.1f}초)")
            return True
        except Exception as e:
            log(self.request_id, "ERROR", f"상태 업데이트 실패: {e}")
            return False
    
    def get_and_clear_state(self, chat_id: str) -> str:
        """최종 메시지 상태를 가져온 후, 해당 아이템을 삭제"""
        log(self.request_id, "DYNAMODB", f"상태 조회 및 삭제 시작: chat_id={chat_id}")
        start_time = time.time()
        try:   
            response = self.table.delete_item(
                Key={'chat_id': chat_id},
                ReturnValues='ALL_OLD'
            )
            attrs = response.get('Attributes', {}) or {}

            parts = attrs.get('message_list')
            if isinstance(parts, list):
                message = " ".join([p for p in parts if isinstance(p, str)]).strip()
            else:
                legacy = attrs.get('message')
                if isinstance(legacy, list):
                    message = " ".join([p for p in legacy if isinstance(p, str)]).strip()
                elif isinstance(legacy, str):
                    message = legacy.strip()
                else:
                    message = ""

            end_time = time.time()
            log(self.request_id, "DYNAMODB", f"'{message}' 조회 및 삭제 성공 ({end_time - start_time:.1f}초)")
            return message
        except Exception as e:
            log(self.request_id, "ERROR", f"상태 조회 및 삭제 실패: {e}")
            return ""

class StepFunctionsClient:
    """Step Functions를 이용한 채팅 처리 작업 스케줄링"""
    def __init__(self, request_id: str):
        self.request_id = request_id
    
    def start_execution(self, chat_id: str) -> bool:
        """지정된 시간 후에 처리를 위한 Step Functions 워크플로우를 시작합니다."""
        execution_prefix = f"chat-processing-{chat_id}"
        
        log(self.request_id, "SFN", f"Step Functions 실행 시도: {execution_prefix}")
        start_time = time.time()
        
        if not config.STATE_MACHINE_ARN:
            log(self.request_id, "ERROR", "STATE_MACHINE_ARN 환경변수가 설정되지 않았습니다.")
            return False
        
        try:
            executions = sfn_client.list_executions(
                stateMachineArn=config.STATE_MACHINE_ARN,
                statusFilter='RUNNING'
            )['executions']

            for exec in executions:
                if exec['name'].startswith(execution_prefix):
                    log(self.request_id, "SFN", f"기존 실행 중단 (타이머 리셋): {exec['name']}")
                    try:
                        sfn_client.stop_execution(
                            executionArn=exec['executionArn'],
                            error='NewMessageReceived',
                            cause='새 메시지 수신으로 인한 타이머 리셋'
                        )
                    except sfn_client.exceptions.ExecutionDoesNotExist:
                        log(self.request_id, "INFO", f"이미 종료된 실행이므로 중단 건너뜀: {exec['name']}")
                        pass
                    except Exception as e:
                        log(self.request_id, "WARNING", f"기존 실행 중단 실패: {e}")
                    break

            random_suffix = uuid.uuid4().hex[:8]
            unique_execution_name = f"{execution_prefix}-{TimeUtils.kst_timestamp()}-{random_suffix}"

            sfn_client.start_execution(
                stateMachineArn=config.STATE_MACHINE_ARN,
                name=unique_execution_name,
                input=json.dumps({"source": "chat-scheduler", "chat_id": chat_id}),
            )
            end_time = time.time()
            log(self.request_id, "SFN", f"작업 예약 성공: {unique_execution_name} ({end_time - start_time:.1f}초)")
            return True
        except Exception as e:
            log(self.request_id, "ERROR", f"Step Functions 실행 실패: {e}")
            return False

class MessageOrchestrator:
    """수신된 메시지의 후속 처리(상태 업데이트, 실행)를 총괄하는 클래스"""
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.repository = MessageRepository(request_id)
        self.scheduler = StepFunctionsClient(request_id)
        
    def orchestrate_processing(self, chat_id: str, message: str) -> bool:
        """메시지 상태를 업데이트하고 최종 처리를 예약"""
        if not self.repository.update_state(chat_id, message):
            return False            
        if not self.scheduler.start_execution(chat_id):
            return False
            
        return True

class ChatService:
    """채팅 관련 비즈니스 로직 처리"""
    def __init__(self, chat_id: str, request_id: str):
        self.chat_id = chat_id
        self.request_id = request_id
        if not self.chat_id:
            raise ValueError("chat_id는 필수입니다")
    
    def generate_reply(self, last_message: str) -> str:
        log(self.request_id, "WEBHOOK", f"AI 응답 생성 시작: '{last_message}'")
        start_time = time.time()
        try:
            result = route_request(last_message)
            end_time = time.time()
            log(self.request_id, "WEBHOOK", f"AI 응답 생성 완료: '{last_message}' ({end_time - start_time:.1f}초)")
            return result.get('response', '보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다.')
        except Exception as e:
            log(self.request_id, "ERROR", f"응답 생성 중 오류: {e}")
            return "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."

    def fetch_history(self, limit: int = 200) -> List[Dict]:
        url = f"{config.CHANNEL_API_BASE_URL}/user-chats/{self.chat_id}/messages"
        headers = { "accept": "application/json", "x-access-key": config.CHANNEL_ACCESS_KEY, "x-access-secret": config.CHANNEL_ACCESS_SECRET }
        params = {"sortOrder": "desc", "limit": limit}
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            messages = response.json().get('messages', [])
            history = [{"personType": msg.get("personType"), "plainText": msg.get("plainText")} for msg in messages if msg.get("plainText")]
            return list(reversed(history))[:-1]
        except requests.RequestException as e:
            log(self.request_id, "ERROR", f"채팅 히스토리 조회 실패: {e}")
            return []

    def send_reply(self, message: str) -> Tuple[Dict[str, str], int]:
        log(self.request_id, "WEBHOOK", f"메시지 전송 시작: '{message}'")
        start_time = time.time()
        if not config.is_channel_api_ready:
            return {"status": "OK", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200
        url = f"{config.CHANNEL_API_BASE_URL}/user-chats/{self.chat_id}/messages"
        headers = { "accept": "application/json", "Content-Type": "application/json", "x-access-key": config.CHANNEL_ACCESS_KEY, "x-access-secret": config.CHANNEL_ACCESS_SECRET }
        payload = {"blocks": [{"type": "text", "value": message}]}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                end_time = time.time()
                log(self.request_id, "WEBHOOK", f"메시지 전송 성공: '{message}' ({end_time - start_time:.1f}초)")
                return {"status": "OK", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200
            else:
                log(self.request_id, "ERROR", f"메시지 전송 실패: {response.status_code} {response.text}")
                return {"status": "ERROR", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200
        except requests.RequestException as e:
            log(self.request_id, "ERROR", f"메시지 전송 중 네트워크 오류: {e}")
            return {"status": "ERROR", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200

class WebhookHandler:
    """새로운 웹훅 메시지 수신 처리"""
    def __init__(self, payload: Dict[str, Any], request_id: str):
        self.parser = WebhookParser(request_id)
        self.orchestrator = MessageOrchestrator(request_id)
        self.payload = payload

    def handle_new_message(self) -> Tuple[Dict[str, str], int]:
        """새로운 메시지를 수신하고 후속 처리"""
        parse_result = self.parser.parse(self.payload)
        if not parse_result.is_valid:
            return {"status": "OK", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200
        
        if self.orchestrator.orchestrate_processing(parse_result.chat_id, parse_result.message):
            return {"status": "OK", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200
        else:
            return {"status": "ERROR", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 500

class ScheduledChatProcessor:
    """스케줄된 작업 처리"""
    def __init__(self, request_id: str):
        self.repository = MessageRepository(request_id)
        self.request_id = request_id
    
    def process(self, chat_id: str) -> Tuple[Dict[str, str], int]:
        """스케줄러에 의해 호출되어, 모아진 메시지를 최종 처리"""
        log(self.request_id, "WEBHOOK", f"예약된 작업 시작: chat_id={chat_id}")

        last_message = self.repository.get_and_clear_state(chat_id)
        if not last_message:
            log(self.request_id, "INFO", "처리할 메시지가 없음 (이미 다른 프로세스에서 처리됨)")
            return {"status": "OK", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200

        chat_service = ChatService(chat_id, self.request_id)
        reply_message = chat_service.generate_reply(last_message)
        
        if reply_message:
            return chat_service.send_reply(reply_message)
        else:
            log(self.request_id, "ERROR", "생성된 응답 없음")
            return {"status": "OK", "message": "보다 정확하고 친절한 안내를 위해 확인 중입니다. 잠시 기다려주시면 빠른 응대 도와드리게습니다."}, 200

def webhook_main_handler(event: Dict[str, Any], request_id: str) -> Tuple[Dict, int]:
    """Lambda의 메인 핸들러 - 이벤트에 따라 적합한 핸들러로 분기"""
    if event.get("source") == "chat-scheduler":
        chat_id = event.get("chat_id")
        processor = ScheduledChatProcessor(request_id)
        return processor.process(chat_id)
    else:
        handler = WebhookHandler(event, request_id)
        return handler.handle_new_message()
    
if __name__ == "__main__":
    test_chat_id = "test-chat-123"
    test_request_id = str(uuid.uuid4())[:16]

    sfn_event = {
        "source": "chat-scheduler",
        "chat_id": test_chat_id
    }
    
    repo = MessageRepository(test_request_id)
    repo.update_state(test_chat_id, "안녕하세요")
    repo.update_state(test_chat_id, "사이즈 문의드립니다!")
    print(f"테스트 메시지 상태 추가 완료: chat_id={test_chat_id}")
    
    result, status_code = webhook_main_handler(sfn_event, test_request_id)
    print(f"Step Functions 스케줄러 처리 결과: {result}, 상태 코드: {status_code}")