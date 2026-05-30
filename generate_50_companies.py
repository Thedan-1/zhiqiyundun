import json
import random
import pandas as pd
import os
import sys

# 基础数据
base_large_extra = {
    'RealCapi': '已实缴',
    'TermStart': '2010-01-01',
    'TermEnd': '长期',
    'TaxpayerType': '一般纳税人',
    'PersonScope': '10000人以上',
    'InsuredCount': '15000',
    'IsSmall': '0',
    'Scale': '大型企业',
}

large_companies = [
    {
        **base_large_extra,
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
        'Scope': '生产、销售：移动通信业务设备、计算机及其零配件；通信技术及配套软件的开发、技术转让等。',
        'PersonScope': '5000-10000人',
        'InsuredCount': '6000',
        'ContactInfo': {'Tel': '400-678-9688', 'Email': 'service@vivo.com'},
        'ActualControllerList': [{'Name': '沈炜'}],
        'Area': {'Province': '广东省', 'City': '东莞市', 'County': ''},
        'Industry': {'Industry': '制造业', 'SubIndustry': '计算机、通信和其他电子设备制造业'},
        'QccIndustry': {'AName': '制造业', 'BName': '通信设备制造'},
        'PartnerList': [{'StockName': '维沃控股有限公司', 'StockPercent': '100%'}],
        'EmployeeList': [{'Name': '施玉坚', 'Job': '执行董事'}],
        'StockInfo': {'StockType': '未上市', 'StockNumber': ''},
        'OriginalName': [{'Name': '暂无'}],
        'BankInfo': {'Bank': '中国建设银行东莞长安支行', 'BankAccount': '44050110461200000123'}
    },
    {
        **base_large_extra,
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
        'Scope': '从事计算机软硬件的技术开发、销售自行开发的软件；计算机技术服务及信息服务等。',
        'ContactInfo': {'Tel': '0755-86013388', 'Email': 'tencent_sp@tencent.com'},
        'ActualControllerList': [{'Name': '马化腾'}],
        'Area': {'Province': '广东省', 'City': '深圳市', 'County': '南山区'},
        'Industry': {'Industry': '信息传输、软件和信息技术服务业', 'SubIndustry': '互联网和相关服务'},
        'QccIndustry': {'AName': '信息传输', 'BName': '互联网'},
        'PartnerList': [{'StockName': '中霸集团有限公司', 'StockPercent': '100%'}],
        'EmployeeList': [{'Name': '马化腾', 'Job': '执行董事'}],
        'StockInfo': {'StockType': '港股', 'StockNumber': '00700'},
        'OriginalName': [{'Name': '无'}],
        'BankInfo': {'Bank': '招商银行深圳分行', 'BankAccount': '755914222010101'}
    },
    {
        **base_large_extra,
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
        'Scope': '网络技术、网络软件等技术开发；电子商务平台及软件系统开发；企业管理咨询。',
        'ContactInfo': {'Tel': '0571-85022088', 'Email': 'alibaba@service.alibaba.com'},
        'ActualControllerList': [{'Name': '马云'}],
        'Area': {'Province': '浙江省', 'City': '杭州市', 'County': '滨江区'},
        'Industry': {'Industry': '信息传输、软件和信息技术服务业', 'SubIndustry': '互联网和相关服务'},
        'QccIndustry': {'AName': '信息传输', 'BName': '互联网'},
        'PartnerList': [{'StockName': '淘宝中国控股有限公司', 'StockPercent': '100%'}],
        'EmployeeList': [{'Name': '戴珊', 'Job': '法定代表人'}],
        'StockInfo': {'StockType': '纽交所', 'StockNumber': 'BABA'},
        'OriginalName': [{'Name': '无'}],
        'BankInfo': {'Bank': '工商银行杭州支行', 'BankAccount': '1202020202020202'}
    },
    {
        **base_large_extra,
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
        'Scope': '从事因特网文化活动；经营电信业务；技术开发、技术推广、技术转让、技术咨询、技术服务。',
        'ContactInfo': {'Tel': '010-58341833', 'Email': 'service@bytedance.com'},
        'ActualControllerList': [{'Name': '张一鸣'}],
        'Area': {'Province': '北京市', 'City': '市辖区', 'County': '海淀区'},
        'Industry': {'Industry': '信息传输、软件和信息技术服务业', 'SubIndustry': '互联网和相关服务'},
        'QccIndustry': {'AName': '信息传输', 'BName': '互联网'},
        'PartnerList': [{'StockName': '字节跳动(香港)有限公司', 'StockPercent': '100%'}],
        'EmployeeList': [{'Name': '张一鸣', 'Job': '执行董事'}],
        'StockInfo': {'StockType': '未上市', 'StockNumber': ''},
        'OriginalName': [{'Name': '无'}],
        'BankInfo': {'Bank': '中国银行北京分行', 'BankAccount': '100100100100'}
    },
    {
        **base_large_extra,
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
        'Scope': '开发、生产计算机软件；提供相关技术咨询、技术服务、技术培训。',
        'ContactInfo': {'Tel': '010-59928888', 'Email': 'help@baidu.com'},
        'ActualControllerList': [{'Name': '李彦宏'}],
        'Area': {'Province': '北京市', 'City': '市辖区', 'County': '海淀区'},
        'Industry': {'Industry': '信息传输、软件和信息技术服务业', 'SubIndustry': '互联网和相关服务'},
        'QccIndustry': {'AName': '信息传输', 'BName': '互联网'},
        'PartnerList': [{'StockName': 'Baidu Holdings Limited', 'StockPercent': '100%'}],
        'EmployeeList': [{'Name': '崔珊珊', 'Job': '执行董事'}],
        'StockInfo': {'StockType': '纳斯达克', 'StockNumber': 'BIDU'},
        'OriginalName': [{'Name': '无'}],
        'BankInfo': {'Bank': '建设银行北京上地支行', 'BankAccount': '102030405060708'}
    }
]

