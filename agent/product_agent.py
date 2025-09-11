from pydantic import BaseModel
import json
import dspy
from core.ontology_manager import get_ontology_manager

def find_product_colors(product_name: str) -> str:
    """특정 상품의 모든 색상 옵션을 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not product_name:
        return "온톨로지 로딩 실패 또는 제품명 없음"
    
    ns = ontology_manager.namespace
    query = (
        f"PREFIX : <{ns}>\n"
        "SELECT DISTINCT ?optionValue WHERE {\n"
        "  ?option a :Option ;\n"
        "          :optionName \"색상\" ;\n"
        "          :optionValue ?optionValue .\n"
        f"  FILTER(CONTAINS(str(?option), \"{product_name}\"))\n"
        "}"
    )
    
    try:
        results = ontology_manager.execute_sparql(query)
        if not results:
            return f"'{product_name}' 상품의 색상 정보를 찾을 수 없습니다."
        
        colors = set()
        for row in results:
            if row:
                option_value = str(row[0])
                color_list = option_value.split(",")
                for color in color_list:
                    color = color.strip()
                    if color:
                        colors.add(color)
        
        if not colors:
            return f"'{product_name}' 상품의 색상 정보를 찾을 수 없습니다."
        
        return f"'{product_name}' 상품의 색상 옵션: {', '.join(sorted(colors))}"
    except Exception as e:
        return f"색상 검색 중 오류 발생: {e}"

def find_product_sizes(product_name: str) -> str:
    """특정 상품의 모든 사이즈 옵션을 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not product_name:
        return "온톨로지 로딩 실패 또는 제품명 없음"
    
    ns = ontology_manager.namespace
    query = (
        f"PREFIX : <{ns}>\n"
        "SELECT DISTINCT ?optionValue WHERE {\n"
        "  ?option a :Option ;\n"
        "          :optionName \"사이즈\" ;\n"
        "          :optionValue ?optionValue .\n"
        f"  FILTER(CONTAINS(str(?option), \"{product_name}\"))\n"
        "}"
    )
    
    try:
        results = ontology_manager.execute_sparql(query)
        if not results:
            return f"'{product_name}' 상품의 사이즈 정보를 찾을 수 없습니다."
        
        sizes = set()
        for row in results:
            if row:
                option_value = str(row[0])
                size_list = option_value.split(",")
                for size in size_list:
                    size = size.strip()
                    if size:
                        sizes.add(size)
        
        if not sizes:
            return f"'{product_name}' 상품의 사이즈 정보를 찾을 수 없습니다."
        
        return f"'{product_name}' 상품의 사이즈 옵션: {', '.join(sorted(sizes))}"
    except Exception as e:
        return f"사이즈 검색 중 오류 발생: {e}"

def find_product_price(product_name: str) -> str:
    """특정 상품의 가격 정보를 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not product_name:
        return "온톨로지 로딩 실패 또는 제품명 없음"
    
    ns = ontology_manager.namespace
    query = (
        f"PREFIX : <{ns}>\n"
        "SELECT ?price WHERE {\n"
        "  ?product a :Product ;\n"
        f"           :productName \"{product_name}\" ;\n"
        "           :productBasePrice ?price .\n"
        "}"
    )
    
    try:
        results = ontology_manager.execute_sparql(query)
        if not results:
            return f"'{product_name}' 상품의 가격 정보를 찾을 수 없습니다."
        price = int(results[0][0])
        return f"'{product_name}' 상품의 가격: {price:,}원"
    except Exception as e:
        return f"가격 검색 중 오류 발생: {e}"

def find_product_types(product_name: str) -> str:
    """특정 상품의 모든 타입 옵션을 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not product_name:
        return "온톨로지 로딩 실패 또는 제품명 없음"
    
    ns = ontology_manager.namespace
    query = (
        f"PREFIX : <{ns}>\n"
        "SELECT DISTINCT ?optionValue WHERE {\n"
        "  ?option a :Option ;\n"
        "          :optionName \"타입\" ;\n"
        "          :optionValue ?optionValue .\n"
        f"  FILTER(CONTAINS(str(?option), \"{product_name}\"))\n"
        "}"
    )
    
    try:
        results = ontology_manager.execute_sparql(query)
        if not results:
            return f"'{product_name}' 상품의 타입 정보를 찾을 수 없습니다."
        
        types = set()
        for row in results:
            if row:
                option_value = str(row[0])
                type_list = option_value.split(",")
                for type_option in type_list:
                    type_option = type_option.strip()
                    if type_option:
                        types.add(type_option)
        
        if not types:
            return f"'{product_name}' 상품의 타입 정보를 찾을 수 없습니다."
        
        return f"'{product_name}' 상품의 타입 옵션: {', '.join(sorted(types))}"
    except Exception as e:
        return f"타입 검색 중 오류 발생: {e}"

