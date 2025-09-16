"""
온톨로지 관리 모듈
온톨로지 로딩, 캐싱, SPARQL 쿼리 등을 중앙화하여 관리
"""
import os
import boto3
from io import BytesIO
from typing import Optional, List, Tuple
from owlready2 import get_ontology, sync_reasoner
from core.config import config

class OntologyManager:
    """온톨로지 관리를 위한 싱글톤 클래스"""
    
    _instance: Optional['OntologyManager'] = None
    _ontology = None
    _namespace = None
    
    def __new__(cls) -> 'OntologyManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_ontology(run_reasoner=False)
    
    def _download_ontology_from_s3(self) -> bool:
        """S3에서 온톨로지 파일 다운로드 (이미 있으면 스킵)"""
        try:
            if not config.is_s3_ready:
                print("❌ S3 설정이 준비되지 않았습니다.")
                return False
            
            if os.path.exists(config.LAMBDA_ONTOLOGY_PATH) and os.path.getsize(config.LAMBDA_ONTOLOGY_PATH) > 0:
                print(f"✅ 기존 온톨로지 파일 사용: {config.LAMBDA_ONTOLOGY_PATH}")
                return True
            
            s3_client = boto3.client('s3', region_name=config.AWS_REGION)
            os.makedirs(os.path.dirname(config.LAMBDA_ONTOLOGY_PATH), exist_ok=True)
            s3_client.download_file(
                config.S3_BUCKET_NAME,
                config.ONTOLOGY_S3_KEY,
                config.LAMBDA_ONTOLOGY_PATH
            )
            
            return os.path.exists(config.LAMBDA_ONTOLOGY_PATH)
        except Exception as e:
            print(f"❌ S3 다운로드 실패: {e}")
            return False
    
    from io import StringIO

    from io import BytesIO

    from io import BytesIO

    def _load_ontology(self, run_reasoner: bool = False) -> None:
        """온톨로지 로딩 (Lambda 안전 모드: BytesIO 기반)
        
        Args:
            run_reasoner (bool): True면 HermiT 실행 (Java 필요), 기본 False
        """
        try:
            if not self._download_ontology_from_s3():
                self._ontology = None
                self._namespace = None
                return
            
            ontology_path = config.LAMBDA_ONTOLOGY_PATH
            abs_path = os.path.abspath(ontology_path)

            if not os.path.exists(abs_path):
                print(f"❌ 온톨로지 파일 없음: {abs_path}")
                return

            size = os.path.getsize(abs_path)
            print(f"📂 온톨로지 로딩: {abs_path}")
            print(f"📏 파일 크기: {size} bytes")

            import owlready2
            owlready2.onto_path.clear()
            owlready2.onto_path.append("/tmp")

            # 메모리 모드 우선
            try:
                owlready2.default_world.set_backend(filename=":memory:")
                print("💾 owlready2 백엔드: 메모리 모드")
            except Exception:
                sqlite_path = "/tmp/ontology.db"
                owlready2.default_world.set_backend(filename=sqlite_path)
                print(f"💾 owlready2 백엔드: SQLite({sqlite_path})")

            with open(abs_path, "rb") as f:
                content = f.read()

            onto = get_ontology("http://example.org/local_ontology.owl")
            onto.load(fileobj=BytesIO(content), only_local=True)

            print("✅ 온톨로지 로딩 성공")
            self._ontology = onto
            self._namespace = getattr(onto, "base_iri", "http://example.org/product-inquiry#")

            if run_reasoner:
                try:
                    with onto:
                        sync_reasoner()
                    print("✅ 추론기 동기화 완료")
                except Exception as e:
                    print(f"⚠️ 추론기 동기화 실패: {e}")
            else:
                print("ℹ️ 추론기 실행 건너뜀 (옵션 비활성화)")

        except Exception as e:
            print(f"❌ 온톨로지 로딩 실패: {e}")
            self._ontology = None
            self._namespace = None

    @property
    def ontology(self):
        return self._ontology
    
    @property
    def namespace(self) -> str:
        return self._namespace or "http://example.org/product-inquiry#"
    
    def is_loaded(self) -> bool:
        return self._ontology is not None
    
    def execute_sparql(self, query: str) -> List[Tuple]:
        if not self.is_loaded():
            print("❌ 온톨로지가 로딩되지 않았습니다.")
            return []
        try:
            return list(self._ontology.world.sparql(query))
        except Exception as e:
            print(f"❌ SPARQL 실행 실패: {e}")
            return []
    
    def get_all_products(self) -> List[str]:
        if not self.is_loaded():
            return []
        Product = getattr(self._ontology, "Product", None)
        if not Product:
            return []
        return [str(p.productName[0]) for p in Product.instances() if getattr(p, "productName", [])]

ontology_manager = OntologyManager()

def get_ontology_manager() -> OntologyManager:
    return ontology_manager
