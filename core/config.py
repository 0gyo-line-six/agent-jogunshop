"""
공통 설정 및 환경변수 관리 모듈
"""
import os
import dspy
from dotenv import load_dotenv
load_dotenv()


class Config:
    """설정 클래스"""
    
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
    AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')
    AZURE_OPENAI_DEPLOYMENT_ID = os.getenv('AZURE_OPENAI_DEPLOYMENT_ID')
    
    # Channel API
    CHANNEL_API_BASE_URL = os.getenv('CHANNEL_API_BASE_URL')
    CHANNEL_ACCESS_KEY = os.getenv('CHANNEL_ACCESS_KEY')
    CHANNEL_ACCESS_SECRET = os.getenv('CHANNEL_ACCESS_SECRET')

    # DynamoDB
    DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')
    
    # Step Functions
    STATE_MACHINE_ARN = os.getenv('STATE_MACHINE_ARN')

    ONTOLOGY_PATH = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "ontology.owl")
    )
    
    @classmethod
    def validate_azure_config(cls) -> bool:
        """Azure OpenAI 설정 검증"""
        required_vars = [
            cls.AZURE_OPENAI_DEPLOYMENT_ID,
            cls.AZURE_OPENAI_API_KEY,
            cls.AZURE_OPENAI_ENDPOINT,
            cls.AZURE_OPENAI_API_VERSION
        ]
        return all(var is not None for var in required_vars)
    
    @classmethod
    def get_missing_vars(cls) -> list:
        """누락된 환경변수 목록 반환"""
        missing = []
        if not cls.AZURE_OPENAI_DEPLOYMENT_ID:
            missing.append("AZURE_OPENAI_DEPLOYMENT_ID")
        if not cls.AZURE_OPENAI_API_KEY:
            missing.append("AZURE_OPENAI_API_KEY")
        if not cls.AZURE_OPENAI_ENDPOINT:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not cls.AZURE_OPENAI_API_VERSION:
            missing.append("AZURE_OPENAI_API_VERSION")
        return missing

_dspy_configured = False

def configure_dspy():
    """DSPy 언어 모델 설정"""
    global _dspy_configured
    
    if _dspy_configured:
        print("✅ DSPy 이미 설정됨")
        return True
    
    if not Config.validate_azure_config():
        missing_vars = Config.get_missing_vars()
        raise ValueError(
            f"DSPy 설정 실패: 누락된 환경변수 - {', '.join(missing_vars)}\n"
            ".env 파일을 확인하세요."
        )
    
    try:
        lm = dspy.LM(
            f'azure/{Config.AZURE_OPENAI_DEPLOYMENT_ID}',
            api_key=Config.AZURE_OPENAI_API_KEY,
            api_base=Config.AZURE_OPENAI_ENDPOINT,
            api_version=Config.AZURE_OPENAI_API_VERSION,
            max_tokens=None,
            temperature=None,
            extra_body={
                "max_completion_tokens": 4096,
            }
        )
        
        dspy.settings.configure(lm=lm)
        _dspy_configured = True
        print("✅ DSPy 설정 완료")
        return True
        
    except Exception as e:
        print(f"❌ DSPy 설정 실패: {e}")
        return False

# 전역 config 인스턴스
config = Config()

def log(request_id: str, level: str, message: str):
    """간단한 로깅 함수"""
    print(f"[{request_id}][{level}] {message}")

def initialize():
    """애플리케이션 초기화 함수 - 명시적으로 호출 필요"""
    print("🚀 애플리케이션 초기화 중...")
    configure_dspy()
    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("DSPy-SPARQL-Agent")
    mlflow.dspy.autolog()
    print("✅ 애플리케이션 초기화 완료")