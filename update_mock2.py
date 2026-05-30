import os

FIX_CODE = """        keyword_candidates = [
            str(params.get('keyword', '')),
            str(params.get('searchKey', '')),
            str(params.get('keyWord', '')),
            str(params.get('keyNo', ''))
        ]
        # Remove empty strings and spaces to match properly
        valid_cands = [k.strip().lower() for k in keyword_candidates if k.strip()]
        query_text = ' '.join(valid_cands) if valid_cands else ''
        
        import json
        import os
        mock_file = os.path.join(os.path.dirname(__file__), 'mock_companies.json')
        companies = []
        if os.path.exists(mock_file):
            with open(mock_file, 'r', encoding='utf-8') as f:
                companies = json.load(f)
                
        company_detail = companies[0] if companies else {}
        if query_text:
            found = False
            for comp in companies:
                if 'keywords' in comp:
                    for kw in comp['keywords']:
                        kw_lower = kw.lower()
                        if kw_lower in query_text or query_text in kw_lower:
                            company_detail = comp
                            found = True
                            break
                if found:
                    break
                # Fallback to Name
                comp_name = comp.get('Name', '').lower()
                if query_text in comp_name or comp_name in query_text:
                    company_detail = comp
                    break"""

qcc_file = 'qichacha_util.py' 
if not os.path.exists(qcc_file):
    qcc_file = '内部数据库_util.py'

with open(qcc_file, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "        keyword_candidates = ["
end_marker = "        if '/EnterpriseInfo/Verify' in endpoint:"

if start_marker in content and end_marker in content:
    before = content[:content.find(start_marker)]
    after = content[content.find(end_marker):]
    new_content = before + FIX_CODE + "\n" + after
    with open(qcc_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
        print("Updated mock logic for better matching.")