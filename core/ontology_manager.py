"""
온톨로지 관리 모듈
온톨로지 로딩, 캐싱, SPARQL 쿼리 등을 중앙화하여 관리
"""
import os
import boto3
import tempfile
from typing import Optional, List, Tuple
from owlready2 import get_ontology, sync_reasoner, destroy_entity
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
            self._load_ontology()
    
    def _download_ontology_from_s3(self) -> Optional[str]:
        """S3에서 온톨로지 파일을 다운로드하여 임시 파일 경로를 반환합니다."""
        try:
            # S3 설정 확인
            s3_bucket = os.environ.get('ONTOLOGY_S3_BUCKET', '09women-bucket')
            s3_key = os.environ.get('ONTOLOGY_S3_KEY', 'ontology.owl')
            
            print(f"📥 S3에서 온톨로지 파일 다운로드 중... (버킷: {s3_bucket}, 키: {s3_key})")
            
            # S3 클라이언트 생성
            s3_client = boto3.client('s3')
            
            # 임시 파일 생성
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.owl')
            temp_path = temp_file.name
            temp_file.close()
            
            # S3에서 파일 다운로드
            s3_client.download_file(s3_bucket, s3_key, temp_path)
            
            print(f"✅ S3에서 온톨로지 파일 다운로드 완료: {temp_path}")
            return temp_path
            
        except Exception as e:
            print(f"❌ S3에서 온톨로지 파일 다운로드 실패: {e}")
            return None
    
    def _load_ontology(self) -> None:
        """온톨로지를 로딩하고 추론기를 동기화합니다."""
        temp_path = None
        try:
            # 먼저 S3에서 온톨로지 다운로드 시도
            temp_path = self._download_ontology_from_s3()
            
            if temp_path and os.path.exists(temp_path):
                ontology_path = temp_path
                print(f"📂 S3에서 다운로드한 온톨로지 파일 로딩 중: {ontology_path}")
                print(f"📋 파일 크기: {os.path.getsize(ontology_path)} bytes")
            else:
                # S3 다운로드 실패 시 로컬 파일 사용 (fallback)
                print("⚠️ S3 다운로드 실패, 로컬 파일로 fallback 시도")
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                ontology_path = os.path.join(project_root, "data", "ontology.owl")
                
                if not os.path.exists(ontology_path):
                    print(f"❌ 로컬 온톨로지 파일도 찾을 수 없습니다: {ontology_path}")
                    return
                
                print(f"📂 로컬 온톨로지 파일 로딩 중: {ontology_path}")
            
            # 파일 존재 및 가독성 재확인
            if not os.path.exists(ontology_path):
                print(f"❌ 온톨로지 파일이 존재하지 않습니다: {ontology_path}")
                return
            
            if not os.access(ontology_path, os.R_OK):
                print(f"❌ 온톨로지 파일에 읽기 권한이 없습니다: {ontology_path}")
                return
            
            print(f"📖 온톨로지 파일 읽기 시작: {ontology_path}")
            with open(ontology_path, "rb") as f:
                print("📊 온톨로지 파일 내용 로딩 중...")
                self._ontology = get_ontology("http://example.org/ontology.owl").load(fileobj=f)
            
            print("🔧 추론기 동기화 중...")
            with self._ontology:
                sync_reasoner()
            
            self._namespace = self._get_namespace()
            print("✅ 온톨로지 로딩 완료")
            
        except FileNotFoundError as e:
            print(f"❌ 온톨로지 파일을 찾을 수 없습니다: {e}")
            self._ontology = None
            self._namespace = None
        except PermissionError as e:
            print(f"❌ 온톨로지 파일 접근 권한이 없습니다: {e}")
            self._ontology = None
            self._namespace = None
        except Exception as e:
            print(f"❌ 온톨로지 로딩 실패: {e}")
            import traceback
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            self._ontology = None
            self._namespace = None
        finally:
            # 임시 파일 정리는 성공적으로 로딩한 후에만 수행
            if temp_path and os.path.exists(temp_path):
                # 로딩이 완료된 후 잠시 대기 후 삭제
                try:
                    import time
                    time.sleep(0.1)  # 파일 핸들이 완전히 닫힐 때까지 대기
                    os.unlink(temp_path)
                    print(f"🗑️ 임시 파일 삭제: {temp_path}")
                except Exception as e:
                    print(f"⚠️ 임시 파일 삭제 실패: {e} (이 오류는 무시해도 됩니다)")
    
    def _get_namespace(self) -> str:
        """온톨로지 네임스페이스를 반환합니다."""
        if not self._ontology:
            return "http://example.org/product-inquiry#"
        
        ns = getattr(self._ontology, "base_iri", "http://example.org/product-inquiry#")
        if not isinstance(ns, str) or not ns:
            ns = "http://example.org/product-inquiry#"
        return ns
    
    @property
    def ontology(self):
        """온톨로지 객체를 반환합니다."""
        return self._ontology
    
    @property
    def namespace(self) -> str:
        """네임스페이스를 반환합니다."""
        return self._namespace or "http://example.org/product-inquiry#"
    
    def is_loaded(self) -> bool:
        """온톨로지가 성공적으로 로딩되었는지 확인합니다."""
        return self._ontology is not None
    
    def execute_sparql(self, query: str) -> List[Tuple]:
        """SPARQL 쿼리를 실행하고 결과를 반환합니다."""
        if not self.is_loaded():
            print("❌ 온톨로지가 로딩되지 않았습니다.")
            return []
        
        try:
            results = list(self._ontology.world.sparql(query))
            return results
        except Exception as e:
            print(f"❌ SPARQL 쿼리 실행 실패: {e}")
            return []
    
    def get_schema_text(self) -> str:
        """온톨로지 스키마 텍스트를 반환합니다 (인스턴스 제외)."""
        temp_path = None
        try:
            # 먼저 S3에서 온톨로지 다운로드 시도
            temp_path = self._download_ontology_from_s3()
            
            if temp_path and os.path.exists(temp_path):
                ontology_path = temp_path
                print(f"📂 S3에서 스키마 텍스트 로딩: {ontology_path}")
            else:
                # S3 다운로드 실패 시 로컬 파일 사용 (fallback)
                print("⚠️ S3 다운로드 실패, 로컬 파일로 스키마 로딩")
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                ontology_path = os.path.join(project_root, "data", "ontology.owl")
            
            # 파일 존재 확인
            if not os.path.exists(ontology_path):
                print(f"❌ 스키마 파일이 존재하지 않습니다: {ontology_path}")
                return ""
            
            with open(ontology_path, "r", encoding="utf-8") as f:
                lines = []
                for line in f:
                    if "<owl:namedindividual" in line.lower():
                        break
                    lines.append(line)
                schema_text = "".join(lines)
                print(f"✅ 스키마 텍스트 로딩 완료: {len(schema_text)} 문자")
                return schema_text
        except Exception as e:
            print(f"❌ 스키마 텍스트 로딩 실패: {e}")
            import traceback
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            return ""
        finally:
            # 임시 파일 정리
            if temp_path and os.path.exists(temp_path):
                try:
                    import time
                    time.sleep(0.1)  # 파일 핸들이 완전히 닫힐 때까지 대기
                    os.unlink(temp_path)
                    print(f"🗑️ 스키마 임시 파일 삭제: {temp_path}")
                except Exception as e:
                    print(f"⚠️ 스키마 임시 파일 삭제 실패: {e}")
    
    def clear_instances(self) -> None:
        """온톨로지의 모든 인스턴스를 제거합니다."""
        if not self.is_loaded():
            print("❌ 온톨로지가 로딩되지 않았습니다.")
            return
        
        try:
            for class_name in ['Variant', 'Option', 'Product', 'Subcategory', 'Category']:
                cls = getattr(self._ontology, class_name, None)
                if cls:
                    for instance in list(cls.instances()):
                        destroy_entity(instance)
            print("✅ 온톨로지 인스턴스 제거 완료")
        except Exception as e:
            print(f"❌ 인스턴스 제거 실패: {e}")
    
    
    def get_all_products(self) -> List[str]:
        """모든 상품명을 반환합니다."""
        if not self.is_loaded():
            return []
        
        try:
            Product = getattr(self._ontology, "Product", None)
            if Product is None:
                return []
            
            products = []
            for prod in Product.instances():
                try:
                    pname = str(prod.productName[0]) if getattr(prod, "productName", []) else ""
                    if pname:
                        products.append(pname)
                except Exception:
                    continue
            return products
        except Exception as e:
            print(f"❌ 상품 목록 조회 실패: {e}")
            return []
    
    def reload_ontology(self) -> bool:
        """온톨로지를 다시 로딩합니다."""
        print("🔄 온톨로지 재로딩 중...")
        self._ontology = None
        self._namespace = None
        self._load_ontology()
        return self.is_loaded()

ontology_manager = OntologyManager()

def get_ontology_manager() -> OntologyManager:
    """온톨로지 매니저 인스턴스를 반환합니다."""
    return ontology_manager