cities = [
    {'Province': '广东省', 'City': '广州市', 'County': '天河区', 'AddrPrefix': '广东省广州市天河区'},
    {'Province': '浙江省', 'City': '杭州市', 'County': '西湖区', 'AddrPrefix': '浙江省杭州市西湖区'},
    {'Province': '四川省', 'City': '成都市', 'County': '武侯区', 'AddrPrefix': '四川省成都市武侯区'},
    {'Province': '江苏省', 'City': '南京市', 'County': '建邺区', 'AddrPrefix': '江苏省南京市建邺区'},
    {'Province': '湖北省', 'City': '武汉市', 'County': '洪山区', 'AddrPrefix': '湖北省武汉市洪山区'}
]

base_sme_names = [
    "星辰科技", "蓝海贸易", "绿源建材", "创新网络", "飞跃物流",
    "宏图文化", "共创广告", "天际软件", "融通商贸", "启航教育",
    "金桥咨询", "未来传媒", "智能制造", "云端数据", "光影视觉",
    "浩宇机电", "盛世地产", "嘉合餐饮", "博雅信息", "汇智医药",
    "瑞丰化工", "卓越机械", "聚力设备", "诚达包装", "信诚财务",
    "鑫源环保", "泰和农业", "安泰物业", "华康医疗", "恒大装饰",
    "新纪元科技", "大有商贸", "百川物流", "九鼎投资", "万达电子",
    "同创仪器", "明达五金", "兴业通讯", "远大塑胶", "通达木业",
    "时代电力", "正大生物", "中天纺织", "华泰服饰", "中科材料"
]

names = ["王涛", "李明", "张伟", "刘洋", "陈静", "杨超", "赵磊", "黄勇", "吴芳", "周强"]