def find_product_sale_status(product_name: str) -> str:
    """특정 상품의 판매 상태 정보를 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not product_name:
        return "온톨로지 로딩 실패 또는 제품명 없음"
    
    ns = ontology_manager.namespace
    query = (
        f"PREFIX : <{ns}>\n"
        "SELECT ?combinationLabel ?saleStatus WHERE {\n"
        "  ?product a :Product ;\n"
        f"           :productName \"{product_name}\" ;\n"
        "           :hasVariant ?variant .\n"
        "  ?variant :combinationLabel ?combinationLabel ;\n"
        "           :saleStatus ?saleStatus .\n"
        "}"
    )
    
    try:
        results = ontology_manager.execute_sparql(query)
        if not results:
            return f"'{product_name}' 상품의 판매 상태 정보를 찾을 수 없습니다."
        
        status_groups = {}
        for row in results:
            if len(row) >= 2:
                combo = str(row[0])
                status = str(row[1])
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(combo)
        
        if status_groups:
            result = f"'{product_name}' 상품의 판매 상태:\n"
            
            status_summary = []
            for status, combos in status_groups.items():
                if status == "판매":
                    status_summary.append(f"✅ 판매중: {len(combos)}개 옵션")
                elif status == "품절":
                    status_summary.append(f"❌ 품절: {len(combos)}개 옵션")
                elif status == "일시품절":
                    status_summary.append(f"⏸️ 일시품절: {len(combos)}개 옵션")
                elif status == "노출안함":
                    status_summary.append(f"🔒 노출안함: {len(combos)}개 옵션")
                else:
                    status_summary.append(f"❓ {status}: {len(combos)}개 옵션")
            
            result += "\n".join(status_summary)
            
            if "판매" in status_groups:
                result += f"\n\n📋 판매중인 옵션:\n"
                for combo in status_groups["판매"]:
                    result += f"  • {combo}\n"
            
            return result
        else:
            return f"'{product_name}' 상품의 판매 상태 정보를 찾을 수 없습니다."
    
    except Exception as e:
        return f"판매 상태 검색 중 오류 발생: {e}"

def find_product_stock(product_name: str) -> str:
    """특정 상품의 재고 정보를 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not product_name:
        return "온톨로지 로딩 실패 또는 제품명 없음"
    
    ns = ontology_manager.namespace
    query = (
        f"PREFIX : <{ns}>\n"
        "SELECT ?combinationLabel ?stockQuantity WHERE {\n"
        "  ?product a :Product ;\n"
        f"           :productName \"{product_name}\" ;\n"
        "           :hasVariant ?variant .\n"
        "  ?variant :combinationLabel ?combinationLabel ;\n"
        "           :stockQuantity ?stockQuantity .\n"
        "}"
    )
    
    try:
        results = ontology_manager.execute_sparql(query)
        if not results:
            return f"'{product_name}' 상품의 재고 정보를 찾을 수 없습니다."
        
        stock_info = []
        total_stock = 0
        for row in results:
            if len(row) >= 2:
                combo = str(row[0])
                stock = int(row[1])
                stock_info.append(f"  {combo}: {stock:,}개")
                total_stock += stock
        
        if stock_info:
            result = f"'{product_name}' 상품의 재고 현황:\n"
            result += "\n".join(stock_info)
            result += f"\n\n총 재고: {total_stock:,}개"
            return result
        else:
            return f"'{product_name}' 상품의 재고 정보를 찾을 수 없습니다."
    
    except Exception as e:
        return f"재고 검색 중 오류 발생: {e}"

