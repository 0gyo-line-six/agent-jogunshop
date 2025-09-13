import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """애플리케이션 설정 관리 클래스"""
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
    
    # DSPy 캐시 설정
    DSPY_CACHE_DIR = os.getenv('DSPY_CACHE_DIR', '/tmp/dspy_cache')
    
    # S3 설정
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'jogunshop-bucket')
    ONTOLOGY_S3_KEY = os.getenv('ONTOLOGY_S3_KEY', 'ontology.owl')
    LAMBDA_ONTOLOGY_PATH = '/tmp/ontology.owl'
    
    # AWS 설정
    AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
    
    @property
    def is_azure_openai_ready(self) -> bool:
        """Azure OpenAI 사용 준비 여부 확인"""
        return bool(self.AZURE_OPENAI_API_KEY and self.AZURE_OPENAI_ENDPOINT)
    
    @property
    def is_channel_api_ready(self) -> bool:
        """Channel API 사용 준비 여부 확인"""
        return bool(self.CHANNEL_ACCESS_KEY and self.CHANNEL_ACCESS_SECRET)
    
    @property
    def is_dspy_ready(self) -> bool:
        """DSPy 사용 준비 여부 확인"""
        return bool(self.is_azure_openai_ready and self.DSPY_CACHE_DIR)
    
    @property
    def is_state_machine_ready(self) -> bool:
        """Step Functions 사용 준비 여부 확인"""
        return bool(self.STATE_MACHINE_ARN)
    
    @property
    def is_s3_ready(self) -> bool:
        """S3 사용 준비 여부 확인"""
        return bool(self.S3_BUCKET_NAME and self.ONTOLOGY_S3_KEY)

config = Config()

def log(request_id: str, level: str, message: str):
    """통합 로깅 함수"""
    print(f"[{level}] [{request_id}] {message}")

def _print_config_status():
    """설정 상태를 출력하는 내부 함수"""
    print("[CONFIG] 애플리케이션 초기화 중...")
    print(f"[CONFIG] Azure OpenAI: {'✓ 사용가능' if config.is_azure_openai_ready else '✗ 미설정'}")
    print(f"[CONFIG] Channel API: {'✓ 사용가능' if config.is_channel_api_ready else '✗ 미설정'}")
    print(f"[CONFIG] DSPy: {'✓ 사용가능' if config.is_dspy_ready else '✗ 미설정'}")
    print(f"[CONFIG] DSPy 캐시 디렉토리: {config.DSPY_CACHE_DIR}")
    print(f"[CONFIG] Step Functions: {'✓ 사용가능' if config.is_state_machine_ready else '✗ 미설정'}")
    print(f"[CONFIG] S3: {'✓ 사용가능' if config.is_s3_ready else '✗ 미설정'}")
    print(f"[CONFIG] S3 버킷: {config.S3_BUCKET_NAME}")
    print(f"[CONFIG] 온톨로지 S3 키: {config.ONTOLOGY_S3_KEY}")

_print_config_status()