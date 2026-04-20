# qichacha_util.py
import time
import hashlib
import json
import requests
from config import QICHACHA_APPKEY, QICHACHA_SECRETKEY, QICHACHA_API_BASE_URL

def gen_qcc_token(app_key, secret_key, timespan):
    """
    生成企查查 API 的 Token
    Token = Md5(key + Timespan + SecretKey)
    """
    sign_string = f"{app_key}{timespan}{secret_key}"
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

def _call_qcc_api(endpoint, params):
    """
    通用企查查 API 调用函数
    """
    timespan = str(int(time.time()))
    token = gen_qcc_token(QICHACHA_APPKEY, QICHACHA_SECRETKEY, timespan)

    headers = {
        'Token': token,
        'Timespan': timespan,
        'Content-Type': 'application/json' # QCC API doc says Content-Type is not required for GET, but often good practice
    }

    # Add AppKey to params
    # Note: Some QCC APIs use 'key' in query, others don't explicitly mention it for GET
    # The provided examples use 'key' in query, so we'll add it here.
    params['key'] = QICHACHA_APPKEY

    url = f"{QICHACHA_API_BASE_URL}{endpoint}"

    print(f"Calling Qichacha API: {url} with params: {params}, headers: {headers}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status() # 检查 HTTP 错误状态

        result = response.json()
        print(f"Qichacha API response for {endpoint}: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if result.get('Status') == '200':
            return result.get('Result') # Most APIs return data in 'Result'
        else:
            print(f"Qichacha API returned an error or no data for {endpoint}: {result.get('Message', 'Unknown error')}")
            return None
    except requests.exceptions.Timeout:
        print(f"请求企查查 API ({endpoint}) 超时。")
        return None
    except requests.exceptions.ConnectionError:
        print(f"无法连接到企查查 API ({endpoint})。")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"企查查 API ({endpoint}) 返回 HTTP 错误: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"调用企查查 API ({endpoint}) 发生未知错误: {e}")
        return None


def verify_enterprise_info(search_key):
    """
    调用企查查企业信息核验接口 (API Code 1)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :return: 企查查 API 返回的原始数据，或 None（如果请求失败）
    """
    params = {'searchKey': search_key}
    result = _call_qcc_api("/EnterpriseInfo/Verify", params)
    if result and result.get('VerifyResult') == 1:
        return result.get('Data')
    return None

def get_basic_details_by_name(keyword):
    """
    调用企查查企业工商信息接口 (API Code 410)
    :param keyword: 搜索关键词（支持统一社会信用代码、企业名称）
    :return: 企查查 API 返回的原始数据，或 None（如果请求失败）
    """
    params = {'keyword': keyword}
    return _call_qcc_api("/ECIV4/GetBasicDetailsByName", params)

def fuzzy_search_companies(search_key, page_index=1):
    """
    调用企查查企业模糊搜索接口 (API Code 886)
    :param search_key: 搜索关键词（支持企业名、人名、产品名、地址、电话、经营范围等）
    :param page_index: 页码，默认第1页
    :return: 企查查 API 返回的 Result 列表，或 None（如果请求失败）
    """
    params = {'searchKey': search_key, 'pageIndex': str(page_index)}
    return _call_qcc_api("/FuzzySearch/GetList", params)

def get_tax_invoice_info(key_word):
    """
    调用企查查税号开票信息接口 (API Code 271)
    :param key_word: 查询关键字（公司名称）
    :return: 企查查 API 返回的 Result 对象，或 None（如果请求失败）
    """
    params = {'keyWord': key_word}
    return _call_qcc_api("/ECICreditCode/GetCreditCodeNew", params)

def get_kyc_info(search_key):
    """
    调用企查查客户身份识别接口 (API Code 2003)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :return: 企查查 API 返回的原始数据 Data，或 None（如果请求失败）
    """
    params = {'searchKey': search_key}
    result = _call_qcc_api("/CustomerDueDiligence/KYC", params)
    if result and result.get('VerifyResult') == 1: # KYC API also uses VerifyResult
        return result.get('Data')
    return None

def search_certification(search_key, cert_category=None, page_size=10, page_index=1, is_valid=None):
    """
    调用企查查资质证书接口 (API Code 255)
    :param search_key: 搜索关键字（公司名称）
    :param cert_category: 证书类型
    :param page_size: 每页数据条数
    :param page_index: 页码
    :param is_valid: 是否有效（0-无效，1-有效，2-未披露）
    :return: 企查查 API 返回的 Result 列表，或 None（如果请求失败）
    """
    params = {
        'searchKey': search_key,
        'pageSize': str(page_size),
        'pageIndex': str(page_index)
    }
    if cert_category:
        params['certCategory'] = cert_category
    if is_valid is not None:
        params['isValid'] = str(is_valid)
    return _call_qcc_api("/ECICertification/SearchCertification", params)

def search_trademark_by_applicant(keyword, int_cls=None, page_size=10, page_index=1):
    """
    调用企查查全国商标查询接口 (API Code 231)
    :param keyword: 申请人名称
    :param int_cls: 商标类别号
    :param page_size: 每页数据条数
    :param page_index: 页码
    :return: 企查查 API 返回的 Result 列表，或 None（如果请求失败）
    """
    params = {
        'keyword': keyword,
        'pageSize': str(page_size),
        'pageIndex': str(page_index)
    }
    if int_cls:
        params['intCls'] = int_cls
    return _call_qcc_api("/tm/SearchByApplicant", params)

def search_patent(search_key, search_type=None, kind_code_desc=None, ipc=None, pub_date_begin=None, pub_date_end=None, page_size=10, page_index=1):
    """
    调用企查查专利查询接口 (API Code 514)
    :param search_key: 查询关键字
    :param search_type: 搜索类型
    :param kind_code_desc: 专利类型
    :param ipc: 国际专利分类号
    :param pub_date_begin: 发布开始时间
    :param pub_date_end: 发布结束时间
    :param page_size: 每页数据条数
    :param page_index: 页码
    :return: 企查查 API 返回的 Result 列表，或 None（如果请求失败）
    """
    params = {
        'searchKey': search_key,
        'pageSize': str(page_size),
        'pageIndex': str(page_index)
    }
    if search_type:
        params['searchType'] = search_type
    if kind_code_desc:
        params['kindCodeDesc'] = kind_code_desc
    if ipc:
        params['ipc'] = ipc
    if pub_date_begin:
        params['pubDateBegin'] = pub_date_begin
    if pub_date_end:
        params['pubDateEnd'] = pub_date_end
    return _call_qcc_api("/PatentV4/Search", params)

def get_annual_report(key_no, year=None):
    """
    调用企查查企业年报信息接口 (API Code 213)
    :param key_no: 企业名称、统一社会信用代码
    :param year: 报送年度
    :return: 企查查 API 返回的 Result 列表，或 None（如果请求失败）
    """
    params = {'keyNo': key_no}
    if year:
        params['year'] = year
    return _call_qcc_api("/AR/GetAnnualReport", params)

# --- 新增的企查查 API 封装函数 ---

def comprehensive_risk_scan(search_key):
    """
    调用企查查综合风险排查接口 (API Code 2006)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :return: 企查查 API 返回的原始数据 Data，或 None（如果请求失败）
    """
    params = {'searchKey': search_key}
    result = _call_qcc_api("/RiskControl/Scan", params)
    if result and result.get('VerifyResult') == 1:
        return result.get('Data')
    return None

def get_shixin_list(search_key, page_index=1, page_size=10):
    """
    调用企查查失信核查接口 (API Code 740)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :param page_index: 页码，默认第1页
    :param page_size: 每页数据条数，默认为10，最大20
    :return: 企查查 API 返回的 Data 列表，或 None（如果请求失败）
    """
    params = {
        'searchKey': search_key,
        'pageIndex': str(page_index),
        'pageSize': str(page_size)
    }
    result = _call_qcc_api("/ShixinCheck/GetList", params)
    if result and result.get('VerifyResult') == 1:
        return result.get('Data')
    return None

def get_exception_list(search_key):
    """
    调用企查查经营异常核查接口 (API Code 739)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :return: 企查查 API 返回的 Data 列表，或 None（如果请求失败）
    """
    params = {'searchKey': search_key}
    result = _call_qcc_api("/ExceptionCheck/GetList", params)
    if result and result.get('VerifyResult') == 1:
        return result.get('Data')
    return None

def get_zhixing_list(search_key, page_index=1, page_size=10):
    """
    调用企查查被执行人核查接口 (API Code 741)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :param page_index: 页码，默认第1页
    :param page_size: 每页数据条数，默认为10，最大20
    :return: 企查查 API 返回的 Data 列表，或 None（如果请求失败）
    """
    params = {
        'searchKey': search_key,
        'pageIndex': str(page_index),
        'pageSize': str(page_size)
    }
    result = _call_qcc_api("/ZhixingCheck/GetList", params)
    if result and result.get('VerifyResult') == 1:
        return result.get('Data')
    return None

def get_serious_illegal_list(search_key):
    """
    调用企查查严重违法核查接口 (API Code 748)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :return: 企查查 API 返回的 Data 列表，或 None（如果请求失败）
    """
    params = {'searchKey': search_key}
    result = _call_qcc_api("/SeriousIllegalCheck/GetList", params)
    if result and result.get('VerifyResult') == 1:
        return result.get('Data')
    return None

def get_judgment_doc_list(search_key, pub_year=None, case_identity=None, case_status=None, key_word_filter=None, page_index=1, page_size=10):
    """
    调用企查查裁决文书核查接口 (API Code 887)
    :param search_key: 搜索关键词（统一社会信用代码、企业名称）
    :param pub_year: 发布年份
    :param case_identity: 案件身份（1-被告，2-原告）
    :param case_status: 案件状态（1-待结案，2-已结案）
    :param key_word_filter: 筛选关键词（支持案号、案由、当事人、判决结果）
    :param page_index: 页码
    :param page_size: 每页数据条数
    :return: 企查查 API 返回的 Data 列表，或 None（如果请求失败）
    """
    params = {
        'searchKey': search_key,
        'pageIndex': str(page_index),
        'pageSize': str(page_size)
    }
    if pub_year:
        params['pubYear'] = str(pub_year)
    if case_identity:
        params['caseIdentity'] = str(case_identity)
    if case_status:
        params['caseStatus'] = str(case_status)
    if key_word_filter:
        params['keyWord'] = key_word_filter # Note: parameter name is 'keyWord' in QCC doc, not 'key_word_filter'
    result = _call_qcc_api("/JudgmentDocCheck/GetList", params)
    if result and result.get('VerifyResult') == 1:
        return result.get('Data')
    return None