def find_variant_prices(product_name: str) -> str:
    """특정 상품의 옵션별 가격 정보를 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not product_name:
        return "온톨로지 로딩 실패 또는 제품명 없음"
    
    ns = ontology_manager.namespace
    query = (
        f"PREFIX : <{ns}>\n"
        "SELECT ?combinationLabel ?variantPrice ?basePrice WHERE {\n"
        "  ?product a :Product ;\n"
        f"           :productName \"{product_name}\" ;\n"
        "           :productBasePrice ?basePrice ;\n"
        "           :hasVariant ?variant .\n"
        "  ?variant :combinationLabel ?combinationLabel ;\n"
        "           :variantPrice ?variantPrice .\n"
        "}"
    )
    
    try:
        results = ontology_manager.execute_sparql(query)
        if not results:
            return f"'{product_name}' 상품의 옵션별 가격 정보를 찾을 수 없습니다."
        
        base_price = int(results[0][2]) if results else 0
        price_info = []
        
        for row in results:
            if len(row) >= 3:
                combo = str(row[0])
                variant_price = int(row[1])
                final_price = base_price + variant_price
                
                if variant_price == 0:
                    price_info.append(f"{combo}: {final_price:,}원")
                else:
                    price_info.append(f"{combo}: {final_price:,}원 (기본가 + {variant_price:,}원)")
        
        if price_info:
            result = f"'{product_name}' 상품의 옵션별 가격:\n"
            result += f"기본 가격: {base_price:,}원\n"
            result += "\n".join(price_info)
            return result
        else:
            return f"'{product_name}' 상품의 옵션별 가격 정보를 찾을 수 없습니다."
    
    except Exception as e:
        return f"옵션별 가격 검색 중 오류 발생: {e}"

def search_products_by_keyword(keyword: str) -> str:
    """키워드로 상품을 검색합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not keyword:
        return "온톨로지 로딩 실패 또는 키워드 없음"
    
    try:
        Product = getattr(ontology_manager.ontology, "Product", None)
        if Product is None:
            return "Product 클래스를 찾을 수 없습니다."
        
        matching_products = []
        for prod in list(Product.instances()):
            try:
                pname = str(prod.productName[0]) if getattr(prod, "productName", []) else ""
                if keyword.lower() in pname.lower():
                    matching_products.append(pname)
            except Exception:
                continue
        
        if not matching_products:
            return f"'{keyword}' 키워드와 일치하는 상품을 찾을 수 없습니다."
        
        return f"'{keyword}' 검색 결과: {', '.join(matching_products)}"
    except Exception as e:
        return f"상품 검색 중 오류 발생: {e}"

def find_product_by_partial_name(partial_name: str) -> str:
    """부분 상품명으로 정확한 상품을 찾아 반환합니다."""
    ontology_manager = get_ontology_manager()
    if not ontology_manager.is_loaded() or not partial_name:
        return "온톨로지 로딩 실패 또는 상품명 없음"
    
    try:
        Product = getattr(ontology_manager.ontology, "Product", None)
        if Product is None:
            return "Product 클래스를 찾을 수 없습니다."
        
        keywords = [keyword.strip().lower() for keyword in partial_name.split() if len(keyword.strip()) > 1]
        
        if not keywords:
            return "검색할 키워드가 없습니다."
        
        exact_matches = []
        high_matches = []
        partial_matches = []
        
        for prod in list(Product.instances()):
            try:
                pname = str(prod.productName[0]) if getattr(prod, "productName", []) else ""
                if not pname:
                    continue
                
                pname_lower = pname.lower()
                
                if partial_name.lower() == pname_lower:
                    exact_matches.append(pname)
                    continue
                
                if partial_name.lower() in pname_lower:
                    high_matches.append(pname)
                    continue
                
                all_keywords_found = True
                for keyword in keywords:
                    if keyword not in pname_lower:
                        all_keywords_found = False
                        break
                
                if all_keywords_found:
                    partial_matches.append(pname)
            
            except Exception:
                continue
        
        if not exact_matches and not high_matches and not partial_matches:
            return f"'{partial_name}'에 해당하는 상품을 찾을 수 없습니다."
        
        result = f"'{partial_name}'으로 찾은 상품:\n"
        
        if exact_matches:
            result += f"\n🎯 정확한 상품명:\n"
            for product in exact_matches:
                result += f"  • {product}\n"
        
        if high_matches:
            if len(high_matches) == 1:
                result += f"\n✅ 찾으신 상품:\n"
                result += f"  • {high_matches[0]}\n"
            else:
                result += f"\n✅ 가능한 상품들 ({len(high_matches)}개):\n"
                for product in high_matches:
                    result += f"  • {product}\n"
        
        if partial_matches and len(high_matches) < 3:
            result += f"\n💡 관련 상품들 ({len(partial_matches)}개):\n"
            for product in partial_matches:
                result += f"  • {product}\n"
        
        if high_matches and len(high_matches) == 1:
            result += f"\n💬 '{high_matches[0]}'을(를) 찾으신 것 같습니다!"
        elif exact_matches and len(exact_matches) == 1:
            result += f"\n💬 정확히 '{exact_matches[0]}'입니다!"
        
        return result
        
    except Exception as e:
        return f"상품 검색 중 오류 발생: {e}"

