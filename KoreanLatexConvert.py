import re
import xml.etree.ElementTree as ET
import os

class KoreanLatexConverter:
    def __init__(self):
        # 한글 수식과 Latex 간의 기본 매핑 정의
        self.korean_to_latex = {
            "TIMES": r"\\times",
            "LEFT": r"\\left",
            "RIGHT": r"\\right",
            "SMALLINTER": r"\\cap",
            "C": r"{\\mathrm C}",
            "rm P": r"\\mathrm { P }",
            "rm": r"",
            "it": r"",  # 이탤릭체 표현을 위한 매핑
        }

        # 역방향 매핑 생성 (Latex -> 한글)
        self.latex_to_korean = {}
        for k, v in self.korean_to_latex.items():
            if v:  # 빈 문자열이 아닌 경우만 매핑
                self.latex_to_korean[v] = k

    def parse_hml_file(self, file_path):
        """HML 파일에서 수식 추출"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 네임스페이스를 동적으로 찾기
            namespaces = {}
            for prefix, uri in root.nsmap.items() if hasattr(root, 'nsmap') else []:
                namespaces[prefix] = uri
            
            result = []
            
            # 네임스페이스 관계없이 모든 'equation' 요소 찾기 시도
            equations = []
            
            # 방법 1: 네임스페이스 없이 직접 검색
            equations = root.findall('.//equation')
            
            # 방법 2: 모든 가능한 네임스페이스 조합 시도
            if not equations:
                for ns_prefix in namespaces:
                    try:
                        equations = root.findall(f'.//{{{namespaces[ns_prefix]}}}equation')
                        if equations:
                            break
                    except:
                        continue
            
            # 방법 3: XPath 사용해서 모든 요소에서 'type' 속성이 'equation'인 요소 찾기
            if not equations:
                equations = root.xpath('.//*[@type="equation"]') if hasattr(root, 'xpath') else []
            
            # 모든 방법이 실패하면 모든 텍스트 노드를 확인하여 수식 형태 찾기
            if not equations:
                print("Not find the formula. Search for text directly")
                # 모든 텍스트 노드 검색 (간단한 재귀 함수)
                def find_all_text(element):
                    texts = []
                    if element.text and element.text.strip():
                        texts.append(element.text)
                    for child in element:
                        texts.extend(find_all_text(child))
                    return texts
                
                all_texts = find_all_text(root)
                
                # 수식 패턴이 있는지 확인 (예: { } over { } 패턴)
                for text in all_texts:
                    if re.search(r'\{[^{}]*\}\s*over\s*\{[^{}]*\}', text):
                        result.append(text)
            else:
                # 찾은 equation 요소에서 텍스트 추출
                for eq in equations:
                    if hasattr(eq, 'text') and eq.text:
                        result.append(eq.text)
                    # 자식 요소의 텍스트도 확인
                    for child in eq.findall('.//*'):
                        if hasattr(child, 'text') and child.text:
                            result.append(child.text)
            
            return result
        except Exception as e:
            print(f"Error parsing HML file: {str(e)}")
            # 파일을 텍스트로 직접 읽어서 정규표현식으로 수식 패턴 찾기
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 수식 패턴 찾기 (예: 'equation' 태그 사이)
                equation_matches = re.findall(r'<equation[^>]*>(.*?)</equation>', content, re.DOTALL)
                if equation_matches:
                    return equation_matches
                
                # 다른 패턴도 시도 (예: { } over { } 패턴)
                formula_matches = re.findall(r'\{[^{}]*\}\s*over\s*\{[^{}]*\}', content)
                if formula_matches:
                    return formula_matches
            except Exception as e2:
                print(f"Error attempting text based parsing: {str(e2)}")
            
            return []

    def korean_to_latex_convert(self, korean_expr):
        """한글 수식을 LaTeX로 변환"""
        try:
            if not isinstance(korean_expr, str):
                print(f"Not a string: {type(korean_expr)}")
                return str(korean_expr)  # 문자열로 변환 시도
                
            # 분수 변환을 위한 재귀 함수
            def process_fraction(expr):
                # 기본 케이스: over가 없으면 종료
                if "over" not in expr:
                    return expr
                    
                # {A} over {B} 패턴 찾기
                stack = []
                i = 0
                start_positions = []
                
                # 균형 잡힌 괄호 찾기
                while i < len(expr):
                    if expr[i] == '{':
                        if not stack:  # 첫 번째 여는 괄호면 위치 기록
                            start_positions.append(i)
                        stack.append(i)
                    elif expr[i] == '}':
                        if stack:
                            stack.pop()
                            if not stack and i+1 < len(expr) and "over" in expr[i+1:i+10]:
                                # 첫 번째 중괄호 쌍 뒤에 over가 있으면
                                first_open = start_positions.pop()
                                first_close = i
                                
                                # over 위치 찾기
                                over_pos = expr[first_close+1:].find("over") + first_close + 1
                                if over_pos >= first_close + 1:
                                    # over 뒤에 나오는 두 번째 중괄호 쌍 찾기
                                    second_start = expr[over_pos+4:].find("{") + over_pos + 4
                                    if second_start >= over_pos + 4:
                                        # 두 번째 중괄호의 닫는 괄호 찾기
                                        stack2 = []
                                        j = second_start
                                        while j < len(expr):
                                            if expr[j] == '{':
                                                stack2.append(j)
                                            elif expr[j] == '}':
                                                stack2.pop()
                                                if not stack2:  # 균형 잡힌 괄호 찾음
                                                    second_close = j
                                                    
                                                    # 분자와 분모 추출
                                                    numerator = expr[first_open+1:first_close]
                                                    denominator = expr[second_start+1:second_close]
                                                    
                                                    # 분자와 분모 재귀적으로 처리
                                                    processed_num = process_fraction(numerator)
                                                    processed_denom = process_fraction(denominator)
                                                    
                                                    # 결과 조합
                                                    before = expr[:first_open]
                                                    after = expr[second_close+1:]
                                                    result = f"{before}\\dfrac{{ {processed_num} }} {{ {processed_denom} }}{after}"
                                                    
                                                    # 변환된 결과에 대해 다시 처리 (중첩된 over 처리)
                                                    return process_fraction(result)
                                            j += 1
                    i += 1
                    
                # over가 발견되지 않았거나 처리할 수 없는 패턴
                return expr
            
            # 분수 패턴 처리
            processed_expr = process_fraction(korean_expr)
            
            # 수식 내 공백 처리 (나중에 처리하기 위해 임시로 미루기)
            if isinstance(processed_expr, str):
                # 먼저 B ^{C} 패턴을 보존하기 위한 처리
                # 수퍼스크립트 패턴 찾기 및 임시 마커로 대체
                superscript_pattern = r'\^{([A-Za-z])}'
                superscript_matches = re.findall(superscript_pattern, processed_expr)
                
                # 임시 마커로 대체하여 보존
                for i, match in enumerate(superscript_matches):
                    marker = f"__SUPERSCRIPT_{i}__"
                    processed_expr = processed_expr.replace(f"^{{{match}}}", marker)
                
                # 나머지 키워드 변환 (C 포함)
                for k, v in self.korean_to_latex.items():
                    if k != "over":  # over는 이미 처리함
                        # 에러 방지를 위한 타입 확인
                        if isinstance(processed_expr, str):
                            processed_expr = re.sub(r'\b' + re.escape(k) + r'\b', v, processed_expr)
                
                # 임시 마커를 원래 수퍼스크립트로 복원
                for i, match in enumerate(superscript_matches):
                    marker = f"__SUPERSCRIPT_{i}__"
                    processed_expr = processed_expr.replace(marker, f"^{{{match}}}")
                
                # C 연산자 주변 처리 (조합 연산자로 사용될 때만)
                processed_expr = re.sub(r'(\d+)\s*\\mathrm\s*C\s*(\d+)', r'\1 {\\mathrm C} \2', processed_expr)                            
                # 수식 내 공백 처리
                processed_expr = re.sub(r'\s+', ' ', processed_expr)
                
            return processed_expr
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error during conversion from Hangul to Latex : {str(e)}")
            return str(korean_expr)  # 안전하게 문자열로 반환
    
    def latex_to_korean_convert(self, latex_expr):
        """LaTeX 수식을 한글 수식으로 변환"""
        try:
            result = latex_expr
            
            # 중첩된 분수, 조합 기호, 서브스크립트 처리를 위해 먼저 일부 특수 패턴 보존
            # 임시 마커로 중요 패턴 대체
            temp_markers = {}
            
            # { } _ { n } {\mathrm C} _ { m } 패턴 찾아서 임시 보존
            combination_pattern = r'(?:\{\s*\})?\s*_\s*\{\s*(\d+)\s*\}\s*\{\\mathrm\s+C\}\s*_\s*\{\s*(\d+)\s*\}'
            comb_matches = re.finditer(combination_pattern, result)
            for i, match in enumerate(comb_matches):
                marker = f"__COMB_{i}__"
                # match.group(0)에서 맨 앞에 빈 중괄호가 있는지 확인 (선택적 그룹이므로 non-capturing)
                if re.match(r'^\{\s*\}', match.group(0)):
                    replacement = f"{{}}_{{{match.group(1)}}} C _{{{match.group(2)}}}"
                else:
                    replacement = f" _{{{match.group(1)}}} C _{{{match.group(2)}}}"
                temp_markers[marker] = replacement
                result = result.replace(match.group(0), marker)
            
            # 1. \dfrac 패턴을 {a} over {b}로 변환
            dfrac_pattern = r'\\dfrac\s*\{\s*(.*?)\s*\}\s*\{\s*(.*?)\s*\}'
            
            # 중첩된 dfrac 패턴을 처리하기 위해 여러 번 반복
            while re.search(dfrac_pattern, result):
                # 가장 안쪽의 \dfrac부터 변환
                match = re.search(dfrac_pattern, result)
                if not match:
                    break
                    
                num, denom = match.groups()
                replacement = f"{{{num}}} over {{{denom}}}"
                result = result[:match.start()] + replacement + result[match.end():]
            
            # 2. 서브스크립트 처리 (_{n} 패턴)
            # 서브스크립트 패턴을 일관되게 처리
            subscript_pattern = r'_\s*\{\s*(\d+)\s*\}'
            result = re.sub(subscript_pattern, r'_{\1}', result)
            
            # 임시 마커 복원
            for marker, original in temp_markers.items():
                result = result.replace(marker, original)
            
            # 3. {\mathrm C} 패턴을 C로 변환
            result = re.sub(r'\{\\mathrm\s+C\}', r'C', result)
            
            # 4. 기타 LaTeX 심볼을 한글로 변환
            for latex_pattern, korean_symbol in sorted(self.latex_to_korean.items(), key=lambda x: len(x[0]), reverse=True):
                if latex_pattern and latex_pattern != r"\mathrm":  # mathrm은 별도 처리
                    # 정규식 특수 문자 이스케이프 처리
                    escaped_pattern = re.escape(latex_pattern)
                    # 패턴이 있는지 확인 후 교체
                    if re.search(escaped_pattern, result):
                        result = re.sub(escaped_pattern, korean_symbol, result)
            
            # 5. 표기법 정리
            # 중괄호 안의 공백 제거
            result = re.sub(r'\{\s+(\d+)\s+\}', r'{\1}', result)
            
            # 남은 \left, \right 등 처리
            left_right_patterns = [
                (r'\\left\s*\(', r'LEFT ('),
                (r'\\right\s*\)', r'RIGHT )'),
                (r'\\cap', r'SMALLINTER'),
                (r'\\times', r'TIMES'),
            ]
            
            for pattern, replacement in left_right_patterns:
                result = re.sub(pattern, replacement, result)
            
            # 6. 조합 표기 수정 (n C m 패턴)
            # {}_{n} C_{m} 패턴 처리
            # result = re.sub(r'\{\s*\}\s*_\s*(\d+)\s*C\s*_\s*(\d+)', r'{}_{\\1} C _{\\2}', result)
            result = re.sub(r'((?:\{\s*\})?)\s*_\s*(\d+)\s*C\s*_\s*(\d+)', lambda m: f"{m.group(1)}_{m.group(2)} C _{{{m.group(3)}}}", result)
            
            # 7. mathrm 처리 - 맨 앞에 rm 추가(없는 경우)
            if '\\mathrm' in result:
                result = re.sub(r'\\mathrm\s*\{\s*([A-Z])\s*\}', r'rm \1', result)  # \mathrm{P} 등의 패턴 처리
                result = result.replace('\\mathrm', 'rm')   # 남은 \mathrm 제거
            if not result.startswith('rm ') and ('over' in result or 'LEFT' in result):
                result = 'rm ' + result
            
            # 8. 불필요한 공백 제거
            result = re.sub(r'\s+', ' ', result)
            result = re.sub(r'\{\s+', '{', result)
            result = re.sub(r'\s+\}', '}', result)
            result = result.replace('{ }', '{}')
            
            return result
            
        except Exception as e:
            print(f"Error during conversion from Latex to Hangul : {str(e)}")
            return latex_expr

    def extract_equations_from_xml(self, xml_content):
        """XML 문서에서 수식 부분 추출"""
        try:
            # XML 파싱 시도
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                # XML이 아니거나 파싱 오류가 있는 경우 정규식으로 시도
                print("Failed XML parsing, Try with regular expression")
                return self.extract_equations_with_regex(xml_content)
            
            # 수식 태그 찾기 (여러 가능한 패턴 시도)
            equations = []
            patterns = [
                './/equation',
                './/*[@type="equation"]',
                './/수식',
                './/formula',
                './/*[contains(@class, "equation")]'
            ]
            
            for pattern in patterns:
                try:
                    equations = root.findall(pattern)
                    if equations:
                        break
                except:
                    continue
            
            result = []
            if equations:
                for eq in equations:
                    eq_text = eq.text
                    if eq_text and eq_text.strip():
                        result.append(eq_text)
                    
                    # 자식 요소도 확인
                    for child in eq.findall('.//*'):
                        if child.text and child.text.strip():
                            result.append(child.text)
            
            # 결과가 없으면 정규식으로 시도
            if not result:
                return self.extract_equations_with_regex(xml_content)
            
            return result
        except Exception as e:
            print(f"Error during parsing XML : {str(e)}")
            return self.extract_equations_with_regex(xml_content)

    def extract_equations_with_regex(self, content):
        """정규식을 사용하여 텍스트에서 수식 패턴 추출"""
        result = []
        
        # 다양한 수식 패턴 시도
        patterns = [
            r'<equation[^>]*>(.*?)</equation>',
            r'<formula[^>]*>(.*?)</formula>',
            r'<수식[^>]*>(.*?)</수식>',
            r'\{[^{}]*\}\s*over\s*\{[^{}]*\}',
            r'rm\s+[A-Z]+\s+LEFT',
            r'TIMES|SMALLINTER|over'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                result.extend(matches)
        
        return result

    def process_file(self, file_path):
        """파일 확장자에 따라 처리 메서드 호출"""
        try:
            _, ext = os.path.splitext(file_path)
            
            if ext.lower() == '.hml':
                return self.parse_hml_file(file_path)
            elif ext.lower() in ['.xml', '.hwpx']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # UTF-8로 읽지 못할 경우 다른 인코딩 시도
                    with open(file_path, 'r', encoding='cp949') as f:
                        content = f.read()
                return self.extract_equations_from_xml(content)
            else:
                print(f"The file format is not supported : {ext}")
                # 텍스트 파일로 간주하고 시도
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return self.extract_equations_with_regex(content)
                except Exception as e:
                    print(f"Failed file read: {str(e)}")
                    return []
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            return []

    def find_equation_in_text(self, text):
        """일반 텍스트에서 수식 패턴 찾기"""
        patterns = [
            r'\{[^{}]*\}\s*over\s*\{[^{}]*\}',  # 분수 패턴
            r'rm\s+[A-Z]+\s+LEFT',  # 확률 함수 패턴
            r'TIMES|SMALLINTER|over'  # 특수 수학 연산자
        ]
        
        results = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # 전체 문장에서 패턴 주변의 컨텍스트를 찾아 결과에 추가
                for match in matches:
                    start_idx = text.find(match)
                    if start_idx >= 0:
                        # 패턴 주변 50자 정도를 컨텍스트로 가져옴
                        context_start = max(0, start_idx - 50)
                        context_end = min(len(text), start_idx + len(match) + 50)
                        context = text[context_start:context_end]
                        results.append(context)
        
        return results

# 예시 테스트
def main():
    converter = KoreanLatexConverter()
    
    # 한글 수식에서 Latex로 변환 테스트
    korean_expr1 = "rm {{1} over {3} TIMES  {1} over {3}} over {{1} over {3} TIMES  {1} over {3} + LEFT ( {2} over {3} TIMES  {{}_{2} C _{1} TIMES  _{1} C {1}} over {{}{3} C _{2}} RIGHT )} = {1} over {5}"
    latex_result1 = converter.korean_to_latex_convert(korean_expr1)
    
    korean_expr2 = "rm P LEFT ( it A SMALLINTER B ^{C} RIGHT ) = rm P LEFT ( it A RIGHT ) rm P LEFT ( it B ^{C} RIGHT ) = rm P LEFT ( it A RIGHT ) TIMES {3} over {8} = {1} over {8}"
    latex_result2 = converter.korean_to_latex_convert(korean_expr2)
    
    print("예시 1:")
    print("한글 수식:", korean_expr1)
    print("변환된 LaTeX:", latex_result1)
    print("\n예시 2:")
    print("한글 수식:", korean_expr2)
    print("변환된 LaTeX:", latex_result2)
    
    # Latex에서 한글 수식으로 역변환 테스트
    expected_latex1 = r"\dfrac{ \dfrac{ 1 } { 3 } \times \dfrac{ 1 } { 3 } } { \dfrac{ 1 } { 3 } \times \dfrac{ 1 } { 3 } + \left ( \dfrac{ 2 } { 3 } \times \dfrac{ { } _ { 2 } {\mathrm C} _ { 1 } \times _ { 1 } {\mathrm C} _ { 1 } } { { } _ { 3 } {\mathrm C} _ { 2 } } \right ) } = \dfrac{ 1 } { 5 }"
    korean_back1 = converter.latex_to_korean_convert(expected_latex1)
    
    expected_latex2 = r"\mathrm { P } \left ( A \cap B ^ { C } \right ) = \mathrm { P } \left ( A \right ) \mathrm { P } \left ( B ^ { C } \right ) = \mathrm { P } \left ( A \right ) \times \dfrac{ 3 } { 8 } = \dfrac{ 1 } { 8 }"
    korean_back2 = converter.latex_to_korean_convert(expected_latex2)
    
    print("\n역변환 테스트:")
    print("LaTeX 수식 1:", expected_latex1)
    print("역변환된 한글 수식 1:", korean_back1)
    print("\nLaTeX 수식 2:", expected_latex2)
    print("역변환된 한글 수식 2:", korean_back2)

if __name__ == "__main__":
    main()