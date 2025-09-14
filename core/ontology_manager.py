"""
온톨로지 관리 모듈
온톨로지 로딩, 캐싱, SPARQL 쿼리 등을 중앙화하여 관리
"""
import os
import boto3
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
    
    def _download_ontology_from_s3(self) -> bool:
        """S3에서 온톨로지 파일을 다운로드합니다."""
        try:
            if not config.is_s3_ready:
                print("❌ S3 설정이 준비되지 않았습니다.")
                return False
            
            # 파일이 이미 존재하고 유효한지 확인
            if os.path.exists(config.LAMBDA_ONTOLOGY_PATH) and os.path.getsize(config.LAMBDA_ONTOLOGY_PATH) > 0:
                print(f"✅ 기존 온톨로지 파일 사용: {config.LAMBDA_ONTOLOGY_PATH}")
                return True
            
            print(f"📥 S3에서 온톨로지 파일 다운로드 시작: s3://{config.S3_BUCKET_NAME}/{config.ONTOLOGY_S3_KEY}")
            
            s3_client = boto3.client('s3', region_name=config.AWS_REGION)
            
            # /tmp 디렉토리가 존재하는지 확인하고 생성
            os.makedirs(os.path.dirname(config.LAMBDA_ONTOLOGY_PATH), exist_ok=True)
            
            s3_client.download_file(
                config.S3_BUCKET_NAME,
                config.ONTOLOGY_S3_KEY,
                config.LAMBDA_ONTOLOGY_PATH
            )
            
            # 파일이 정상적으로 다운로드되었는지 확인
            if os.path.exists(config.LAMBDA_ONTOLOGY_PATH):
                file_size = os.path.getsize(config.LAMBDA_ONTOLOGY_PATH)
                print(f"✅ S3에서 온톨로지 파일 다운로드 완료: {config.LAMBDA_ONTOLOGY_PATH} ({file_size:,} bytes)")
                return True
            else:
                print(f"❌ 다운로드된 파일이 존재하지 않습니다: {config.LAMBDA_ONTOLOGY_PATH}")
                return False
                
        except Exception as e:
            print(f"❌ S3에서 온톨로지 파일 다운로드 실패: {e}")
            return False
    
    def _load_ontology(self) -> None:
        """온톨로지를 로딩하고 추론기를 동기화합니다."""
        try:
            # S3에서 온톨로지 파일 다운로드 (Lambda 환경 전용)
            if not self._download_ontology_from_s3():
                print("❌ S3에서 온톨로지 파일 다운로드 실패 - Lambda 환경에서는 S3 연결이 필수입니다.")
                self._ontology = None
                self._namespace = None
                return
            
            # S3에서 다운로드 성공한 경우
            ontology_path = config.LAMBDA_ONTOLOGY_PATH
            
            print(f"📂 온톨로지 파일 로딩 중: {ontology_path}")
            print(f"📋 파일 크기: {os.path.getsize(ontology_path):,} bytes")
            
            # 파일 존재 및 가독성 재확인
            if not os.path.exists(ontology_path):
                print(f"❌ 온톨로지 파일이 존재하지 않습니다: {ontology_path}")
                return
            
            if not os.access(ontology_path, os.R_OK):
                print(f"❌ 온톨로지 파일에 읽기 권한이 없습니다: {ontology_path}")
                return
            
            print(f"📖 온톨로지 파일 읽기 시작: {ontology_path}")
            
            print("📊 온톨로지 파일 내용 로딩 중...")
            # 절대 경로로 변환
            abs_path = os.path.abspath(ontology_path)
            print(f"🔍 절대 경로: {abs_path}")
            
            # 로딩 직전 파일 상태 재확인
            if not os.path.exists(abs_path):
                print(f"❌ 절대 경로 파일이 존재하지 않음: {abs_path}")
                return
            
            file_size = os.path.getsize(abs_path)
            print(f"📏 로딩 직전 파일 크기: {file_size:,} bytes")
            
            # Lambda 환경을 위한 owlready2 설정 및 디버깅
            import owlready2
            import tempfile
            
            try:
                version = getattr(owlready2, '__version__', 'unknown')
                if version == 'unknown':
                    version = getattr(owlready2, 'VERSION', 'unknown')
                print(f"🔧 owlready2 버전: {version}")
            except Exception:
                print("🔧 owlready2 버전: 확인불가 (정상동작)")
            
            # Lambda 환경 최적화 설정
            print("🔧 Lambda 환경 최적화 설정 중...")
            
            # owlready2 완전 초기화
            try:
                owlready2.default_world.close()
                print("🔄 owlready2 world 닫기 완료")
            except:
                pass
            
            # onto_path 설정
            print(f"🗂️ 기본 onto_path: {owlready2.onto_path}")
            owlready2.onto_path.clear()
            owlready2.onto_path.append("/tmp")
            print(f"📁 onto_path 설정: {owlready2.onto_path}")
            
            # tempfile 설정
            tempfile.tempdir = "/tmp"
            
            # owlready2 백엔드를 메모리 모드로 설정
            try:
                # 새로운 world 생성
                owlready2.default_world = owlready2.World()
                owlready2.default_world.set_backend(filename=":memory:")
                print("💾 owlready2 백엔드를 메모리 모드로 설정")
            except Exception as e:
                print(f"⚠️ 메모리 백엔드 설정 실패: {e}")
                # 메모리 백엔드 실패 시 /tmp에 SQLite 파일 생성
                try:
                    sqlite_path = "/tmp/ontology.db"
                    owlready2.default_world.set_backend(filename=sqlite_path)
                    print(f"💾 SQLite 백엔드 설정: {sqlite_path}")
                except Exception as e2:
                    print(f"⚠️ SQLite 백엔드 설정도 실패: {e2}")
            
            # 환경 변수 설정
            import os
            os.environ['OWLREADY2_TMP'] = '/tmp'
            os.environ['TMPDIR'] = '/tmp'
            os.environ['TMP'] = '/tmp'
            os.environ['TEMP'] = '/tmp'
            
            # /tmp 디렉토리 여유 공간 확인
            import shutil
            free_space = shutil.disk_usage("/tmp").free
            print(f"💽 /tmp 디렉토리 여유 공간: {free_space / (1024*1024):.1f} MB")
            
            # 파일 상태 상세 정보
            import stat
            file_stat = os.stat(abs_path)
            print(f"📊 파일 상태:")
            print(f"  - 크기: {file_stat.st_size:,} bytes")
            print(f"  - 모드: {oct(file_stat.st_mode)}")
            print(f"  - 수정 시간: {file_stat.st_mtime}")
            print(f"  - 접근 시간: {file_stat.st_atime}")
            
            # 상대 경로로만 로딩 시도
            loading_methods = [
                ("상대 경로", ontology_path)
            ]
            
            for method_name, path_to_try in loading_methods:
                try:
                    print(f"🔄 {method_name}으로 로딩 시도: {path_to_try}")
                    
                    # 파일 존재 확인
                    if not os.path.exists(path_to_try):
                        print(f"⚠️ 파일이 존재하지 않음: {path_to_try}")
                        continue
                    
                    # owlready2 로딩 시도
                    onto = get_ontology(path_to_try)
                    print(f"✅ 온톨로지 객체 생성 성공: {onto}")
                    
                    # 온톨로지 객체 상세 정보
                    print(f"🔍 온톨로지 객체 상세 정보:")
                    print(f"  - base_iri: {onto.base_iri}")
                    print(f"  - name: {onto.name}")
                    
                    # 파일 읽기 테스트
                    try:
                        with open(path_to_try, 'r') as f:
                            first_line = f.readline().strip()
                            print(f"📄 파일 첫 줄: {first_line[:100]}...")
                    except Exception as read_error:
                        print(f"⚠️ 파일 읽기 테스트 실패: {read_error}")
                    
                    # 실제 로딩 - 여러 방법 시도
                    print("🔄 실제 로딩 시도 중...")
                    
                    # 방법 1: 기본 load() 시도
                    try:
                        self._ontology = onto.load()
                        print(f"✅ 온톨로지 로딩 성공 ({method_name}) - 기본 방법")
                        break
                    except Exception as load_detail_error:
                        print(f"❌ 기본 onto.load() 실패: {load_detail_error}")
                        
                        # 방법 2: reload=True 옵션으로 시도
                        try:
                            print("🔄 reload=True 옵션으로 재시도...")
                            self._ontology = onto.load(reload=True)
                            print(f"✅ 온톨로지 로딩 성공 ({method_name}) - reload=True")
                            break
                        except Exception as reload_error:
                            print(f"❌ reload=True 방법도 실패: {reload_error}")
                            
                            # 방법 3: 파일을 직접 읽어서 로딩
                            try:
                                print("🔄 파일 직접 읽기 방법으로 시도...")
                                with open(path_to_try, 'rb') as f:
                                    content = f.read()
                                print(f"📄 파일 내용 읽기 완료: {len(content)} bytes")
                                
                                # 임시 파일로 저장 후 로딩
                                temp_file = "/tmp/temp_ontology.owl"
                                with open(temp_file, 'wb') as f:
                                    f.write(content)
                                
                                temp_onto = get_ontology(temp_file)
                                self._ontology = temp_onto.load()
                                print(f"✅ 온톨로지 로딩 성공 ({method_name}) - 임시 파일 방법")
                                break
                                
                            except Exception as temp_error:
                                print(f"❌ 임시 파일 방법도 실패: {temp_error}")
                                
                                # 모든 방법 실패 시 상세 오류 출력
                                print(f"❌ 모든 로딩 방법 실패!")
                                print(f"❌ 오류 타입: {type(load_detail_error).__name__}")
                                import traceback
                                print(f"❌ 상세 스택 트레이스: {traceback.format_exc()}")
                                
                                # owlready2 내부 상태 재확인
                                print(f"🔍 로딩 실패 시 owlready2 상태:")
                                print(f"  - onto_path: {owlready2.onto_path}")
                                print(f"  - default_world: {owlready2.default_world}")
                                print(f"  - onto.base_iri: {onto.base_iri}")
                                
                                # 파일 시스템 상태 확인
                                print(f"🔍 파일 시스템 상태:")
                                print(f"  - 파일 존재: {os.path.exists(path_to_try)}")
                                print(f"  - 파일 크기: {os.path.getsize(path_to_try) if os.path.exists(path_to_try) else 'N/A'}")
                                print(f"  - 읽기 권한: {os.access(path_to_try, os.R_OK) if os.path.exists(path_to_try) else 'N/A'}")
                                
                                raise load_detail_error
                    
                except Exception as load_error:
                    print(f"❌ {method_name} 로딩 실패: {load_error}")
                    continue
            
            # 모든 방법이 실패한 경우
            if self._ontology is None:
                print("❌ 모든 로딩 방법 실패")
                return
            
            print("🔧 추론기 동기화 중...")
            try:
                with self._ontology:
                    # Lambda 환경에서 추론기가 실패할 수 있으므로 try-catch로 감싸기
                    sync_reasoner()
                print("✅ 추론기 동기화 완료")
            except Exception as reasoner_error:
                print(f"⚠️ 추론기 동기화 실패 (Lambda 환경에서는 정상적 현상일 수 있음): {reasoner_error}")
                # 추론기 실패해도 온톨로지 자체는 사용 가능하므로 계속 진행
            
            self._namespace = self._get_namespace()
            print("✅ 온톨로지 로딩 완료")
            
        except FileNotFoundError as e:
            print(f"❌ 온톨로지 파일을 찾을 수 없습니다: {e}")
            print(f"❌ 현재 작업 디렉토리: {os.getcwd()}")
            print(f"❌ /tmp 디렉토리 내용: {os.listdir('/tmp') if os.path.exists('/tmp') else '존재하지 않음'}")
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
        if self._ontology is None:
            print("🔄 온톨로지가 로딩되지 않음 - 재시도 중...")
            self._load_ontology()
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
        try:
            # Lambda 환경에서 다운로드된 온톨로지 파일 사용
            ontology_path = config.LAMBDA_ONTOLOGY_PATH
            
            # 파일 존재 확인
            if not os.path.exists(ontology_path):
                print(f"❌ 스키마 파일이 존재하지 않습니다: {ontology_path}")
                print("❌ S3에서 온톨로지 파일을 먼저 다운로드해야 합니다.")
                return ""
            
            print(f"📂 스키마 텍스트 로딩: {ontology_path}")
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
        # S3에서 최신 파일을 다시 다운로드하고 로딩
        self._load_ontology()
        return self.is_loaded()

ontology_manager = OntologyManager()

def get_ontology_manager() -> OntologyManager:
    """온톨로지 매니저 인스턴스를 반환합니다."""
    return ontology_manager