sme_companies = []
for i, name_prefix in enumerate(base_sme_names):
    full_name = f"{name_prefix}有限公司"
    city = random.choice(cities)
    oper_name = random.choice(names)
    start_year = random.randint(2015, 2023)
    start_date = f"{start_year}-0{random.randint(1,9)}-1{random.randint(0,9)}"
    reg_cap = f"{random.randint(50, 500)}万元人民币"
    person_cnt = random.randint(5, 45)
    
    comp = {
        'keywords': [name_prefix],
        'Name': full_name,
        'OperName': oper_name,
        'StartDate': start_date,
        'Status': '存续',
        'No': f"11010{random.randint(1000000000, 9999999999)}",
        'CreditCode': f"91{random.randint(1000000000000000, 9999999999999999)}L",
        'RegistCapi': reg_cap,
        'RealCapi': '未实缴' if random.random() > 0.5 else '已实缴',
        'EconKind': '有限责任公司',
        'Address': f"{city['AddrPrefix']}街道{random.randint(1,100)}号",
        'Scope': f"{name_prefix}相关的技术开发、咨询、服务；销售商品等。",
        'PersonScope': f"{person_cnt}人",
        'InsuredCount': str(random.randint(max(1, person_cnt-10), person_cnt)),
        'TaxpayerType': '小规模纳税人' if person_cnt < 20 else '一般纳税人',
        'IsSmall': '1',
        'Scale': '微型企业' if person_cnt < 20 else '小型企业',
        'Area': {'Province': city['Province'], 'City': city['City'], 'County': city['County']},
        'ContactInfo': {'Tel': f"138{random.randint(10000000,99999999)}", 'Email': f"contact@{random.randint(1000,9999)}.com"},
        'Industry': {'Industry': '科技推广和应用服务业' if '科技' in name_prefix else '各类实体与服务业', 'SubIndustry': '综合服务'},
        'QccIndustry': {'AName': '服务业', 'BName': '其他'},
        'PartnerList': [{'StockName': oper_name, 'StockPercent': '100%'}],
        'EmployeeList': [{'Name': oper_name, 'Job': '执行董事'}],
        'ActualControllerList': [{'Name': oper_name}],
        'StockInfo': {'StockType': '未上市', 'StockNumber': ''},
        'OriginalName': [{'Name': '无'}],
        'BankInfo': {'Bank': '当地商业银行', 'BankAccount': f"102030{random.randint(10000000,99999999)}"}
    }
    sme_companies.append(comp)

all_companies = large_companies + sme_companies

# Save to JSON
with open('mock_companies.json', 'w', encoding='utf-8') as f:
    json.dump(all_companies, f, ensure_ascii=False, indent=2)

# Save to Excel
df_data = []
for c in all_companies:
    df_data.append({
        '企业名称': c.get('Name', ''),
        '法定代表人': c.get('OperName', ''),
        '成立日期': c.get('StartDate', ''),
        '注册资本': c.get('RegistCapi', ''),
        '企业状态': c.get('Status', ''),
        '统一社会信用代码': c.get('CreditCode', ''),
        '企业类型': c.get('EconKind', ''),
        '注册地址': c.get('Address', ''),
        '经营范围': c.get('Scope', ''),
        '人员规模': c.get('PersonScope', ''),
        '参保人数': c.get('InsuredCount', ''),
        '纳税人资质': c.get('TaxpayerType', ''),
        '企业规模': c.get('Scale', ''),
        '联系电话': c.get('ContactInfo', {}).get('Tel', ''),
        '电子邮箱': c.get('ContactInfo', {}).get('Email', '')
    })

df = pd.DataFrame(df_data)
df.to_excel('企业信息演示数据_50家.xlsx', index=False)
print("Created mock_companies.json and 企业信息演示数据_50家.xlsx!")

# Now patch the application to read from the JSON file
MOCK_CODE = """        keyword_candidates = [
            str(params.get('keyword', '')),
            str(params.get('searchKey', '')),
            str(params.get('keyWord', '')),
            str(params.get('keyNo', ''))
        ]
        query_text = ' '.join(keyword_candidates).lower()
        
        import json
        import os
        mock_file = os.path.join(os.path.dirname(__file__), 'mock_companies.json')
        companies = []
        if os.path.exists(mock_file):
            with open(mock_file, 'r', encoding='utf-8') as f:
                companies = json.load(f)
                
        company_detail = companies[0] if companies else {}
        found = False
        for comp in companies:
            if 'keywords' in comp:
                for kw in comp['keywords']:
                    if kw in query_text:
                        company_detail = comp
                        found = True
                        break
            if found:
                break
            # 兼容没写keywords的中小企业查询
            if comp.get('Name', '') in query_text or query_text in comp.get('Name', ''):
                company_detail = comp
                found = True
                break
"""

qcc_file = '内部数据库_util.py' if os.path.exists('内部数据库_util.py') else 'qichacha_util.py'

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
        print("Updated mock logic to read from JSON.")
