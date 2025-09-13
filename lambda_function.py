"""
AWS Lambda 핸들러 진입점
"""
import os, time, json, uuid
os.environ['HOME'] = '/tmp'
os.environ['DSPY_CACHE_DIR'] = '/tmp/dspy_cache'
cache_dir = '/tmp/dspy_cache'
os.makedirs(cache_dir, exist_ok=True)
from core.config import log
from core.webhook import webhook_main_handler
from core.config import config
from core.ontology_manager import get_ontology_manager
import dspy
import openai

_dspy_configured = False
_ontology_initialized = False

def ensure_dspy_configured():
    """DSPy 설정을 한 번만 실행하도록 보장"""
    global _dspy_configured
    if not _dspy_configured:
        if not config.is_dspy_ready:
            raise ValueError("DSPy 설정이 준비되지 않았습니다. Azure OpenAI 또는 캐시 디렉토리 설정을 확인하세요.")

        lm = dspy.LM(
            f'azure/{config.AZURE_OPENAI_DEPLOYMENT_ID}',
            api_key=config.AZURE_OPENAI_API_KEY,
            api_base=config.AZURE_OPENAI_ENDPOINT,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )
        dspy.settings.configure(lm=lm, cache_dir=config.DSPY_CACHE_DIR)
        _dspy_configured = True

def ensure_ontology_initialized():
    """온톨로지 매니저 초기화를 한 번만 실행하도록 보장"""
    global _ontology_initialized
    if not _ontology_initialized:
        ontology_manager = get_ontology_manager()
        if ontology_manager.is_loaded():
            log("GLOBAL", "LAMBDA_INIT", "온톨로지 로딩 완료")
        else:
            log("GLOBAL", "LAMBDA_INIT", "온톨로지 로딩 실패 - S3 연결 또는 파일 확인 필요")
        _ontology_initialized = True

try:
    start_time = time.time()
    ensure_dspy_configured()
    end_time = time.time()
    log("GLOBAL", "LAMBDA_INIT", f"DSPy 설정 완료. ({end_time - start_time:.1f}초)")
    log("GLOBAL", "LAMBDA_INIT", f"openai version: {getattr(openai, '__version__', 'unknown')}")
    
    # 온톨로지 초기화
    ontology_start_time = time.time()
    ensure_ontology_initialized()
    ontology_end_time = time.time()
    log("GLOBAL", "LAMBDA_INIT", f"온톨로지 초기화 완료. ({ontology_end_time - ontology_start_time:.1f}초)")
except Exception as e:
    log("GLOBAL", "LAMBDA_INIT_ERROR", f"초기화 실패: {e}")

def lambda_handler(event, context):
    """AWS Lambda 핸들러 함수"""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:16]
    log(request_id, "LAMBDA", "새로운 웹훅 요청 처리 시작")

    try:
        if isinstance(event.get('body'), str):
            request_json = json.loads(event['body'])
            log(request_id, "LAMBDA", f"JSON 문자열 파싱 완료")
        elif event.get("source") == "chat-scheduler":
            request_json = event
            log(request_id, "LAMBDA", "Scheduler에 의한 직접 호출 감지")
        else:
            log(request_id, "ERROR", "올바르지 않은 요청 형식")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"status": "ERROR", "message": "Invalid request format"})
            }
        result_data, status_code = webhook_main_handler(request_json, request_id)        
        log(request_id, "LAMBDA", f"처리 완료: {result_data.get('status', 'unknown')} (HTTP {status_code})")
        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result_data)
        }
    except Exception as e:
        log(request_id, "ERROR", f"웹훅 요청 처리 중 예외 발생: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"status": "ERROR", "message": "Internal server error"})
        }
    finally:
        end_time = time.time()
        log(request_id, "LAMBDA", f"웹훅 요청 처리 종료 ({end_time - start_time:.1f}초)")