class ProductQueryAgent(dspy.Signature):
    """당신은 상품 정보를 조회하는 도우미입니다. 사용자의 요청에 따라 적절한 도구를 선택하여 상품의 색상, 사이즈, 타입, 가격, 재고, 옵션별 가격, 판매 상태 정보를 제공하거나 상품을 검색하고, 부분 상품명으로 정확한 상품을 찾을 수 있습니다."""

    user_request: str = dspy.InputField()
    query_result: str = dspy.OutputField(
        desc="사용자 요청에 대한 답변 결과"
    )

agent = dspy.ReAct(
    ProductQueryAgent,
    tools=[
        find_product_colors,
        find_product_sizes,
        find_product_types,
        find_product_price,
        find_product_sale_status,
        find_product_stock,
        find_variant_prices,
        search_products_by_keyword,
        find_product_by_partial_name,
    ]
)

def run_product_agent(user_request: str):
    try:
        prediction = agent(user_request=user_request)
        query_result = getattr(prediction, "query_result", None)
        if query_result:
            print("\n[Query Result]")
            print(query_result)

        def _serialize(obj):
            if isinstance(obj, BaseModel):
                try:
                    return obj.model_dump()
                except Exception:
                    try:
                        return obj.dict()
                    except Exception:
                        return str(obj)
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple, set)):
                return [_serialize(v) for v in obj]
            return obj

        def _indent(text: str, spaces: int = 2) -> str:
            prefix = " " * spaces
            return "\n".join(prefix + line for line in str(text).splitlines())

        trajectory = getattr(prediction, "trajectory", None)
        if isinstance(trajectory, dict) and trajectory:
            print("\n[Reasoning & Tool Calls]")

            indices = sorted({
                int(k.rsplit("_", 1)[1])
                for k in trajectory.keys()
                if "_" in k and k.rsplit("_", 1)[1].isdigit()
            })

            for idx in indices:
                thought = trajectory.get(f"thought_{idx}")
                tool_name = trajectory.get(f"tool_name_{idx}")
                tool_args = trajectory.get(f"tool_args_{idx}")
                observation = trajectory.get(f"observation_{idx}")

                print(f"- Step {idx + 1}")
                if thought:
                    print(_indent(f"Thought: {thought}", 2))
                if tool_name:
                    print(_indent(f"Tool: {tool_name}", 2))
                if tool_args is not None:
                    try:
                        args_str = json.dumps(_serialize(tool_args), ensure_ascii=False, indent=2)
                    except Exception:
                        args_str = str(tool_args)
                    print(_indent("Args:", 2))
                    print(_indent(args_str, 4))
                if observation is not None:
                    try:
                        obs_str = json.dumps(_serialize(observation), ensure_ascii=False, indent=2)
                    except Exception:
                        obs_str = str(observation)
                    print(_indent("Observation:", 2))
                    print(_indent(obs_str, 4))

        return prediction
    except Exception as e:
        print(f"ERROR: {e}")
        return None