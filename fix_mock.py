import os
import re

MOCK_CODE = """        keyword_candidates = [
            str(params.get('keyword', '')),
            str(params.get('searchKey', '')),
            str(params.get('keyWord', '')),
            str(params.get('keyNo', ''))
        ]
        query_text = ' '.join(keyword_candidates).lower()
        
        companies = [
            {
                'keywords': ['维沃', 'vivo'],
                'Name': '维沃移动通信有限公司',
                'OperName': '施玉坚',
                'StartDate': '2010-06-07',
                'Status': '存续',
                'No': '441900400125191',
                'CreditCode': '91441900557262083U',
                'RegistCapi': '6500万元人民币',
                'EconKind': '有限责任公司(自然人投资或控股)',
                'Address': '广东省东莞市长安镇维沃路1号',
                'Scope': '生产、销售：移动通信业务设备、计算机及其零配件；通信技术及配套软件的开发、技术转让等。'
            },
            {
                'keywords': ['腾讯', 'tencent'],
                'Name': '腾讯科技（深圳）有限公司',
                'OperName': '马化腾',
                'StartDate': '2000-02-24',
                'Status': '存续',
                'No': '440301104612450',
                'CreditCode': '91440300708461136T',
                'RegistCapi': '200000万美元',
                'EconKind': '有限责任公司(台港澳法人独资)',
                'Address': '深圳市南山区海天二路33号腾讯滨海大厦',
                'Scope': '从事计算机软硬件的技术开发、销售自行开发的软件；计算机技术服务及信息服务等。'
            },
            {
                'keywords': ['阿里', 'alibaba'],
                'Name': '阿里巴巴（中国）网络技术有限公司',
                'OperName': '戴珊',
                'StartDate': '1999-09-09',
                'Status': '存续',
                'No': '330100400013504',
                'CreditCode': '91330100799655058B',
                'RegistCapi': '1072514万美元',
                'EconKind': '有限责任公司(台港澳法人独资)',
                'Address': '杭州市滨江区网商路699号',
                'Scope': '网络技术、网络软件等技术开发；电子商务平台及软件系统开发；企业管理咨询。'
            },
            {
                'keywords': ['字节', 'bytedance', '头条'],
                'Name': '北京字节跳动科技有限公司',
                'OperName': '张一鸣',
                'StartDate': '2012-03-09',
                'Status': '存续',
                'No': '110108014664790',
                'CreditCode': '91110108592317351H',
                'RegistCapi': '1000万元人民币',
                'EconKind': '有限责任公司(自然人独资)',
                'Address': '北京市海淀区紫金数码园4号楼',
                'Scope': '从事因特网文化活动；经营电信业务；技术开发、技术推广、技术转让、技术咨询、技术服务。'
            },
            {
                'keywords': ['百度', 'baidu'],
                'Name': '百度在线网络技术（北京）有限公司',
                'OperName': '崔珊珊',
                'StartDate': '2000-01-18',
                'Status': '存续',
                'No': '110108000673293',
                'CreditCode': '91110000802100433B',
                'RegistCapi': '4520万美元',
                'EconKind': '有限责任公司(外国法人独资)',
                'Address': '北京市海淀区上地十街10号百度大厦3层',
                'Scope': '开发、生产计算机软件；提供相关技术咨询、技术服务、技术培训。'
            }
        ]
        
        company_detail = companies[0] # Default to vivo if no match
        for comp in companies:
            for kw in comp['keywords']:
                if kw in query_text:
                    company_detail = comp
                    break
"""

qcc_file = 'qichacha_util.py'
with open(qcc_file, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "        keyword_candidates = ["
end_marker = "        if '/EnterpriseInfo/Verify' in endpoint:"
if start_marker in content and end_marker in content:
    before = content[:content.find(start_marker)]
    after = content[content.find(end_marker):]
    new_content = before + MOCK_CODE + after
    with open(qcc_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

DIRS_TO_SEARCH = ['.']
EXTENSIONS = ['.py', '.html', '.js', '.md']

for root, dirs, files in os.walk('.'):
    if '.venv' in root or '__pycache__' in root or 'instance' in root or '.git' in root:
        continue
        
    for file in files:
        if file.endswith(tuple(EXTENSIONS)):
            filepath = os.path.join(root, file)
            if 'fix_mock.py' in filepath:
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    c = f.read()
                except UnicodeDecodeError:
                    continue
            
            if '企查查' in c:
                new_c = c.replace('企查查', '内部数据库')
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_c)

print("Done modification!")