# app.py
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, url_for, redirect, flash, session, abort, send_file
import requests
import uuid
import time
import json
import urllib.parse
import traceback
import datetime
import os
import re
import io
import pandas as pd
from functools import wraps  # 用于装饰器
from collections import defaultdict  # 用于分类链接

# Flask-SQLAlchemy 和 Flask-Login
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import SelectField, BooleanField
from wtforms.validators import DataRequired

# 导入配置
import config

# 导入数据库模型和表单
from models import db, User, Role, Permission, SystemSetting, AuditLog, ExternalLink
from forms import RegistrationForm, LoginForm, ResetPasswordForm, UserForm, RoleForm, SystemSettingForm, ExternalLinkForm

# 假设 auth_util.py 存在于同一目录下
from auth_util import gen_sign_headers
from qichacha_util import (
    verify_enterprise_info, get_basic_details_by_name, fuzzy_search_companies,
    get_tax_invoice_info, get_kyc_info, search_certification, search_trademark_by_applicant,
    search_patent, get_annual_report,
    comprehensive_risk_scan, get_shixin_list, get_exception_list,
    get_zhixing_list, get_serious_illegal_list, get_judgment_doc_list
)

app = Flask(__name__, instance_relative_config=True)
# APP_ID 和 APP_KEY 将从 SystemSetting 动态获取，这里不再硬编码全局变量

URI_COMPLETIONS = '/vivogpt/completions'  # 文本生成 URI
DOMAIN = 'api-ai.vivo.com.cn'
METHOD = 'POST'
# 从 config.py 加载配置
app.config.from_object(config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'site.db')
# 初始化数据库
db.init_app(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 未登录用户尝试访问@login_required页面时，会重定向到此视图函数


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 权限控制装饰器 ---
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请登录以访问此页面。', 'warning')
                return redirect(url_for('login', next=request.url))
            if not current_user.is_active:
                flash('您的账户已被禁用。', 'danger')
                logout_user()
                return redirect(url_for('login'))

            # 检查用户角色是否拥有该权限
            if not current_user.role or not any(p.name == permission_name for p in current_user.role.permissions):
                flash('您没有足够的权限访问此页面。', 'danger')
                abort(403)  # Forbidden
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Context processor to make external_links available globally
@app.context_processor
def inject_global_data():
    # 过滤掉非活跃的链接
    all_active_external_links = ExternalLink.query.filter_by(is_active=True).order_by(ExternalLink.category,
                                                                                      ExternalLink.name).all()

    categorized_links = defaultdict(list)
    for link in all_active_external_links:
        categorized_links[link.category].append(link)

    # 对每个分类内的链接列表进行二次排序
    for category_name in categorized_links:
        # 尝试按图标名称中的数字部分排序
        # float('inf') 确保非数字或非.png的图标排在后面
        categorized_links[category_name].sort(key=lambda x: int(x.icon.split('.')[0]) if x.icon and x.icon.endswith('.png') and x.icon.split('.')[0].isdigit() else float('inf'))

    category_icons = {
        '项目管理和协作工具': 'project-diagram',
        '文档管理和网盘工具': 'folder-open',
        '下载和多媒体工具': 'download',
        '设计和营销小工具': 'paint-brush',
        'HR工具': 'users',
        '财务管理和报销平台': 'calculator',
        '法律咨询平台': 'gavel',
        '国家政策查询平台': 'scroll',
        '一站式中小企业服务平台': 'globe',
        '我的工具': 'tools', # 为您的图片工具分类添加一个 FontAwesome 图标作为分类标题图标
        '其他': 'th-large'
    }

    return dict(external_links=all_active_external_links, categorized_links=categorized_links,
                category_icons=category_icons)

# 我的 APP_ID 和 APP_KEY (蓝心大模型) - 从SystemSetting动态获取
# 注意：在请求时动态获取，而不是在全局定义
URI_COMPLETIONS = '/vivogpt/completions'  # 文本生成 URI
DOMAIN = 'api-ai.vivo.com.cn'
METHOD = 'POST'

# 获取当前文件所在目录的路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_IMAGE_PATH = os.path.join(BASE_DIR, 'static', 'images', 'beijing.jpg')

# 报告页面输入数据字段的中文映射
INPUT_DATA_KEY_MAP = {
    'companyName': '公司名称',
    'revenue': '年收入（万元）',
    'profitMargin': '利润率（%）',
    'debtRatio': '负债率（%）',
    'cashFlow': '现金流状况',
    'marketShare': '市场份额（%）',
    'competitors': '竞争对手数量',
    'customerChurn': '客户流失率（%）',
    'employeeTurnover': '员工流动率（%）',
    'managementStability': '管理层稳定性',
    'innovationAbility': '创新能力',
    'industryRisk': '行业风险',
    'policySupport': '政策支持'
}

# 风险得分字段的中文映射
k_map_risk = {
    'total': '总风险评分',
    'financial': '财务风险得分',
    'market': '市场风险得分',
    'management': '管理风险得分',
    'external': '外部风险得分'
}


# --- 辅助函数：将HTML内容转换为纯文本，用于Excel导出 ---
def html_to_plain_text(html_content):
    if not html_content:
        return ""
    # 简单的HTML标签移除和格式化
    text = html_content.replace('<br>', '\n')
    text = text.replace('<li>', '\n- ')
    text = text.replace('<ul>', '')
    text = text.replace('</ul>', '')
    text = text.replace('</li>', '')
    text = text.replace('<p>', '')
    text = text.replace('</p>', '')
    text = text.replace('<div>', '')
    text = text.replace('</div>', '')
    text = text.replace('<strong>', '')
    text = text.replace('</strong>', '')
    # 移除可能存在的数字前缀，例如 "①. "
    text = re.sub(r'^[①②③④]\.\s*', '', text, flags=re.MULTILINE)
    return text.strip()


# 计算初步风险评分 (保持不变)
def calculate_preliminary_risk(data):
    # ... (与你提供的app.py中相同) ...
    weights = {
        'financial': 0.4,
        'market': 0.3,
        'management': 0.2,
        'external': 0.1
    }

    # 确保数据是数值类型，并处理可能的 NaN
    revenue = float(data.get('revenue', 0))
    profit_margin = float(data.get('profitMargin', 0))
    debt_ratio = float(data.get('debtRatio', 0))
    market_share = float(data.get('marketShare', 0))
    competitors = float(data.get('competitors', 0))
    customer_churn = float(data.get('customerChurn', 0))
    employee_turnover = float(data.get('employeeTurnover', 0))

    # 对于下拉选择框，根据字符串值进行逻辑判断并赋值
    cash_flow = data.get('cashFlow', 'positive')
    management_stability = data.get('managementStability', 'high')
    innovation_ability = data.get('innovationAbility', 'high')
    industry_risk_value = data.get('industryRisk', 'low')
    policy_support_value = data.get('policySupport', 'yes')

    industry_risk_score = 0
    if industry_risk_value == 'high':
        industry_risk_score = 100
    elif industry_risk_value == 'medium':
        industry_risk_score = 50
    else:
        industry_risk_score = 0

    policy_support_score = 0
    if policy_support_value == 'no':
        policy_support_score = 100
    else:
        policy_support_score = 0

    # 财务风险计算 (确保分数在 0-100 之间)
    financial_risk = (
            (100 - min(max(profit_margin, 0), 100)) * 0.4 +
            min(max(debt_ratio, 0), 100) * 0.4 +
            (100 if cash_flow == 'negative' else 0) * 0.2
    )
    financial_risk = round(min(max(financial_risk, 0), 100))

    # 市场风险计算
    market_risk = (
            (100 - min(max(market_share, 0), 100)) * 0.5 +
            min(max(competitors * 5, 0), 100) * 0.5 +
            min(max(customer_churn, 0), 100) * 0.5
    )
    market_risk = round(min(max(market_risk, 0), 100))

    # 管理风险计算
    management_risk = (
            min(max(employee_turnover, 0), 100) * 0.5 +
            (100 if management_stability == 'low' else (50 if management_stability == 'medium' else 0)) * 0.3 +
            (100 if innovation_ability == 'low' else (50 if innovation_ability == 'medium' else 0)) * 0.2
    )
    management_risk = round(min(max(management_risk, 0), 100))

    # 外部风险计算
    external_risk = (
            industry_risk_score * 0.7 +
            policy_support_score * 0.3
    )
    external_risk = round(min(max(external_risk, 0), 100))

    # 综合风险评分
    total_score = (
            financial_risk * weights['financial'] +
            market_risk * weights['market'] +
            management_risk * weights['management'] +
            external_risk * weights['external']
    )

    return {
        'total': round(total_score),
        'financial': financial_risk,
        'market': market_risk,
        'management': management_risk,
        'external': external_risk
    }


# 辅助函数：精简并格式化企查查数据，用于蓝心大模型Prompt (保持不变)
def _format_qcc_data_for_bluelm_prompt(qcc_data, api_type='verify', search_key=None):
    # ... (与你提供的app.py中相同) ...
    formatted_data = []

    if api_type == 'verify' or api_type == 'kyc_verify':
        # 企业信息核验 API (Verify) 和 客户身份识别 API (KYC) 字段高度相似
        # 仅在KYC场景下，对某些列表字段做更精简的处理
        formatted_data.append(f"企业名称: {qcc_data.get('Name', 'N/A')}")
        formatted_data.append(f"统一社会信用代码: {qcc_data.get('CreditCode', 'N/A')}")
        formatted_data.append(f"法定代表人: {qcc_data.get('OperName', 'N/A')}")
        formatted_data.append(f"登记状态: {qcc_data.get('Status', 'N/A')}")
        formatted_data.append(f"成立日期: {qcc_data.get('StartDate', 'N/A')}")
        formatted_data.append(f"注册资本: {qcc_data.get('RegistCapi', 'N/A')}")
        formatted_data.append(f"实缴资本: {qcc_data.get('RealCapi', 'N/A')}")
        formatted_data.append(f"企业类型: {qcc_data.get('EconKind', 'N/A')}")
        formatted_data.append(f"营业期限: {qcc_data.get('TermStart', 'N/A')} 至 {qcc_data.get('TermEnd', 'N/A')}")
        formatted_data.append(f"纳税人资质: {qcc_data.get('TaxpayerType', 'N/A')}")
        formatted_data.append(f"人员规模: {qcc_data.get('PersonScope', 'N/A')}")
        formatted_data.append(f"参保人数: {qcc_data.get('InsuredCount', 'N/A')}")
        formatted_data.append(f"注册地址: {qcc_data.get('Address', 'N/A')}")
        if qcc_data.get('Area'):
            formatted_data.append(
                f"所属地区: {qcc_data['Area'].get('Province', '')}{qcc_data['Area'].get('City', '')}{qcc_data['Area'].get('County', '')}".strip())
        if qcc_data.get('ContactInfo'):
            formatted_data.append(f"联系电话: {qcc_data['ContactInfo'].get('Tel', 'N/A')}")
            formatted_data.append(f"邮箱: {qcc_data['ContactInfo'].get('Email', 'N/A')}")
        scope_text = qcc_data.get('Scope', 'N/A')
        if len(scope_text) > 300:  # 限制经营范围长度
            formatted_data.append(f"经营范围: {scope_text[:300]}...")
        else:
            formatted_data.append(f"经营范围: {scope_text}")

        if qcc_data.get('PartnerList') and len(qcc_data['PartnerList']) > 0:
            shareholders = [f"{p.get('StockName', 'N/A')}({p.get('StockPercent', 'N/A')})" for p in
                            qcc_data['PartnerList'][:3]]
            formatted_data.append(f"主要股东: {', '.join(shareholders)}")
        if qcc_data.get('EmployeeList') and len(qcc_data['EmployeeList']) > 0:
            employees = [f"{e.get('Name', 'N/A')}({e.get('Job', 'N/A')})" for e in qcc_data['EmployeeList'][:3]]
            formatted_data.append(f"主要人员: {', '.join(employees)}")
        if qcc_data.get('ActualControllerList') and len(qcc_data['ActualControllerList']) > 0:
            formatted_data.append(f"实际控制人: {qcc_data['ActualControllerList'][0].get('Name', 'N/A')}")
        if api_type == 'verify':  # Verify接口有更多字段
            formatted_data.append(
                f"是否小微企业: {'是' if qcc_data.get('IsSmall') == '1' else ('否' if qcc_data.get('IsSmall') == '0' else 'N/A')}")
            formatted_data.append(f"企业规模: {qcc_data.get('Scale', 'N/A')}")
            if qcc_data.get('Industry'):
                formatted_data.append(
                    f"国标行业: {qcc_data['Industry'].get('Industry', 'N/A')} - {qcc_data['Industry'].get('SubIndustry', 'N/A')}")
            if qcc_data.get('QccIndustry'):
                formatted_data.append(
                    f"企查查行业: {qcc_data['QccIndustry'].get('AName', 'N/A')} > {qcc_data['QccIndustry'].get('BName', 'N/A')}")
            if qcc_data.get('StockInfo'):
                formatted_data.append(
                    f"上市信息: {qcc_data['StockInfo'].get('StockType', 'N/A')} {qcc_data['StockInfo'].get('StockNumber', '')}")
            if qcc_data.get('OriginalName'):
                formatted_data.append(f"曾用名: {', '.join([n.get('Name', '') for n in qcc_data['OriginalName']])}")
            if qcc_data.get('RevokeInfo'):
                revoke_info = qcc_data['RevokeInfo']
                if revoke_info.get('CancelDate'):
                    formatted_data.append(
                        f"注销日期: {revoke_info['CancelDate']}, 原因: {revoke_info.get('CancelReason', 'N/A')}")
                elif revoke_info.get('RevokeDate'):
                    formatted_data.append(
                        f"吊销日期: {revoke_info['RevokeDate']}, 原因: {revoke_info.get('RevokeReason', 'N/A')}")
            if qcc_data.get('BankInfo'):
                formatted_data.append(
                    f"开票银行: {qcc_data['BankInfo'].get('Bank', 'N/A')}, 账号: {qcc_data['BankInfo'].get('BankAccount', 'N/A')}")

    elif api_type == 'industrial_info':
        formatted_data.append(f"企业名称: {qcc_data.get('Name', 'N/A')}")
        formatted_data.append(f"统一社会信用代码: {qcc_data.get('CreditCode', 'N/A')}")
        formatted_data.append(f"法定代表人: {qcc_data.get('OperName', 'N/A')}")
        formatted_data.append(f"登记状态: {qcc_data.get('Status', 'N/A')}")
        formatted_data.append(f"成立日期: {qcc_data.get('StartDate', 'N/A')}")
        formatted_data.append(f"注册资本: {qcc_data.get('RegistCapi', 'N/A')}")
        formatted_data.append(f"实缴资本: {qcc_data.get('RecCap', 'N/A')}")
        formatted_data.append(f"企业类型: {qcc_data.get('EconKind', 'N/A')}")
        formatted_data.append(f"营业期限: {qcc_data.get('TermStart', 'N/A')} 至 {qcc_data.get('TermEnd', 'N/A')}")
        formatted_data.append(f"核准日期: {qcc_data.get('CheckDate', 'N/A')}")
        formatted_data.append(f"登记机关: {qcc_data.get('BelongOrg', 'N/A')}")
        formatted_data.append(f"注册地址: {qcc_data.get('Address', 'N/A')}")
        if qcc_data.get('Area'):
            formatted_data.append(
                f"所属地区: {qcc_data['Area'].get('Province', '')}{qcc_data['Area'].get('City', '')}{qcc_data['Area'].get('County', '')}".strip())
        scope_text = qcc_data.get('Scope', 'N/A')
        if len(scope_text) > 300:
            formatted_data.append(f"经营范围: {scope_text[:300]}...")
        else:
            formatted_data.append(f"经营范围: {scope_text}")
        if qcc_data.get('OriginalName'):
            formatted_data.append(f"曾用名: {', '.join([n.get('Name', '') for n in qcc_data['OriginalName']])}")
        if qcc_data.get('RevokeInfo'):
            revoke_info = qcc_data['RevokeInfo']
            if revoke_info.get('CancelDate'):
                formatted_data.append(
                    f"注销日期: {revoke_info['CancelDate']}, 原因: {revoke_info.get('CancelReason', 'N/A')}")
            elif revoke_info.get('RevokeDate'):
                formatted_data.append(
                    f"吊销日期: {revoke_info['RevokeDate']}, 原因: {revoke_info.get('RevokeReason', 'N/A')}")

    elif api_type == 'fuzzy_search':
        if not qcc_data:  # Handle empty list case
            return f"未找到与 '{search_key}' 相关的企业。"
        formatted_data.append(f"企业名称: {qcc_data.get('Name', 'N/A')}")
        formatted_data.append(f"统一社会信用代码: {qcc_data.get('CreditCode', 'N/A')}")
        formatted_data.append(f"法定代表人: {qcc_data.get('OperName', 'N/A')}")
        formatted_data.append(f"登记状态: {qcc_data.get('Status', 'N/A')}")
        formatted_data.append(f"成立日期: {qcc_data.get('StartDate', 'N/A')}")
        formatted_data.append(f"注册地址: {qcc_data.get('Address', 'N/A')}")

    elif api_type == 'tax_invoice':
        formatted_data.append(f"企业名称: {qcc_data.get('Name', 'N/A')}")
        formatted_data.append(f"统一社会信用代码 (纳税人识别号): {qcc_data.get('CreditCode', 'N/A')}")
        formatted_data.append(f"企业类型: {qcc_data.get('EconKind', 'N/A')}")
        formatted_data.append(f"企业状态: {qcc_data.get('Status', 'N/A')}")
        formatted_data.append(f"地址: {qcc_data.get('Address', 'N/A')}")
        formatted_data.append(f"联系电话: {qcc_data.get('Tel', 'N/A')}")
        formatted_data.append(f"开户行: {qcc_data.get('Bank', 'N/A')}")
        formatted_data.append(f"开户行账号: {qcc_data.get('BankAccount', 'N/A')}")

    elif api_type == 'certification':
        if not qcc_data: return "未查询到资质证书信息。"
        formatted_data.append(f"证书名称: {qcc_data.get('Name', 'N/A')}")
        formatted_data.append(f"证书类型: {qcc_data.get('TypeDesc', 'N/A')}")
        formatted_data.append(f"证书编号: {qcc_data.get('No', 'N/A')}")
        formatted_data.append(f"生效日期: {qcc_data.get('StartDate', 'N/A')}")
        formatted_data.append(f"截止日期: {qcc_data.get('EndDate', 'N/A')}")
        formatted_data.append(f"发证机构: {', '.join(qcc_data.get('InstitutionList', [])) or 'N/A'}")
        formatted_data.append(f"证书状态: {qcc_data.get('Status', 'N/A')}")

    elif api_type == 'trademark':
        if not qcc_data: return "未查询到商标信息。"
        formatted_data.append(f"商标名称: {qcc_data.get('Name', 'N/A')}")
        formatted_data.append(f"注册号: {qcc_data.get('RegNo', 'N/A')}")
        formatted_data.append(f"国际分类: {qcc_data.get('Category', 'N/A')}")
        formatted_data.append(f"申请人: {qcc_data.get('ApplicantCn', 'N/A')}")
        formatted_data.append(f"申请日期: {qcc_data.get('AppDate', 'N/A')}")
        formatted_data.append(f"商标状态: {qcc_data.get('FlowStatusDesc', 'N/A')}")
        if qcc_data.get('ImageUrl'):
            formatted_data.append(f"商标图案URL: {qcc_data['ImageUrl']}")

    elif api_type == 'patent':
        if not qcc_data: return "未查询到专利信息。"
        formatted_data.append(f"专利标题: {qcc_data.get('Title', 'N/A')}")
        formatted_data.append(f"申请号: {qcc_data.get('ApplicationNumber', 'N/A')}")
        formatted_data.append(f"申请日期: {qcc_data.get('ApplicationDate', 'N/A')}")
        formatted_data.append(f"公开号: {qcc_data.get('PublicationNumber', 'N/A')}")
        formatted_data.append(f"公开日期: {qcc_data.get('PublicationDate', 'N/A')}")
        formatted_data.append(f"专利类型: {qcc_data.get('KindCodeDesc', 'N/A')}")
        formatted_data.append(f"法律状态: {qcc_data.get('LegalStatusDesc', 'N/A')}")
        formatted_data.append(f"发明人: {', '.join(qcc_data.get('InventorStringList', [])) or 'N/A'}")
        formatted_data.append(f"申请人: {', '.join(qcc_data.get('AssigneestringList', [])) or 'N/A'}")

    elif api_type == 'annual_report':
        if not qcc_data: return "未查询到企业年报信息。"
        basic_info = qcc_data.get('BasicInfoData', {})
        assets_data = qcc_data.get('AssetsData', {})
        formatted_data.append(f"报送年度: {qcc_data.get('Year', 'N/A')}")
        formatted_data.append(f"发布日期: {qcc_data.get('PublishDate', 'N/A')}")
        formatted_data.append(f"企业名称: {basic_info.get('CompanyName', 'N/A')}")
        formatted_data.append(f"统一社会信用代码: {basic_info.get('CreditCode', 'N/A')}")
        formatted_data.append(f"经营状态: {basic_info.get('Status', 'N/A')}")
        formatted_data.append(f"从业人数: {basic_info.get('EmployeeCount', 'N/A')}")
        formatted_data.append(f"资产总额: {assets_data.get('TotalAssets', 'N/A')}")
        formatted_data.append(f"负债总额: {assets_data.get('TotalLiabilities', 'N/A')}")
        formatted_data.append(f"营业总收入: {assets_data.get('GrossTradingIncome', 'N/A')}")
        formatted_data.append(f"利润总额: {assets_data.get('TotalProfit', 'N/A')}")
        formatted_data.append(f"净利润: {assets_data.get('NetProfit', 'N/A')}")
        formatted_data.append(f"纳税总额: {assets_data.get('TotalTaxAmount', 'N/A')}")
        if qcc_data.get('PartnerList'):
            shareholders = [
                f"{p.get('Name', 'N/A')}(认缴:{p.get('ShouldCapi', 'N/A')}, 实缴:{p.get('RealCapi', 'N/A')})" for p in
                qcc_data['PartnerList'][:3]]
            formatted_data.append(f"主要股东及出资: {', '.join(shareholders)}")
        if qcc_data.get('StockChangeList'):
            changes = [f"{sc.get('Name', 'N/A')}(前:{sc.get('Before', 'N/A')}, 后:{sc.get('After', 'N/A')})" for sc in
                       qcc_data['StockChangeList'][:2]]
            formatted_data.append(f"股权变更: {', '.join(changes)}")

    elif api_type == 'comprehensive_risk':
        # 综合风险排查 API 返回的 Data 结构与 Verify 接口类似，但包含更多风险信息
        # 这里只提取部分关键信息，避免Prompt过长
        formatted_data.append(f"企业名称: {qcc_data.get('Name', 'N/A')}")
        formatted_data.append(f"统一社会信用代码: {qcc_data.get('CreditCode', 'N/A')}")
        formatted_data.append(f"法定代表人: {qcc_data.get('OperName', 'N/A')}")
        formatted_data.append(f"登记状态: {qcc_data.get('Status', 'N/A')}")
        formatted_data.append(f"注册资本: {qcc_data.get('RegistCapi', 'N/A')}")
        formatted_data.append(f"成立日期: {qcc_data.get('StartDate', 'N/A')}")
        formatted_data.append(f"注册地址: {qcc_data.get('Address', 'N/A')}")
        formatted_data.append(f"经营范围: {qcc_data.get('Scope', 'N/A')[:200]}...")  # 限制长度
        formatted_data.append(f"参保人数: {qcc_data.get('InsuredCount', 'N/A')}")

        # 提取风险信息
        risk_sections = {
            'ShiXin': '失信被执行人',
            'ZhiXing': '被执行人',
            'AdminPenalty': '行政处罚',
            'Exception': '经营异常',
            'ChattelMortgage': '动产抵押',
            'Liquidation': '清算信息',
            'EquityPledge': '股权出质',
            'SeriousIllegal': '严重违法',
            'EquityFreeze': '股权冻结',
            'JudicialSale': '司法拍卖',
            'Bankruptcy': '破产重整',
            'Sumptuary': '限制高消费',
            'EnvPunishment': '环保处罚',
            'TaxOweNotice': '欠税公告',
            'TaxIllegal': '税收违法',
            'TaxAbnormal': '税务非正常户',
            'TaxHurry': '税务催缴',
            'TaxReminder': '税务催报',
        }
        for key, display_name in risk_sections.items():
            risk_info = qcc_data.get(key)
            if risk_info and risk_info.get('TotalCount') and int(risk_info['TotalCount']) > 0:
                count = risk_info['TotalCount']
                amount = risk_info.get('TotalAmount', '')
                if amount:
                    formatted_data.append(f"{display_name}: 共 {count} 条, 涉案总金额 {amount} 万元")
                else:
                    formatted_data.append(f"{display_name}: 共 {count} 条")
                # 进一步提取DataList中的关键信息，只取1条
                if risk_info.get('DataList') and len(risk_info['DataList']) > 0:
                    first_item = risk_info['DataList'][0]
                    if key == 'ShiXin':
                        formatted_data.append(
                            f"  - 最新失信案号: {first_item.get('CaseNo', 'N/A')}, 金额: {first_item.get('Amount', 'N/A')}元, 履行情况: {first_item.get('ExecuteStatus', 'N/A')}")
                    elif key == 'ZhiXing':
                        formatted_data.append(
                            f"  - 最新被执行案号: {first_item.get('CaseNo', 'N/A')}, 标的: {first_item.get('BiaoDi', 'N/A')}元")
                    elif key == 'AdminPenalty':
                        formatted_data.append(
                            f"  - 最新行政处罚文书号: {first_item.get('DocNo', 'N/A')}, 金额: {first_item.get('PunishAmt', 'N/A')}元")
                    elif key == 'Exception':
                        formatted_data.append(
                            f"  - 最新经营异常原因: {first_item.get('AddReason', 'N/A')}, 列入日期: {first_item.get('AddDate', 'N/A')}")
                    # ... 可以根据需要添加更多详细信息

    elif api_type == 'shixin_check':
        if not qcc_data: return f"未找到与 '{search_key}' 相关的失信信息。"
        formatted_data.append(f"案号: {qcc_data.get('Anno', 'N/A')}")
        formatted_data.append(f"立案日期: {qcc_data.get('Liandate', 'N/A')}")
        formatted_data.append(f"执行法院: {qcc_data.get('Executegov', 'N/A')}")
        formatted_data.append(f"涉案金额: {qcc_data.get('Amount', 'N/A')}元")
        formatted_data.append(f"履行情况: {qcc_data.get('Executestatus', 'N/A')}")
        formatted_data.append(f"失信行为: {qcc_data.get('ActionRemark', 'N/A')}")
        formatted_data.append(f"发布日期: {qcc_data.get('Publicdate', 'N/A')}")

    elif api_type == 'exception_check':
        if not qcc_data: return f"未找到与 '{search_key}' 相关的经营异常信息。"
        formatted_data.append(f"列入原因: {qcc_data.get('AddReason', 'N/A')}")
        formatted_data.append(f"列入日期: {qcc_data.get('AddDate', 'N/A')}")
        formatted_data.append(f"作出决定机关: {qcc_data.get('DecisionOffice', 'N/A')}")
        if qcc_data.get('RomoveReason'):
            formatted_data.append(f"移出原因: {qcc_data.get('RomoveReason', 'N/A')}")
            formatted_data.append(f"移出日期: {qcc_data.get('RemoveDate', 'N/A')}")

    elif api_type == 'zhixing_check':
        if not qcc_data: return f"未找到与 '{search_key}' 相关的被执行信息。"
        formatted_data.append(f"案号: {qcc_data.get('Anno', 'N/A')}")
        formatted_data.append(f"立案时间: {qcc_data.get('Liandate', 'N/A')}")
        formatted_data.append(f"执行法院: {qcc_data.get('ExecuteGov', 'N/A')}")
        formatted_data.append(f"执行标的: {qcc_data.get('Biaodi', 'N/A')}元")
        formatted_data.append(f"疑似申请执行人: {qcc_data.get('SuspectedApplicant', 'N/A')}")

    elif api_type == 'serious_illegal_check':
        if not qcc_data: return f"未找到与 '{search_key}' 相关的严重违法信息。"
        formatted_data.append(f"列入原因: {qcc_data.get('AddReason', 'N/A')}")
        formatted_data.append(f"列入时间: {qcc_data.get('AddDate', 'N/A')}")
        formatted_data.append(f"列入决定机关: {qcc_data.get('AddOffice', 'N/A')}")
        if qcc_data.get('RemoveReason'):
            formatted_data.append(f"移除原因: {qcc_data.get('RemoveReason', 'N/A')}")
            formatted_data.append(f"移除时间: {qcc_data.get('RemoveDate', 'N/A')}")

    elif api_type == 'judgment_doc_check':
        if not qcc_data: return f"未找到与 '{search_key}' 相关的裁决文书信息。"
        formatted_data.append(f"文书标题: {qcc_data.get('CaseName', 'N/A')}")
        formatted_data.append(f"案号: {qcc_data.get('CaseNo', 'N/A')}")
        formatted_data.append(f"案由: {qcc_data.get('CaseReason', 'N/A')}")
        formatted_data.append(f"案件金额: {qcc_data.get('Amount', 'N/A')}元")
        formatted_data.append(f"裁判日期: {qcc_data.get('JudgeDate', 'N/A')}")
        formatted_data.append(f"发布日期: {qcc_data.get('PublishDate', 'N/A')}")
        formatted_data.append(f"是否原告: {'是' if qcc_data.get('IsProsecutor') == 'true' else '否'}")
        formatted_data.append(f"是否被告: {'是' if qcc_data.get('IsDefendant') == 'true' else '否'}")
        if qcc_data.get('PartyList'):
            parties = [f"{p.get('Name', 'N/A')}({p.get('RoleType', 'N/A')})" for p in qcc_data['PartyList'][:3]]
            formatted_data.append(f"当事人: {', '.join(parties)}")
        formatted_data.append(f"裁判结果: {qcc_data.get('JudgeResult', 'N/A')[:200]}...")  # 限制长度

    return "\n".join(formatted_data)


# 辅助函数：格式化模糊搜索数据用于蓝心大模型Prompt (保持不变)
def _format_fuzzy_search_data_for_bluelm_prompt(fuzzy_data_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not fuzzy_data_list:
        return f"未找到与 '{search_key}' 相关的企业。"

    formatted_data = [f"模糊搜索关键词: {search_key}\n找到以下企业（前5条）："]
    for i, data in enumerate(fuzzy_data_list[:5]):
        formatted_data.append(f"--- 企业 {i + 1} ---")
        formatted_data.append(_format_qcc_data_for_bluelm_prompt(data, api_type='fuzzy_search', search_key=search_key))
    return "\n".join(formatted_data)


# 辅助函数：格式化税号开票信息数据用于蓝心大模型Prompt (保持不变)
def _format_tax_invoice_data_for_bluelm_prompt(tax_data):
    return _format_qcc_data_for_bluelm_prompt(tax_data, api_type='tax_invoice')


# 辅助函数：格式化客户身份识别数据用于蓝心大模型Prompt (保持不变)
def _format_kyc_data_for_bluelm_prompt(kyc_data):
    return _format_qcc_data_for_bluelm_prompt(kyc_data, api_type='kyc_verify')


# 辅助函数：格式化资质证书数据用于蓝心大模型Prompt (保持不变)
def _format_certification_data_for_bluelm_prompt(certification_data_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not certification_data_list:
        return f"未找到与 '{search_key}' 相关的资质证书信息。"
    formatted_data = [f"查询关键词: {search_key}\n找到以下资质证书（前3条）："]
    for i, data in enumerate(certification_data_list[:3]):
        formatted_data.append(f"--- 证书 {i + 1} ---")
        formatted_data.append(_format_qcc_data_for_bluelm_prompt(data, api_type='certification'))
    return "\n".join(formatted_data)


# 辅助函数：格式化全国商标查询数据用于蓝心大模型Prompt (保持不变)
def _format_trademark_data_for_bluelm_prompt(trademark_data_list, keyword):
    # ... (与你提供的app.py中相同) ...
    if not trademark_data_list:
        return f"未找到与申请人 '{keyword}' 相关的商标信息。"
    formatted_data = [f"申请人: {keyword}\n找到以下商标（前3条）："]
    for i, data in enumerate(trademark_data_list[:3]):
        formatted_data.append(f"--- 商标 {i + 1} ---")
        formatted_data.append(_format_qcc_data_for_bluelm_prompt(data, api_type='trademark'))
    return "\n".join(formatted_data)


# 辅助函数：格式化专利查询数据用于蓝心大模型Prompt (保持不变)
def _format_patent_data_for_bluelm_prompt(patent_data_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not patent_data_list:
        return f"未找到与 '{search_key}' 相关的专利信息。"
    formatted_data = [f"查询关键词: {search_key}\n找到以下专利（前3条）："]
    for i, data in enumerate(patent_data_list[:3]):
        formatted_data.append(f"--- 专利 {i + 1} ---")
        formatted_data.append(_format_qcc_data_for_bluelm_prompt(data, api_type='patent'))
    return "\n".join(formatted_data)


# 辅助函数：格式化企业年报信息数据用于蓝心大模型Prompt (保持不变)
def _format_annual_report_data_for_bluelm_prompt(annual_report_data_list, key_no):
    # ... (与你提供的app.py中相同) ...
    if not annual_report_data_list:
        return f"未找到与 '{key_no}' 相关的企业年报信息。"
    # 通常年报只取最新一年
    latest_report = annual_report_data_list[0]
    formatted_data = [f"查询关键词: {key_no}\n找到最新企业年报："]
    formatted_data.append(_format_qcc_data_for_bluelm_prompt(latest_report, api_type='annual_report'))
    return "\n".join(formatted_data)


# 辅助函数：格式化失信核查数据用于蓝心大模型Prompt (保持不变)
def _format_shixin_data_for_bluelm_prompt(shixin_data_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not shixin_data_list:
        return f"未找到与 '{search_key}' 相关的失信信息。"
    formatted_data = [f"查询关键词: {search_key}\n找到以下失信信息（前3条）："]
    for i, data in enumerate(shixin_data_list[:3]):
        formatted_data.append(f"--- 失信记录 {i + 1} ---")
        formatted_data.append(_format_qcc_data_for_bluelm_prompt(data, api_type='shixin_check', search_key=search_key))
    return "\n".join(formatted_data)


# 辅助函数：格式化经营异常数据用于蓝心大模型Prompt (保持不变)
def _format_exception_data_for_bluelm_prompt(exception_data_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not exception_data_list:
        return f"未找到与 '{search_key}' 相关的经营异常信息。"
    formatted_data = [f"查询关键词: {search_key}\n找到以下经营异常信息（前3条）："]
    for i, data in enumerate(exception_data_list[:3]):
        formatted_data.append(f"--- 经营异常记录 {i + 1} ---")
        formatted_data.append(
            _format_qcc_data_for_bluelm_prompt(data, api_type='exception_check', search_key=search_key))
    return "\n".join(formatted_data)


# 辅助函数：格式化被执行人数据用于蓝心大模型Prompt (保持不变)
def _format_zhixing_data_for_bluelm_prompt(zhixing_data_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not zhixing_data_list:
        return f"未找到与 '{search_key}' 相关的被执行信息。"
    formatted_data = [f"查询关键词: {search_key}\n找到以下被执行信息（前3条）："]
    for i, data in enumerate(zhixing_data_list[:3]):
        formatted_data.append(f"--- 被执行记录 {i + 1} ---")
        formatted_data.append(_format_qcc_data_for_bluelm_prompt(data, api_type='zhixing_check', search_key=search_key))
    return "\n".join(formatted_data)


# 辅助函数：格式化严重违法数据用于蓝心大模型Prompt (保持不变)
def _format_serious_illegal_data_for_bluelm_prompt(serious_illegal_data_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not serious_illegal_data_list:
        return f"未找到与 '{search_key}' 相关的严重违法信息。"
    formatted_data = [f"查询关键词: {search_key}\n找到以下严重违法信息（前3条）："]
    for i, data in enumerate(serious_illegal_data_list[:3]):
        formatted_data.append(f"--- 严重违法记录 {i + 1} ---")
        formatted_data.append(
            _format_qcc_data_for_bluelm_prompt(data, api_type='serious_illegal_check', search_key=search_key))
    return "\n".join(formatted_data)


# 辅助函数：格式化裁决文书数据用于蓝心大模型Prompt (保持不变)
def _format_judgment_doc_data_for_bluelm_prompt(judgment_doc_list, search_key):
    # ... (与你提供的app.py中相同) ...
    if not judgment_doc_list:
        return f"未找到与 '{search_key}' 相关的裁决文书信息。"
    formatted_data = [f"查询关键词: {search_key}\n找到以下裁决文书信息（前3条）："]
    for i, data in enumerate(judgment_doc_list[:3]):
        formatted_data.append(f"--- 裁决文书 {i + 1} ---")
        formatted_data.append(
            _format_qcc_data_for_bluelm_prompt(data, api_type='judgment_doc_check', search_key=search_key))
    return "\n".join(formatted_data)


@app.route('/')
@login_required  # 要求登录才能访问首页
def index():
    # external_links handled by context processor
    return render_template('index.html')


# --- 认证路由 ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user_role = Role.query.filter_by(name='User').first()  # 默认注册为普通用户
        if not user_role:
            flash('系统错误：默认用户角色未配置。请联系管理员。', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password, role=user_role)
        db.session.add(user)
        db.session.commit()
        flash('您的账户已创建！您现在可以登录了。', 'success')
        # 记录审计日志
        audit_log = AuditLog(user_id=user.id, action='注册', details=f'用户 {user.username} 注册成功',
                             ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('auth/register.html', title='注册', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('您的账户已被禁用。', 'danger')
                logout_user()
                return redirect(url_for('login'))
            login_user(user, remember=form.remember.data)
            # 记录审计日志
            audit_log = AuditLog(user_id=user.id, action='登录', details=f'用户 {user.username} 登录成功',
                                 ip_address=request.remote_addr)
            db.session.add(audit_log)
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('登录失败，请检查用户名和密码。', 'danger')
            # 记录审计日志 (匿名登录失败)
            audit_log = AuditLog(user_id=None, action='登录失败', details=f'尝试登录失败，用户名: {form.username.data}',
                                 ip_address=request.remote_addr)
            db.session.add(audit_log)
            db.session.commit()
    return render_template('auth/login.html', title='登录', form=form)


@app.route('/logout')
@login_required
def logout():
    # 记录审计日志
    audit_log = AuditLog(user_id=current_user.id, action='登出', details=f'用户 {current_user.username} 登出成功',
                         ip_address=request.remote_addr)
    db.session.add(audit_log)
    db.session.commit()
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('index'))


# --- 智慧搜查路由 (需要登录和相应权限) ---
# 为每个智能搜查子模块添加单独的权限
@app.route('/smart_search/q1_qiyexinxihecha', endpoint='q1_qiyexinxihecha')
@login_required
@permission_required('q1_qiyexinxihecha')
def q1_qiyexinxihecha():
    return render_template('smart_search/q1_qiyexinxihecha.html')


@app.route('/smart_search/q1_gongshangxinxi', endpoint='q1_gongshangxinxi')
@login_required
@permission_required('q1_gongshangxinxi')
def q1_gongshangxinxi():
    return render_template('smart_search/q1_gongshangxinxi.html')


@app.route('/smart_search/q1_mohusousuo', endpoint='q1_mohusousuo')
@login_required
@permission_required('q1_mohusousuo')
def q1_mohusousuo():
    return render_template('smart_search/q1_mohusousuo.html')


@app.route('/smart_search/q1_shuihaokaipiao', endpoint='q1_shuihaokaipiao')
@login_required
@permission_required('q1_shuihaokaipiao')
def q1_shuihaokaipiao():
    return render_template('smart_search/q1_shuihaokaipiao.html')


@app.route('/smart_search/q3_zonghefengxianpaizha', endpoint='q3_zonghefengxianpaizha')
@login_required
@permission_required('q3_zonghefengxianpaizha')
def q3_zonghefengxianpaizha():
    return render_template('smart_search/q3_zonghefengxianpaizha.html')


@app.route('/smart_search/q2_kehushenfenshibie', endpoint='q2_kehushenfenshibie')
@login_required
@permission_required('q2_kehushenfenshibie')
def q2_kehushenfenshibie():
    return render_template('smart_search/q2_kehushenfenshibie.html')


@app.route('/smart_search/q2_zizhizhengshu', endpoint='q2_zizhizhengshu')
@login_required
@permission_required('q2_zizhizhengshu')
def q2_zizhizhengshu():
    return render_template('smart_search/q2_zizhizhengshu.html')


@app.route('/smart_search/q2_shangbiaochaxun', endpoint='q2_shangbiaochaxun')
@login_required
@permission_required('q2_shangbiaochaxun')
def q2_shangbiaochaxun():
    return render_template('smart_search/q2_shangbiaochaxun.html')


@app.route('/smart_search/q2_zhuanlichaxun', endpoint='q2_zhuanlichaxun')
@login_required
@permission_required('q2_zhuanlichaxun')
def q2_zhuanlichaxun():
    return render_template('smart_search/q2_zhuanlichaxun.html')


@app.route('/smart_search/q2_nianbaoxinxi', endpoint='q2_nianbaoxinxi')
@login_required
@permission_required('q2_nianbaoxinxi')
def q2_nianbaoxinxi():
    return render_template('smart_search/q2_nianbaoxinxi.html')


# @app.route('/smart_search/q3_zonghefengxianpaizha', endpoint='q3_zonghefengxianpaizha') # This one seems to be removed from the nav, keeping for completeness
# @login_required
# @permission_required('q3_zonghefengxianpaizha')
# def q3_zonghefengxianpaizha():
#     return render_template('smart_search/q3_zonghefengxianpaizha.html')


@app.route('/smart_search/q3_shixinhecha', endpoint='q3_shixinhecha')
@login_required
@permission_required('q3_shixinhecha')
def q3_shixinhecha():
    return render_template('smart_search/q3_shixinhecha.html')


@app.route('/smart_search/q3_jingyinyichanghecha', endpoint='q3_jingyinyichanghecha')
@login_required
@permission_required('q3_jingyinyichanghecha')
def q3_jingyinyichanghecha():
    return render_template('smart_search/q3_jingyinyichanghecha.html')


@app.route('/smart_search/q3_beizhixingrenhecha', endpoint='q3_beizhixingrenhecha')
@login_required
@permission_required('q3_beizhixingrenhecha')
def q3_beizhixingrenhecha():
    return render_template('smart_search/q3_beizhixingrenhecha.html')


@app.route('/smart_search/q3_yanzhongweifahecha', endpoint='q3_yanzhongweifahecha')
@login_required
@permission_required('q3_yanzhongweifahecha')
def q3_yanzhongweifahecha():
    return render_template('smart_search/q3_yanzhongweifahecha.html')


@app.route('/smart_search/q3_caipanwenshuhecha', endpoint='q3_caipanwenshuhecha')
@login_required
@permission_required('q3_caipanwenshuhecha')
def q3_caipanwenshuhecha():
    return render_template('smart_search/q3_caipanwenshuhecha.html')


# --- 智慧搜查路由结束 ---


@app.route('/api/analyze_risk', methods=['POST'])
@login_required
@permission_required('perform_assessment')
def analyze_risk():
    data = request.json
    print(f"Received data from frontend for risk analysis: {data}")

    required_fields = [
        'companyName', 'revenue', 'profitMargin', 'debtRatio', 'cashFlow',
        'marketShare', 'competitors', 'customerChurn',
        'employeeTurnover', 'managementStability', 'innovationAbility',
        'industryRisk', 'policySupport'
    ]
    for field in required_fields:
        if field not in data or data[field] == '':
            return jsonify({'success': False, 'error': f'缺少必要字段或字段为空: {field}'}), 400

    try:
        preliminary_risk_data = calculate_preliminary_risk(data)
        print(f"Preliminary risk calculated: {preliminary_risk_data}")
    except Exception as e:
        print(f"初步风险计算出错: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'数据处理错误，请检查输入格式: {e}'}), 400

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企业风险评估数据进行详细、深入的分析。

    **请严格按照以下两部分结构输出，并确保每部分都有详细内容，不要遗漏：**

    **风险分析报告：**
    ①. **财务风险：** 根据年收入、利润率、负债率、现金流状况进行深入分析。请提供充分的解释和至少一个具体例子。
    ②. **市场风险：** 根据市场份额、竞争对手数量、客户流失率进行深入分析。请提供充分的解释和至少一个具体例子。
    ③. **管理风险：** 根据员工流动率、管理层稳定性、创新能力进行深入分析。请提供充分的解释和至少一个具体例子。
    ④. **外部风险：** 根据行业风险、政策支持进行深入分析。请提供充分的解释和至少一个具体例子。

    **改进建议：**
    ①. **针对财务风险的建议：** 请提供具体可操作的建议，至少2-3行内容，包含具体例子。
    ②. **针对市场风险的建议：** 请提供具体可操作的建议，至少2-3行内容，包含具体例子。
    ③. **针对管理风险的建议：** 请提供具体可操作的建议，至少2-3行内容，包含具体例子。
    ④. **针对外部风险的建议：** 请提供具体可操作的建议，至少2-3行内容，包含具体例子。

    ---
    企业数据：
    公司名称：{data.get('companyName', '未知企业')}
    年收入：{data.get('revenue', '未知')} 万元
    利润率：{data.get('profitMargin', '未知')} %
    负债率：{data.get('debtRatio', '未知')} %
    现金流状况：{data.get('cashFlow', '未知')}
    市场份额：{data.get('marketShare', '未知')} %
    竞争对手数量：{data.get('competitors', '未知')}
    客户流失率：{data.get('customerChurn', '未知')} %
    员工流动率：{data.get('employeeTurnover', '未知')} %
    管理层稳定性：{data.get('managementStability', '未知')}
    创新能力：{data.get('innovationAbility', '未知')}
    行业风险：{data.get('industryRisk', '未知')}
    政策支持：{data.get('policySupport', '未知')}

    初步风险评估得分（0-100分，分数越高风险越高）：
    总风险评分：{preliminary_risk_data['total']}
    财务风险得分：{preliminary_risk_data['financial']}
    市场风险得分：{preliminary_risk_data['market']}
    管理风险得分：{preliminary_risk_data['management']}
    外部风险得分：{preliminary_risk_data['external']}
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 2048
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        # 动态获取蓝心大模型API密钥
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID  # Fallback to config
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY  # Fallback to config

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        print(f"Sending request to BlueLM: {url} with headers: {headers} and data: {api_data}")
        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        res_obj = response.json()
        print(f"Received response from BlueLM: {res_obj}")

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            # Determine risk level text for storage
            total_risk_score = preliminary_risk_data['total']
            risk_level_text = '低风险'
            if total_risk_score >= 70:
                risk_level_text = '高风险'
            elif total_risk_score >= 40:
                risk_level_text = '中风险'

            # Store in database
            new_record = AuditLog(
                user_id=current_user.id,
                action='执行风险评估',
                details=json.dumps({
                    'type': 'assessment',
                    'input_data': data,
                    'preliminary_risk': preliminary_risk_data,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html,
                    'company_name': data.get('companyName', '未知企业'),
                    'risk_level_text': risk_level_text
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'totalRisk': preliminary_risk_data['total'],
                'financialRisk': preliminary_risk_data['financial'],
                'marketRisk': preliminary_risk_data['market'],
                'managementRisk': preliminary_risk_data['management'],
                'externalRisk': preliminary_risk_data['external'],
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)  # Return the ID from database
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            print(f"蓝心大模型返回错误: code={res_obj.get('code')}, msg={error_msg}")
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except requests.exceptions.Timeout:
        print("请求蓝心大模型 API 超时。")
        return jsonify({'success': False, 'error': '请求蓝心大模型 API 超时，请稍后再试。'}), 504
    except requests.exceptions.ConnectionError:
        print("无法连接到蓝心大模型 API。")
        return jsonify({'success': False, 'error': '无法连接到蓝心大模型 API，请检查网络连接。'}), 503
    except requests.exceptions.HTTPError as e:
        print(f'请求蓝心大模型 API 返回 HTTP 错误: {e.response.status_code} - {e.response.text}')
        return jsonify(
            {'success': False, 'error': f'蓝心大模型 API 返回错误: {e.response.status_code}'}), e.response.status_code
    except Exception as e:
        print(f'服务器内部错误: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'服务器内部错误: {e}'}), 500


@app.route('/api/dashboard_stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    # 从数据库获取评估记录
    all_assessment_logs = AuditLog.query.filter_by(action='执行风险评估').all()

    total_assessments = len(all_assessment_logs)
    today = datetime.date.today()
    today_assessments = 0
    high_risk_count = 0
    low_risk_count = 0
    medium_risk_count = 0
    total_risk_score_sum = 0

    for log in all_assessment_logs:
        record_data = json.loads(log.details)
        if record_data.get('type') == 'assessment':  # 确保是评估类型
            record_timestamp = log.timestamp
            preliminary_risk = record_data.get('preliminary_risk', {})
            total_risk_score = preliminary_risk.get('total', 0)

            if record_timestamp.date() == today:
                today_assessments += 1

            total_risk_score_sum += total_risk_score

            if total_risk_score >= 70:
                high_risk_count += 1
            elif total_risk_score >= 40:
                medium_risk_count += 1
            else:
                low_risk_count += 1

    avg_total_risk = round(total_risk_score_sum / total_assessments) if total_assessments > 0 else 0

    return jsonify({
        'totalAssessments': total_assessments,
        'todayAssessments': today_assessments,
        'highRiskCount': high_risk_count,
        'avgTotalRisk': avg_total_risk,
        'riskDistribution': {
            'low': low_risk_count,
            'medium': medium_risk_count,
            'high': high_risk_count
        }
    })


@app.route('/api/recent_assessments', methods=['GET'])
@login_required
def get_recent_assessments():
    # 从数据库获取最近的评估记录
    recent_assessment_logs = AuditLog.query.filter_by(action='执行风险评估').order_by(AuditLog.timestamp.desc()).limit(
        5).all()

    formatted_records = []
    for log in recent_assessment_logs:
        record_data = json.loads(log.details)
        if record_data.get('type') == 'assessment':
            company_name = record_data.get('company_name', '未知企业')
            risk_level_text = record_data.get('risk_level_text', 'N/A')
            total_risk_score = record_data.get('preliminary_risk', {}).get('total', 0)

            color = 'var(--success-color)'
            if total_risk_score >= 70:
                color = 'var(--danger-color)'
            elif total_risk_score >= 40:
                color = 'var(--warning-color)'

            formatted_records.append({
                'id': str(log.id),
                'companyName': company_name,
                'riskLevel': risk_level_text,
                'riskColor': color,
                'time': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'assessment'  # 明确类型
            })
    return jsonify(formatted_records)


# 新增：获取所有历史评估记录，可筛选 (针对仪表盘评估)
@app.route('/api/history/assessments', methods=['GET'])
@login_required
@permission_required('view_assessment_report')  # Changed to specific permission
def get_history_assessments():
    search_query = request.args.get('query', '').lower()

    # 从数据库获取评估记录
    all_assessment_logs = AuditLog.query.filter_by(action='执行风险评估').order_by(AuditLog.timestamp.desc()).all()

    filtered_records = []
    for log in all_assessment_logs:
        record_data = json.loads(log.details)
        if record_data.get('type') == 'assessment':
            company_name = record_data.get('company_name', '未知企业')
            if search_query in company_name.lower():
                risk_level_text = record_data.get('risk_level_text', 'N/A')
                total_risk_score = record_data.get('preliminary_risk', {}).get('total', 0)

                color = 'var(--success-color)'
                if total_risk_score >= 70:
                    color = 'var(--danger-color)'
                elif total_risk_score >= 40:
                    color = 'var(--warning-color)'

                filtered_records.append({
                    'id': str(log.id),
                    'companyName': company_name,
                    'riskLevel': risk_level_text,
                    'riskColor': color,
                    'time': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'assessment'
                })
    return jsonify(filtered_records)


# 辅助函数：获取企查查历史记录的通用逻辑
def _get_qcc_history_records(action_type, permission_name):
    search_query = request.args.get('query', '').lower()

    # Apply permission check here as well for API access
    if not current_user.is_authenticated or not current_user.role or not any(
            p.name == permission_name for p in current_user.role.permissions):
        return jsonify({'error': '您没有足够的权限访问此历史记录。'}), 403

    # 从数据库获取所有相关操作日志
    all_qcc_logs = AuditLog.query.filter_by(action=action_type).order_by(AuditLog.timestamp.desc()).all()

    filtered_records = []
    for log in all_qcc_logs:
        record_data = json.loads(log.details)
        company_name = record_data.get('company_name', '未知企业')

        # 对于模糊搜索，company_name 可能是 "模糊搜索: keyword"
        # 对于其他，company_name 是实际公司名
        if search_query in company_name.lower():
            # For QCC verify, we don't have a direct 'totalRisk' score,
            # so we might infer it from AI analysis or just show '已分析'
            risk_level = '已分析'
            color = 'var(--info-color)'  # Neutral color for analyzed

            filtered_records.append({
                'id': str(log.id),
                'companyName': company_name,
                'riskLevel': risk_level,
                'riskColor': color,
                'time': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'type': record_data.get('type', 'unknown')  # 明确类型
            })
    return jsonify(filtered_records)


# 新增：获取企业信息核验历史记录
@app.route('/api/history/qcc_verify', methods=['GET'])
@login_required
@permission_required('q1_qiyexinxihecha')  # Specific permission
def get_history_qcc_verify():
    return _get_qcc_history_records('执行企查查核验', 'q1_qiyexinxihecha')


# 新增：获取企业工商信息历史记录
@app.route('/api/history/industrial_info', methods=['GET'])
@login_required
@permission_required('q1_gongshangxinxi')  # Specific permission
def get_history_industrial_info():
    return _get_qcc_history_records('执行企业工商信息查询', 'q1_gongshangxinxi')


# 新增：获取企业模糊搜索历史记录
@app.route('/api/history/fuzzy_search', methods=['GET'])
@login_required
@permission_required('q1_mohusousuo')  # Specific permission
def get_history_fuzzy_search():
    return _get_qcc_history_records('执行企业模糊搜索', 'q1_mohusousuo')


# 新增：获取税号开票信息历史记录
@app.route('/api/history/tax_invoice', methods=['GET'])
@login_required
@permission_required('q1_shuihaokaipiao')  # Specific permission
def get_history_tax_invoice():
    return _get_qcc_history_records('执行税号开票信息查询', 'q1_shuihaokaipiao')


# 新增：获取客户身份识别历史记录
@app.route('/api/history/kyc_verify', methods=['GET'])
@login_required
@permission_required('q2_kehushenfenshibie')  # Specific permission
def get_history_kyc_verify():
    return _get_qcc_history_records('执行客户身份识别查询', 'q2_kehushenfenshibie')


# 新增：获取资质证书历史记录
@app.route('/api/history/certification', methods=['GET'])
@login_required
@permission_required('q2_zizhizhengshu')  # Specific permission
def get_history_certification():
    return _get_qcc_history_records('执行资质证书查询', 'q2_zizhizhengshu')


# 新增：获取全国商标查询历史记录
@app.route('/api/history/trademark', methods=['GET'])
@login_required
@permission_required('q2_shangbiaochaxun')  # Specific permission
def get_history_trademark():
    return _get_qcc_history_records('执行全国商标查询', 'q2_shangbiaochaxun')


# 新增：获取专利查询历史记录
@app.route('/api/history/patent', methods=['GET'])
@login_required
@permission_required('q2_zhuanlichaxun')  # Specific permission
def get_history_patent():
    return _get_qcc_history_records('执行专利查询', 'q2_zhuanlichaxun')


# 新增：获取企业年报信息历史记录
@app.route('/api/history/annual_report', methods=['GET'])
@login_required
@permission_required('q2_nianbaoxinxi')  # Specific permission
def get_history_annual_report():
    return _get_qcc_history_records('执行企业年报信息查询', 'q2_nianbaoxinxi')


@app.route('/api/history/comprehensive_risk', methods=['GET'])
@login_required
@permission_required('q3_zonghefengxianpaizha')
def get_history_comprehensive_risk():
    return _get_qcc_history_records('执行综合风险排查', 'q3_zonghefengxianpaizha')


# 新增：获取失信核查历史记录
@app.route('/api/history/shixin_check', methods=['GET'])
@login_required
@permission_required('q3_shixinhecha')  # Specific permission
def get_history_shixin_check():
    return _get_qcc_history_records('执行失信核查', 'q3_shixinhecha')


# 新增：获取经营异常核查历史记录
@app.route('/api/history/exception_check', methods=['GET'])
@login_required
@permission_required('q3_jingyinyichanghecha')  # Specific permission
def get_history_exception_check():
    return _get_qcc_history_records('执行经营异常核查', 'q3_jingyinyichanghecha')


# 新增：获取被执行人核查历史记录
@app.route('/api/history/zhixing_check', methods=['GET'])
@login_required
@permission_required('q3_beizhixingrenhecha')  # Specific permission
def get_history_zhixing_check():
    return _get_qcc_history_records('执行被执行人核查', 'q3_beizhixingrenhecha')


# 新增：获取严重违法核查历史记录
@app.route('/api/history/serious_illegal_check', methods=['GET'])
@login_required
@permission_required('q3_yanzhongweifahecha')  # Specific permission
def get_history_serious_illegal_check():
    return _get_qcc_history_records('执行严重违法核查', 'q3_yanzhongweifahecha')


# 新增：获取裁决文书核查历史记录
@app.route('/api/history/judgment_doc_check', methods=['GET'])
@login_required
@permission_required('q3_caipanwenshuhecha')  # Specific permission
def get_history_judgment_doc_check():
    return _get_qcc_history_records('执行裁决文书核查', 'q3_caipanwenshuhecha')


# 新增：详细报告页面路由 (现在也支持所有 QCC 报告)
@app.route('/report/<int:record_id>')  # 修改为 int 类型，因为数据库ID是整数
@login_required
@permission_required('view_assessment_report')  # Changed to specific permission
def view_report(record_id):
    audit_log = AuditLog.query.get(record_id)
    if not audit_log:
        return "报告未找到", 404

    # 确保用户只能查看自己的报告，或者管理员可以查看所有报告
    if audit_log.user_id != current_user.id and not (current_user.role and current_user.role.name == 'Admin'):
        flash('您没有权限查看此报告。', 'danger')
        abort(403)

    record_data = json.loads(audit_log.details)
    report_type = record_data.get('type', 'unknown')

    # 将 AuditLog 的 timestamp 传递给模板
    record_data['timestamp'] = audit_log.timestamp

    return render_template('report.html', record=record_data, key_map=INPUT_DATA_KEY_MAP, report_type=report_type)


@app.route('/api/qichacha/verify_and_analyze', methods=['POST'])
@login_required
@permission_required('q1_qiyexinxihecha')  # Specific permission
def qichacha_verify_and_analyze():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM')

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    qcc_data = verify_enterprise_info(search_key)

    if not qcc_data:
        return jsonify({'success': False, 'error': '未查询到企业信息，请检查关键词或稍后再试。'}), 404

    formatted_qcc_data_for_prompt = _format_qcc_data_for_bluelm_prompt(qcc_data, api_type='verify')

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查企业信息核验数据，对企业进行全面、深入的风险分析，并提供具体、可操作的改进建议。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm if company_name_for_bluelm else qcc_data.get('Name', '未知')}

    企查查核验数据（已精简）：
    {formatted_qcc_data_for_prompt}

    风险分析报告：
    ①. **注册信息与合规风险分析：** [具体风险描述，例如：注册资本与实缴资本差异大，可能存在资金链风险。这可能导致公司在运营中面临潜在的融资困难，尤其是在需要大额资金投入的项目上，会增加财务不确定性。]
    ②. **经营状况与市场风险分析：** [具体风险描述，例如：人员规模或参保人数与企业规模不匹配，可能存在用工风险或经营不善。例如，如果注册资本很高但参保人数很少，可能表明企业实际运营规模小，存在“空壳公司”的风险，或未能足额为员工缴纳社保。]
    ③. **股权结构与管理风险分析：** [具体风险描述，例如：股权结构复杂或集中度过高，可能存在公司治理风险。复杂的股权结构可能导致决策效率低下，股东之间容易产生纠纷；过度集中的股权则可能导致“一股独大”，损害中小股东利益，甚至出现内部控制失衡。]
    ④. **其他潜在风险：** [根据数据中未被前三点覆盖但值得关注的风险点进行分析，例如：曾用名频繁变更、联系方式异常等。]

    改进建议：
    ①. **针对注册信息与合规风险的建议：** [具体可操作的建议，例如：核实注册资本到位情况，并根据实际经营情况调整经营范围。确保注册资本真实到位，增强公司财务实力；同时，定期审查并优化经营范围，聚焦核心业务，避免不必要的合规风险。]
    ②. **针对经营状况与市场风险的建议：** [具体可操作的建议，例如：优化人员结构，提高人均产出，关注行业发展趋势，进行市场多元化布局。通过精简管理层级、提升员工技能培训、引入自动化技术等方式提高效率；同时，密切关注市场动态，适时拓展新的客户群体和销售渠道。]
    ③. **针对股权结构与管理风险的建议：** [具体可操作的建议，例如：优化股权结构，引入战略投资者，完善公司治理机制。通过股权激励、引入外部董事等方式，平衡各方利益，提升决策的科学性和透明度；建立有效的董事会和监事会，发挥其监督作用。]
    ④. **综合风险管理建议：** [提供全面的风险管理策略，例如：建立风险预警系统、加强信息披露、定期进行风险评估等。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        # 动态获取蓝心大模型API密钥
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        print(f"Sending QCC-based request to BlueLM: {url} with headers: {headers}")
        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()
        print(f"Received QCC-based response from BlueLM: {res_obj}")

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']

            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            # Store in database
            new_record = AuditLog(
                user_id=current_user.id,
                action='执行企查查核验',
                details=json.dumps({
                    'type': 'qcc_verify',
                    'search_key': search_key,
                    'company_name': qcc_data.get('Name', search_key),
                    'qcc_data': qcc_data,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'qccData': qcc_data,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            print(f"蓝心大模型返回错误 (QCC场景): code={res_obj.get('code')}, msg={error_msg}")
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except requests.exceptions.Timeout:
        print("请求蓝心大模型 API 超时 (QCC场景)。")
        return jsonify({'success': False, 'error': '请求蓝心大模型 API 超时，请稍后再试。'}), 504
    except requests.exceptions.ConnectionError:
        print("无法连接到蓝心大模型 API (QCC场景)。")
        return jsonify({'success': False, 'error': '无法连接到蓝心大模型 API，请检查网络连接。'}), 503
    except requests.exceptions.HTTPError as e:
        print(f'请求蓝心大模型 API 返回 HTTP 错误 (QCC场景): {e.response.status_code} - {e.response.text}')
        return jsonify(
            {'success': False, 'error': f'蓝心大模型 API 返回错误: {e.response.status_code}'}), e.response.status_code
    except Exception as e:
        print(f'服务器内部错误 (QCC场景): {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'服务器内部错误: {e}'}), 500


# --- 新增企查查 API 路由和 AI 分析 (都修改为存储到数据库) ---

# 企业工商信息查询
@app.route('/api/qichacha/industrial_info', methods=['POST'])
@login_required
@permission_required('q1_gongshangxinxi')  # Specific permission
def industrial_info_query():
    data = request.json
    keyword = data.get('keyword')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or keyword

    if not keyword:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    qcc_data = get_basic_details_by_name(keyword)

    if not qcc_data:
        return jsonify({'success': False, 'error': '未查询到企业工商信息，请检查关键词或稍后再试。'}), 404

    formatted_qcc_data_for_prompt = _format_qcc_data_for_bluelm_prompt(qcc_data, api_type='industrial_info')

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查企业工商信息数据，对企业进行全面、深入的风险分析，并提供具体、可操作的改进建议。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查工商信息数据：
    {formatted_qcc_data_for_prompt}

    风险分析报告：
    ①. **基本信息合规风险：** [分析企业名称、统一社会信用代码、法定代表人、登记状态、成立日期等是否存在异常或潜在风险。例如，如果登记状态为“注销”或“吊销”，则企业已停止运营，存在巨大合作风险。]
    ②. **注册资本与实缴风险：** [分析注册资本、实缴资本、注册地址等信息，评估是否存在“空壳公司”风险或资金实力不足。例如，注册资本很高但实缴资本很低，可能意味着企业实际资金实力不足，存在履约风险。]
    ③. **经营范围与行业风险：** [分析经营范围是否清晰、是否包含高风险行业，以及营业期限等。例如，经营范围过广可能导致企业在不熟悉的领域盲目扩张，增加合规风险。]
    ④. **历史变更与潜在风险：：** [分析曾用名、注销吊销信息等历史数据，判断企业是否存在经营不稳定或规避责任的倾向。例如，频繁变更名称可能暗示企业存在不良历史记录或试图规避债务。]

    改进建议：
    ①. **针对基本信息合规的建议：** [例如，确保企业登记信息与实际经营状况一致，及时更新工商变更信息。]
    ②. **针对资本与财务风险的建议：：** [例如，根据业务发展需要，逐步增加实缴资本，提升企业信用；合理规划资金使用，避免过度依赖注册资本。]
    ③. **针对经营与行业风险的建议：** [例如，聚焦核心经营范围，避免盲目扩张；深入研究行业政策和市场趋势，提前预警并规避风险。]
    ④. **针对历史风险管理的建议：** [例如，保持企业信息的透明度，避免频繁变更关键信息；建立完善的档案管理制度，确保历史记录可追溯。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行企业工商信息查询',
                details=json.dumps({
                    'type': 'industrial_info',
                    'keyword': keyword,
                    'company_name': qcc_data.get('Name', keyword),
                    'qcc_data': qcc_data,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'qccData': qcc_data,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 企业模糊搜索
@app.route('/api/qichacha/fuzzy_search', methods=['POST'])
@login_required
@permission_required('q1_mohusousuo')  # Specific permission
def fuzzy_search_query():
    data = request.json
    search_key = data.get('searchKey')

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词'}), 400

    qcc_data_list = fuzzy_search_companies(search_key)

    if not qcc_data_list:
        return jsonify({'success': False, 'error': '未查询到相关企业信息，请检查关键词或稍后再试。'}), 404

    formatted_qcc_data_for_prompt = _format_fuzzy_search_data_for_bluelm_prompt(qcc_data_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查企业模糊搜索结果，对搜索到的企业（如果有多条，请综合分析前几条）进行潜在风险分析，并提供搜索策略和进一步核实的建议。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    搜索关键词：{search_key}

    企查查模糊搜索结果：
    {formatted_qcc_data_for_prompt}

    风险分析报告：
    ①. **匹配度与准确性风险：** [分析搜索结果与关键词的匹配程度，以及是否存在大量不相关或名称相似的企业，可能导致误判。例如，搜索“科技公司”可能返回大量同名或类似名称的企业，需要仔细甄别其注册地址、法定代表人等信息以确认目标。]
    ②. **企业状态与经营风险：** [分析搜索结果中企业的登记状态（如存续、注销、吊销），判断是否存在已停止运营或异常的企业。例如，如果搜索结果中包含大量已注销或吊销的企业，可能反映该关键词对应的行业或区域存在较高风险。]
    ③. **信息完整性与核实风险：** [分析模糊搜索结果中信息的完整性（如缺乏统一社会信用代码、成立日期），提示进一步核实的必要性。例如，模糊搜索结果通常不包含详细的经营范围或股权信息，需要通过更精确的查询接口进行补充核实。]
    ④. **潜在关联风险：** [如果搜索结果中出现多个关联企业或同名企业，分析其潜在的关联风险或混淆风险。例如，同一法定代表人名下有多家企业，需要警惕其业务关联性和风险传导。]

    改进建议：
    ①. **优化搜索策略：** [例如，结合统一社会信用代码、法定代表人姓名、注册地址等更精确的关键词进行组合搜索，缩小范围。]
    ②. **多维度信息核实：** [例如，对于模糊搜索到的企业，应进一步通过“企业信息核验”或“企业工商信息”接口获取详细数据，进行交叉验证。]
    ③. **关注异常状态企业：** [例如，对搜索结果中显示“注销”、“吊销”、“经营异常”的企业，应立即排除或进行深度风险排查。]
    ④. **建立企业画像：** [例如，结合多个查询结果，构建完整的企业画像，包括其股权结构、对外投资、法律诉讼等，进行全面风险评估。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行企业模糊搜索',
                details=json.dumps({
                    'type': 'fuzzy_search',
                    'search_key': search_key,
                    'company_name': f"模糊搜索: {search_key}",
                    'qcc_data_list': qcc_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'qccDataList': qcc_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 税号开票信息
@app.route('/api/qichacha/tax_invoice', methods=['POST'])
@login_required
@permission_required('q1_shuihaokaipiao')  # Specific permission
def tax_invoice_query():
    data = request.json
    keyword = data.get('keyword')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or keyword

    if not keyword:
        return jsonify({'success': False, 'error': '请输入查询关键字（公司名称）'}), 400

    qcc_data = get_tax_invoice_info(keyword)

    if not qcc_data:
        return jsonify({'success': False, 'error': '未查询到税号开票信息，请检查公司名称或稍后再试。'}), 404

    formatted_qcc_data_for_prompt = _format_tax_invoice_data_for_bluelm_prompt(qcc_data)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查税号开票信息，对企业进行潜在财务风险和合规风险分析，并提供具体的核实建议。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查税号开票信息：
    {formatted_qcc_data_for_prompt}

    风险分析报告：
    ①. **信息一致性风险：** [分析开票信息中的企业名称、统一社会信用代码、地址、电话与企业其他公开信息是否一致。例如，如果开票信息与工商注册信息不符，可能存在虚假开票或税务欺诈风险。]
    ②. **银行账户异常风险：** [分析开户行和开户行账号是否存在异常或频繁变更。例如，如果开户行或账号与常规经营不符，可能暗示资金流向存在问题或企业经营不稳定。]
    ③. **企业状态与合规风险：** [结合企业状态（如存续、注销）分析其开票资质。例如，已注销的企业仍在提供开票信息，可能涉及违法行为。]
    ④. **税务合规性风险：** [根据纳税人识别号和企业类型，分析其潜在的税务合规风险。例如，小微企业享受税收优惠，但如果其经营规模超出范围，可能面临税务追溯风险。]

    改进建议：
    ①. **核对信息一致性：** [例如，务必将开票信息与工商信息、银行流水等进行多方核对，确保信息真实有效。]
    ②. **监控银行账户：** [例如，定期核查合作企业的开户行和账号，对于异常变动及时进行风险评估和沟通。]
    ③. **关注企业经营状态：** [例如，在业务往来前，核实企业的最新经营状态，避免与异常企业进行交易。]
    ④. **加强税务风险管理：** [例如，建议企业定期进行税务自查，确保开票行为和税务申报符合国家规定，避免税务风险。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行税号开票信息查询',
                details=json.dumps({
                    'type': 'tax_invoice',
                    'keyword': keyword,
                    'company_name': qcc_data.get('Name', keyword),
                    'qcc_data': qcc_data,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'qccData': qcc_data,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：客户身份识别 API 路由和 AI 分析
@app.route('/api/qichacha/kyc_verify', methods=['POST'])
@login_required
@permission_required('q2_kehushenfenshibie')  # Specific permission
def kyc_verify_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    kyc_data = get_kyc_info(search_key)

    if not kyc_data:
        return jsonify({'success': False, 'error': '未查询到客户身份识别信息，请检查关键词或稍后再试。'}), 404

    formatted_kyc_data_for_prompt = _format_kyc_data_for_bluelm_prompt(kyc_data)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查客户身份识别（KYC）数据，对企业进行全面、深入的风险分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查客户身份识别（KYC）数据：
    {formatted_kyc_data_for_prompt}

    风险分析报告：
    ①. **身份真实性与合规风险：** [分析企业名称、统一社会信用代码、法定代表人、登记状态等核心信息，判断是否存在虚假注册、冒用身份或与实际不符的情况。例如，如果企业登记状态为“注销”或“吊销”，则其身份已失效，存在严重的合规风险。]
    ②. **股权结构与实际控制人风险：** [分析股东信息、实际控制人等，评估股权穿透后的最终受益人，判断是否存在股权代持、多层嵌套或实际控制人不明等风险。例如，复杂的股权结构可能被用于隐藏资金来源或规避监管，增加洗钱或关联交易的风险。]
    ③. **经营范围与业务匹配风险：** [核查经营范围与实际业务是否匹配，判断是否存在超范围经营或涉及高风险业务。例如，如果企业经营范围与所申请的业务不符，可能存在欺诈风险或业务能力不足。]
    ④. **历史沿革与声誉风险：** [分析曾用名、变更信息、注销吊销信息等历史数据，判断企业是否存在频繁变更、不良记录或负面舆情。例如，频繁的企业名称变更可能暗示企业试图规避历史债务或法律责任，损害其市场声誉。]

    改进建议：
    ①. **加强身份信息核实：** [例如，通过多方交叉验证企业核心信息，包括工商档案、税务登记、银行开户信息等，确保身份真实有效。对于关键人员（如法定代表人、实际控制人），应进行背景调查。]
    ②. **深入股权穿透分析：** [例如，利用专业工具进行股权穿透，识别最终受益所有人，并对复杂股权结构进行风险评估。对于存在代持或多层嵌套的情况，要求提供补充说明和相关协议。]
    ③. **严格业务范围审查：** [例如，核查企业经营范围与申请业务的匹配度，对于超出经营范围的业务请求应拒绝或要求补充相关资质。定期复核业务开展情况，确保符合经营许可。]
    ④. **持续风险监控与预警：** [例如，建立客户全生命周期风险监控机制，定期对企业的工商变更、法律诉讼、行政处罚、负面舆情等信息进行跟踪和预警。对于发现的异常情况，及时启动风险处置流程。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行客户身份识别查询',
                details=json.dumps({
                    'type': 'kyc_verify',
                    'search_key': search_key,
                    'company_name': kyc_data.get('Name', search_key),
                    'kyc_data': kyc_data,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'kycData': kyc_data,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：资质证书 API 路由和 AI 分析
@app.route('/api/qichacha/certification', methods=['POST'])
@login_required
@permission_required('q2_zizhizhengshu')  # Specific permission
def certification_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（公司名称）'}), 400

    certification_data_list = search_certification(search_key)

    if not certification_data_list:
        return jsonify({'success': False, 'error': '未查询到资质证书信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_certification_data_for_bluelm_prompt(certification_data_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查资质证书数据，对企业进行潜在的合规风险、经营风险和声誉风险分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查资质证书数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **资质有效性与合规风险：** [分析证书的有效期限和状态，判断是否存在过期、无效或即将到期的资质证书，可能导致企业经营不合规。例如，如果核心业务所需的资质证书已过期，企业可能面临停业整顿、罚款甚至吊销营业执照的风险。]
    ②. **资质完整性与业务匹配风险：** [评估企业拥有的资质证书是否完整覆盖其所有经营业务，判断是否存在关键业务无相应资质的情况。例如，如果企业从事建筑工程，但缺乏相应的施工资质，则其承接的项目可能存在非法施工风险。]
    ③. **资质数量与竞争力风险：** [分析企业资质证书的数量和质量，判断其在行业中的竞争力和专业水平。例如，如果同行业竞争对手拥有更多高级别或稀缺资质，则该企业在市场竞争中可能处于劣势。]
    ④. **发证机构与声誉风险：** [核查发证机构的权威性和证书的真实性，判断是否存在虚假证书或非正规机构颁发的证书。例如，如果证书由非官方或声誉不佳的机构颁发，可能影响企业在客户和合作伙伴心中的信任度。]

    改进建议：
    ①. **建立资质管理体系：** [例如，建立完善的资质证书管理体系，定期审查所有证书的有效期限和状态，提前进行续期或更新。指派专人负责资质管理，确保合规运营。]
    ②. **补齐关键业务资质：** [例如，对照企业经营范围和实际业务，梳理所需的各项资质证书，并制定计划逐步申请和获取缺失的关键资质。]
    ③. **提升资质等级与数量：** [例如，鼓励企业积极申请更高级别或更多种类的资质证书，以提升市场竞争力和业务拓展能力。]
    ④. **加强资质真实性核查：** [例如，对所有资质证书进行真实性核查，确保其由合法、权威机构颁发。对于存疑的证书，应立即进行核实并采取相应措施。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行资质证书查询',
                details=json.dumps({
                    'type': 'certification',
                    'search_key': search_key,
                    'company_name': company_name_for_bluelm,
                    'certification_data_list': certification_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'certificationDataList': certification_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：全国商标查询 API 路由和 AI 分析
@app.route('/api/qichacha/trademark', methods=['POST'])
@login_required
@permission_required('q2_shangbiaochaxun')  # Specific permission
def trademark_query():
    data = request.json
    keyword = data.get('keyword')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or keyword

    if not keyword:
        return jsonify({'success': False, 'error': '请输入申请人名称'}), 400

    trademark_data_list = search_trademark_by_applicant(keyword)

    if not trademark_data_list:
        return jsonify({'success': False, 'error': '未查询到相关商标信息，请检查申请人名称或稍后再试。'}), 404

    formatted_data_for_prompt = _format_trademark_data_for_bluelm_prompt(trademark_data_list, keyword)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查全国商标查询数据，对企业的知识产权风险、市场竞争力风险和声誉风险进行分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查全国商标查询数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **商标保护完整性风险：** [分析企业拥有的商标数量、类别覆盖范围和注册状态，判断是否存在核心品牌未注册、注册类别不全或商标被抢注的风险。例如，如果企业主营业务的关键商标在相关国际分类下未注册，可能导致品牌被侵权，损害市场份额。]
    ②. **商标侵权与法律风险：** [核查是否存在与竞争对手商标高度相似或容易引起混淆的商标，判断是否存在潜在的商标侵权纠纷。例如，如果企业使用的商标与现有知名商标过于接近，可能面临法律诉讼和巨额赔偿。]
    ③. **商标活跃度与市场风险：** [分析商标的申请日期、状态和使用情况，判断企业在品牌建设和市场推广方面的投入和策略。例如，长期不使用或状态异常的商标可能反映企业品牌战略不清晰或市场运营不力。]
    ④. **商标资产价值风险：** [评估商标作为无形资产的价值和保护力度，判断是否存在因商标管理不善导致资产贬值或流失的风险。例如，缺乏有效维护和推广的商标，其品牌价值可能难以提升，甚至面临被撤销的风险。]

    改进建议：
    ①. **完善商标布局策略：** [例如，对核心品牌进行多类别、全方位的注册保护，并定期审查商标组合，及时补充注册新业务或新产品所需的商标。]
    ②. **加强商标监测与维权：** [例如，建立商标监测系统，定期对市场上的近似商标进行排查，对于侵权行为及时采取法律手段进行维权。]
    ③. **提升品牌管理与运营：** [例如，积极推广和使用已注册商标，提升品牌知名度和美誉度。对于闲置商标，应考虑转让、授权或及时注销，避免资源浪费。]
    ④. **定期进行商标价值评估：** [例如，将商标作为重要的无形资产进行管理，定期评估其市场价值，并将其纳入企业整体风险管理体系。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行全国商标查询',
                details=json.dumps({
                    'type': 'trademark',
                    'keyword': keyword,
                    'company_name': company_name_for_bluelm,
                    'trademark_data_list': trademark_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'trademarkDataList': trademark_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：专利查询 API 路由和 AI 分析
@app.route('/api/qichacha/patent', methods=['POST'])
@login_required
@permission_required('q2_zhuanlichaxun')  # Specific permission
def patent_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入查询关键字（公司名称或专利名称）'}), 400

    patent_data_list = search_patent(search_key)

    if not patent_data_list:
        return jsonify({'success': False, 'error': '未查询到相关专利信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_patent_data_for_bluelm_prompt(patent_data_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查专利查询数据，对企业的知识产权风险、技术创新风险和市场竞争风险进行分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查专利查询数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **专利保护完整性风险：** [分析企业拥有的专利数量、类型（发明、实用新型、外观设计）和保护范围，判断是否存在核心技术未申请专利或专利保护不足的风险。例如，如果企业的重要技术仅申请了实用新型专利，其保护力度可能弱于发明专利，易被模仿。]
    ②. **专利侵权与法律风险：** [核查是否存在与竞争对手专利相似或可能引起侵权的专利，判断是否存在潜在的专利纠纷。例如，如果企业的产品或技术与他人已有的专利存在重叠，可能面临专利侵权诉讼和高额赔偿。]
    ③. **专利技术创新风险：** [分析专利的申请日期、公开日期和法律状态，判断企业在技术创新方面的活跃度和专利技术的先进性。例如，如果企业长期没有新的专利申请，可能表明其研发投入不足或创新能力停滞，影响未来竞争力。]
    ④. **专利资产价值风险：** [评估专利作为无形资产的价值和市场应用前景，判断是否存在因专利管理不善导致资产贬值或流失的风险。例如，大量低质量或已过时的专利可能无法为企业带来实际价值，反而增加维护成本。]

    改进建议：
    ①. **制定全面专利战略：** [例如，针对核心技术和产品，制定发明专利、实用新型专利和外观设计专利相结合的全面保护策略，确保技术创新得到充分保护。]
    ②. **加强专利风险排查：** [例如，在产品研发和上市前，进行全面的专利检索和侵权风险分析，规避潜在的专利纠纷。]
    ③. **提升研发创新能力：** [例如，加大研发投入，鼓励技术创新，定期进行专利技术评估，确保专利组合具有先进性和市场竞争力。]
    ④. **优化专利管理与运营：** [例如，建立完善的专利管理制度，包括专利申请、维护、许可和转让等环节。积极将专利技术转化为市场价值，实现知识产权的商业化。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行专利查询',
                details=json.dumps({
                    'type': 'patent',
                    'search_key': search_key,
                    'company_name': company_name_for_bluelm,
                    'patent_data_list': patent_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'patentDataList': patent_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：企业年报信息 API 路由和 AI 分析
@app.route('/api/qichacha/annual_report', methods=['POST'])
@login_required
@permission_required('q2_nianbaoxinxi')  # Specific permission
def annual_report_query():
    data = request.json
    key_no = data.get('keyNo')
    year = data.get('year')  # Optional year
    company_name_for_bluelm = data.get('companyNameForBlueLM') or key_no

    if not key_no:
        return jsonify({'success': False, 'error': '请输入查询关键字（企业名称或统一社会信用代码）'}), 400

    annual_report_data_list = get_annual_report(key_no, year)

    if not annual_report_data_list:
        return jsonify({'success': False, 'error': '未查询到企业年报信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_annual_report_data_for_bluelm_prompt(annual_report_data_list, key_no)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查企业年报信息，对企业的财务健康状况、经营稳定性、股东结构变化和社保合规性进行分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查企业年报信息：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **财务健康状况风险：** [分析年报中的资产总额、负债总额、营业总收入、净利润等财务数据，判断企业是否存在资不抵债、盈利能力下降或经营亏损的风险。例如，如果负债总额远超资产总额，可能表明企业财务状况恶化，存在破产风险。]
    ②. **经营稳定性风险：** [结合从业人数、经营状态、股权变更信息等，评估企业经营的稳定性。例如，从业人数大幅减少或经营状态异常（如停业），可能预示企业经营出现问题。]
    ③. **股东结构与治理风险：** [分析股东及出资信息、股权变更信息，判断是否存在股权结构不稳定、股东纠纷或实际控制人变更等风险。例如，频繁的股权转让可能反映企业内部不稳定或存在潜在的利益冲突。]
    ④. **社保与合规风险：** [核查社保信息（如参保人数、缴费基数），判断企业是否存在社保欠缴、未足额缴纳或与实际用工人数不符的风险。例如，社保参保人数与员工数量严重不符，可能存在用工不规范或逃避社保责任的风险。]

    改进建议：
    ①. **强化财务风险管理：** [例如，定期进行财务审计和风险评估，优化资产负债结构，提升盈利能力。对于财务指标异常的企业，应深入调查其经营状况。]
    ②. **提升经营管理效率：** [例如，关注员工队伍的稳定性，优化人力资源管理；对于经营状态异常的企业，应及时采取措施恢复正常运营。]
    ③. **优化公司治理结构：** [例如，建立透明、稳定的股权结构，明确股东权利义务，完善公司治理机制，避免因股权纠纷影响企业发展。]
    ④. **确保社保合规性：** [例如，严格按照国家规定为员工缴纳社保，确保参保人数与实际用工人数一致。定期进行社保自查，避免因社保问题引发法律风险。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行企业年报信息查询',
                details=json.dumps({
                    'type': 'annual_report',
                    'key_no': key_no,
                    'company_name': company_name_for_bluelm,
                    'annual_report_data_list': annual_report_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'annualReportDataList': annual_report_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：综合风险排查 API 路由和 AI 分析
@app.route('/api/qichacha/comprehensive_risk', methods=['POST'])
@login_required
@permission_required('q3_zonghefengxianpaizha')  # Specific permission
def comprehensive_risk_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    qcc_data = comprehensive_risk_scan(search_key)

    if not qcc_data:
        return jsonify({'success': False, 'error': '未查询到综合风险信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_qcc_data_for_bluelm_prompt(qcc_data, api_type='comprehensive_risk')

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查综合风险排查数据，对企业进行全面、深入的风险分析，并提供具体、可操作的改进建议。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查综合风险排查数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **司法涉诉风险：** [分析失信被执行人、被执行人、裁决文书等信息，判断企业是否存在法律诉讼风险和信用风险。例如，如果企业多次被列为失信被执行人，将严重影响其融资能力和商业合作。]
    ②. **经营合规风险：** [分析经营异常、严重违法、行政处罚等信息，判断企业是否存在经营不规范、违反法律法规的风险。例如，被列入经营异常名录可能导致企业在招投标、融资等方面受限。]
    ③. **财务与资产风险：** [分析动产抵押、股权出质、股权冻结、司法拍卖、破产重整、清算信息、欠税公告等，判断企业是否存在财务危机、资产受限或面临破产清算的风险。例如，股权被大量冻结可能预示企业存在重大债务纠纷。]
    ④. **税务与环保风险：** [分析欠税公告、税收违法、税务非正常户、税务催缴、税务催报、环保处罚等信息，判断企业是否存在税务违规和环境污染风险。例如，多次出现欠税公告可能表明企业财务状况紧张或存在偷逃税行为。]

    改进建议：
    ①. **加强法律合规管理：** [例如，建立健全法律顾问制度，定期进行合规审查，及时处理法律纠纷，避免成为失信被执行人。]
    ②. **优化经营管理：** [例如，严格遵守市场监管规定，避免经营异常和严重违法行为；加强内部控制，防范行政处罚。]
    ③. **健全财务风险控制：** [例如，优化资产结构，减少抵押和质押；建立预警机制，防范股权冻结和司法拍卖；合理规划税务，避免欠税和税务违法。]
    ④. **履行社会责任：** [例如，严格执行环保法规，减少环境污染；规范税务申报，避免税务风险；积极响应税务催缴和催报，维护良好信用。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=60)  # 综合风险排查可能耗时更长
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行综合风险排查',
                details=json.dumps({
                    'type': 'comprehensive_risk',
                    'search_key': search_key,
                    'company_name': qcc_data.get('Name', search_key),
                    'qcc_data': qcc_data,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'qccData': qcc_data,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：失信核查 API 路由和 AI 分析
@app.route('/api/qichacha/shixin_check', methods=['POST'])
@login_required
@permission_required('q3_shixinhecha')  # Specific permission
def shixin_check_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    shixin_data_list = get_shixin_list(search_key)

    if not shixin_data_list:
        return jsonify({'success': False, 'error': '未查询到失信信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_shixin_data_for_bluelm_prompt(shixin_data_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查失信被执行人核查数据，对企业进行信用风险、法律风险和经营风险分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查失信被执行人核查数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **严重信用风险：** [分析失信记录的数量、涉案金额、履行情况和失信行为，判断企业是否存在严重的信用问题和拒不履行法律义务的倾向。例如，多次被列为失信被执行人且涉案金额巨大，表明企业信用状况极差，合作风险极高。]
    ②. **法律诉讼风险：** [分析失信记录的案号、执行法院和执行依据文号，判断企业是否面临或曾面临重大法律诉讼，以及其对法律裁决的尊重程度。例如，有履行能力而拒不履行生效法律文书确定义务，直接反映企业法律意识薄弱或恶意逃避债务。]
    ③. **经营与融资受限风险：** [失信被执行人将受到多方面限制，包括融资、招投标、高消费等，分析这些限制对企业经营的潜在影响。例如，企业将难以从银行获得贷款，限制其业务扩张和日常运营。]
    ④. **声誉与市场风险：** [失信信息公开将严重损害企业声誉，影响其市场形象和客户信任度。例如，负面信用记录可能导致客户流失、合作伙伴终止合作，甚至影响员工士气。]

    改进建议：
    ①. **立即履行法律义务：** [例如，对于已判决的债务，企业应立即制定还款计划并积极履行，争取从失信名单中移除。]
    ②. **加强法律合规培训：** [例如，定期对管理层和员工进行法律合规培训，提升法律意识，确保企业经营行为符合法律法规。]
    ③. **重建企业信用：** [例如，通过公开透明的方式披露整改情况，积极与债权人沟通协商，逐步恢复市场信任。]
    ④. **建立风险预警机制：** [例如，建立健全内部法律风险预警机制，对潜在的法律纠纷进行早期识别和干预，避免演变为失信案件。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行失信核查',
                details=json.dumps({
                    'type': 'shixin_check',
                    'search_key': search_key,
                    'company_name': company_name_for_bluelm,
                    'shixin_data_list': shixin_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'shixinDataList': shixin_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：经营异常核查 API 路由和 AI 分析
@app.route('/api/qichacha/exception_check', methods=['POST'])
@login_required
@permission_required('q3_jingyinyichanghecha')  # Specific permission
def exception_check_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    exception_data_list = get_exception_list(search_key)

    if not exception_data_list:
        return jsonify({'success': False, 'error': '未查询到经营异常信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_exception_data_for_bluelm_prompt(exception_data_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查经营异常核查数据，对企业进行经营合规风险、市场信誉风险和潜在法律风险分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查经营异常核查数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **经营合规性风险：** [分析企业被列入经营异常名录的原因（如未按时年报、通过登记住所无法联系等），判断企业是否存在违反工商行政管理法规的行为。例如，未按时年报可能导致企业信用评级下降，影响其市场竞争力。]
    ②. **市场信誉风险：** [经营异常信息公开将损害企业在客户、合作伙伴和公众中的信誉，影响其商业合作机会。例如，被列入异常名录可能导致合作伙伴对其履约能力产生质疑，甚至终止合作。]
    ③. **潜在法律与行政风险：** [经营异常可能引发行政处罚，甚至在严重情况下导致吊销营业执照。分析其潜在的法律后果。例如，通过登记住所无法联系，可能被认定为“失联企业”，面临行政处罚和法律诉讼风险。]
    ④. **经营稳定性风险：** [经营异常往往是企业经营出现问题的信号，分析其对企业长期经营稳定性的影响。例如，如果企业长期处于经营异常状态，可能预示其业务停滞或面临倒闭风险。]

    改进建议：
    ①. **及时纠正异常原因：** [例如，对于未按时年报的企业，应立即补报；对于通过登记住所无法联系的，应及时办理地址变更或提供有效联系方式。]
    ②. **加强信息披露透明度：** [例如，主动向合作伙伴和客户解释经营异常情况，并披露整改措施，重建信任。]
    ③. **建立健全内部管理制度：** [例如，完善工商档案管理制度，确保按时履行各项法定义务；加强日常运营管理，确保企业正常经营。]
    ④. **定期进行风险自查：** [例如，定期对企业经营状况进行自查，识别并纠正潜在的合规风险，避免被列入经营异常名录。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行经营异常核查',
                details=json.dumps({
                    'type': 'exception_check',
                    'search_key': search_key,
                    'company_name': company_name_for_bluelm,
                    'exception_data_list': exception_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'exceptionDataList': exception_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：被执行人核查 API 路由和 AI 分析
@app.route('/api/qichacha/zhixing_check', methods=['POST'])
@login_required
@permission_required('q3_beizhixingrenhecha')  # Specific permission
def zhixing_check_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    zhixing_data_list = get_zhixing_list(search_key)

    if not zhixing_data_list:
        return jsonify({'success': False, 'error': '未查询到被执行信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_zhixing_data_for_bluelm_prompt(zhixing_data_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查被执行人核查数据，对企业进行法律风险、财务风险和经营风险分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查被执行人核查数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **法律诉讼风险：** [分析被执行记录的案号、立案时间、执行法院，判断企业是否面临或曾面临法律诉讼，以及其对法律裁决的执行情况。例如，被法院强制执行，表明企业存在未履行或未完全履行的法律义务。]
    ②. **财务偿付能力风险：** [分析执行标的金额，判断企业是否存在大额债务未偿还，以及其财务偿付能力。例如，执行标的金额巨大，可能预示企业存在严重的财务危机，影响其流动性和持续经营能力。]
    ③. **经营与合作风险：** [被列为被执行人将影响企业在商业合作中的信誉，可能导致供应商、客户和金融机构对其产生质疑。例如，合作伙伴可能因担心风险而终止合作，影响企业业务开展。]
    ④. **声誉与市场风险：** [被执行信息公开将损害企业声誉，影响其市场形象和品牌价值。例如，负面法律记录可能导致公众对其产生负面认知，影响其市场竞争力。]

    改进建议：
    ①. **积极应对法律诉讼：** [例如，对于被执行案件，企业应积极与法院和申请执行人沟通，制定还款计划或寻求和解，尽快解决债务问题。]
    ②. **加强财务管理与风险控制：** [例如，建立健全财务管理制度，严格控制债务规模，确保资金链健康。定期进行财务审计，识别并化解潜在的财务风险。]
    ③. **提升企业合规意识：** [例如，加强法律合规培训，确保企业经营行为符合法律法规，避免因违规行为引发法律纠纷。]
    ④. **重建市场信任：** [例如，通过公开透明的方式披露案件进展和解决方案，积极与利益相关者沟通，逐步恢复市场信任。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行被执行人核查',
                details=json.dumps({
                    'type': 'zhixing_check',
                    'search_key': search_key,
                    'company_name': company_name_for_bluelm,
                    'zhixing_data_list': zhixing_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'zhixingDataList': zhixing_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：严重违法核查 API 路由和 AI 分析
@app.route('/api/qichacha/serious_illegal_check', methods=['POST'])
@login_required
@permission_required('q3_yanzhongweifahecha')  # Specific permission
def serious_illegal_check_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    serious_illegal_data_list = get_serious_illegal_list(search_key)

    if not serious_illegal_data_list:
        return jsonify({'success': False, 'error': '未查询到严重违法信息，请检查关键词或稍后再试。'}), 404

    formatted_data_for_prompt = _format_serious_illegal_data_for_bluelm_prompt(serious_illegal_data_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查严重违法核查数据，对企业进行法律合规风险、市场信誉风险和经营资质风险分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查严重违法核查数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **严重法律合规风险：** [分析企业被列入严重违法失信企业名单的原因和决定机关，判断企业是否存在严重违反法律法规的行为。例如，被列入严重违法名单，通常意味着企业存在重大违法行为，将面临严厉的法律制裁。]
    ②. **市场准入与经营资质风险：** [严重违法企业将受到市场准入限制，甚至可能被吊销相关经营资质。分析其对企业正常经营和业务拓展的潜在影响。例如，企业可能无法参与招投标、获得政府补贴，甚至被限制特定行业经营。]
    ③. **企业信誉与声誉风险：** [严重违法信息公开将对企业信誉和声誉造成毁灭性打击，影响其在客户、合作伙伴、投资者和公众中的形象。例如，负面新闻和公众质疑可能导致客户流失、融资困难，甚至引发品牌危机。]
    ④. **潜在刑事责任风险：** [某些严重违法行为可能涉及刑事责任，分析其潜在的法律后果。例如，如果违法行为构成犯罪，相关责任人可能面临刑事处罚。]

    改进建议：
    ①. **彻底整改违法行为：** [例如，企业应立即停止所有违法行为，并根据决定机关的要求进行彻底整改，争取从严重违法名单中移除。]
    ②. **加强法律合规体系建设：** [例如，建立完善的法律合规管理体系，定期进行合规审查和风险评估，确保企业经营行为完全符合法律法规。]
    ③. **重建企业形象与信任：** [例如，通过公开透明的方式披露整改情况和积极承担社会责任，逐步恢复市场信任和公众形象。]
    ④. **寻求专业法律援助：** [例如，在处理严重违法问题时，应立即寻求专业的法律援助，确保采取的措施合法有效。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行严重违法核查',
                details=json.dumps({
                    'type': 'serious_illegal_check',
                    'search_key': search_key,
                    'company_name': company_name_for_bluelm,
                    'serious_illegal_data_list': serious_illegal_data_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'seriousIllegalDataList': serious_illegal_data_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 新增：裁决文书核查 API 路由和 AI 分析
@app.route('/api/qichacha/judgment_doc_check', methods=['POST'])
@login_required
@permission_required('q3_caipanwenshuhecha')  # Specific permission
def judgment_doc_check_query():
    data = request.json
    search_key = data.get('searchKey')
    company_name_for_bluelm = data.get('companyNameForBlueLM') or search_key
    pub_year = data.get('pubYear')
    case_identity = data.get('caseIdentity')
    case_status = data.get('caseStatus')
    key_word_filter = data.get('keyWordFilter')

    if not search_key:
        return jsonify({'success': False, 'error': '请输入搜索关键词（企业名称或统一社会信用代码）'}), 400

    judgment_doc_list = get_judgment_doc_list(
        search_key,
        pub_year=pub_year,
        case_identity=case_identity,
        case_status=case_status,
        key_word_filter=key_word_filter
    )

    if not judgment_doc_list:
        return jsonify({'success': False, 'error': '未查询到裁决文书信息，请检查关键词或筛选条件。'}), 404

    formatted_data_for_prompt = _format_judgment_doc_data_for_bluelm_prompt(judgment_doc_list, search_key)

    prompt_text = f"""
    你是一个专业的企业风险评估专家。请根据以下企查查裁决文书核查数据，对企业进行法律诉讼风险、财务风险和声誉风险分析，并提供具体的核实建议和风险管理策略。请在每一点中提供充分的解释和至少一个具体例子，确保分析的深度和实用性。
    要求：
    1. 风险分析报告和改进建议都应详细，每点至少包含2-3行内容。
    2. 使用中文数字加圆点（如“①. ”、“②. ”）作为列表前缀。
    3. 严格按照以下格式输出，不要包含额外的前言或后语，也不要在标题以外的内容中使用Markdown格式（例如不要使用双星号**加粗**）。

    企业名称：{company_name_for_bluelm}

    企查查裁决文书核查数据：
    {formatted_data_for_prompt}

    风险分析报告：
    ①. **法律诉讼风险：** [分析裁决文书的数量、案件类型、案由、当事人角色（原告/被告），判断企业是否频繁涉诉，以及其在法律纠纷中的地位和责任。例如，如果企业作为被告频繁出现，且判决结果不利，可能表明其存在经营不规范或法律风险较高。]
    ②. **财务影响风险：** [分析案件金额、裁判结果，判断法律诉讼对企业财务状况的潜在影响，包括赔偿、罚款或资产冻结等。例如，涉及大额赔偿的案件，可能对企业现金流和盈利能力造成严重冲击。]
    ③. **经营与合作风险：** [法律诉讼，特别是重大诉讼，可能影响企业与供应商、客户和金融机构的合作关系，甚至导致业务中断。例如，被查封资产可能导致企业生产经营受阻。]
    ④. **声誉与市场风险：** [裁决文书公开将对企业声誉造成负面影响，损害其市场形象和品牌价值。例如，涉及不正当竞争或欺诈的案件，可能导致公众对其产生负面认知。]

    改进建议：
    ①. **加强法律合规管理：** [例如，建立健全法律顾问制度，定期进行合规审查，确保企业经营行为符合法律法规，减少法律纠纷的发生。]
    ②. **积极应对诉讼：** [例如，对于已发生的诉讼，应积极应诉，寻求专业法律援助，争取有利的判决结果；对于败诉案件，及时履行法律义务。]
    ③. **建立风险预警机制：** [例如，建立内部法律风险预警机制，对潜在的法律纠纷进行早期识别和干预，避免诉讼扩大化。]
    ④. **提升信息透明度：** [例如，在法律允许的范围内，向利益相关者披露诉讼进展和解决方案，维护企业声誉。]
    """

    params = {
        'requestId': str(uuid.uuid4())
    }

    api_data = {
        'prompt': prompt_text,
        'model': config.BLUE_LM_MODEL_NAME,
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 4000
        }
    }

    url = f'https://{DOMAIN}{URI_COMPLETIONS}'

    try:
        app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
        current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

        headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
        headers['Content-Type'] = 'application/json'

        response = requests.post(url, json=api_data, headers=headers, params=params, timeout=45)
        response.raise_for_status()

        res_obj = response.json()

        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            risk_factors_html, suggestions_html = _parse_bluelm_output(content)

            new_record = AuditLog(
                user_id=current_user.id,
                action='执行裁决文书核查',
                details=json.dumps({
                    'type': 'judgment_doc_check',
                    'search_key': search_key,
                    'company_name': company_name_for_bluelm,
                    'judgment_doc_list': judgment_doc_list,
                    'bluelm_output': content,
                    'risk_factors_html': risk_factors_html,
                    'suggestions_html': suggestions_html
                }),
                ip_address=request.remote_addr
            )
            db.session.add(new_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'judgmentDocList': judgment_doc_list,
                'riskFactorsHtml': risk_factors_html,
                'suggestionsHtml': suggestions_html,
                'bluelmOutput': content,
                'assessmentId': str(new_record.id)
            })
        else:
            error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
            return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'请求出错: {e}'}), 500


# 通用解析 BlueLM 输出函数 (保持不变)
def _parse_bluelm_output(content):
    risk_factors_html_parts = []
    suggestions_html_parts = []

    try:
        content_lines = content.strip().split('\n')
        current_section_type = None  # "risk_report" or "suggestions"
        current_list = None  # Reference to risk_factors_html_parts or suggestions_html_parts

        # This will store the parts of the current item's content,
        # including the initial title and the following description.
        current_item_lines = []

        # Helper to process and append a completed item
        def _process_and_append_item():
            nonlocal current_item_lines
            if not current_item_lines or current_list is None:
                return

            # Join all lines of the current item
            full_item_text = " ".join(current_item_lines).strip()

            # Regex to find "①. **Title:** Content"
            # Group 1: The numbered prefix (e.g., "①.")
            # Group 2: The bolded title (e.g., "匹配度与准确性风险")
            # Group 3: The rest of the content after the title and colon
            match = re.match(r'^(^[①②③④⑤⑥⑦⑧⑨⑩]\.\s*)\*\*(.*?)\*\*:\s*(.*)', full_item_text)

            if match:
                numbered_prefix = match.group(1).strip()
                title_text = match.group(2).strip()
                description_text = match.group(3).strip()

                # Remove any remaining ** from the description text
                clean_description = description_text.replace('**', '').strip()

                # Construct the HTML for this item
                html_item = (
                    f'<div class="suggestion-item">'
                    f'{numbered_prefix} <strong>{title_text}</strong>: {clean_description}'
                    f'</div>'
                )
                current_list.append(html_item)
            else:
                # Fallback for lines that don't match the expected pattern,
                # just clean up ** and wrap in a div.
                clean_text = full_item_text.replace('**', '').strip()
                current_list.append(f'<div class="suggestion-item">{clean_text}</div>')

            current_item_lines = []  # Reset for the next item

        for line in content_lines:
            line = line.strip()

            if not line:  # Skip empty lines
                continue

            if line == "风险分析报告：":
                _process_and_append_item()  # Process any pending item before switching section
                current_section_type = "risk_report"
                current_list = risk_factors_html_parts
                continue
            elif line == "改进建议：":
                _process_and_append_item()  # Process any pending item before switching section
                current_section_type = "suggestions"
                current_list = suggestions_html_parts
                continue

            # If we are in a section and the line starts with a numbered prefix,
            # it's a new item. Process the previous one (if any) and start a new one.
            if current_section_type is not None and re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]\.\s*', line):
                _process_and_append_item()
                current_item_lines.append(line)
            elif current_section_type is not None and current_item_lines:
                # This line is a continuation of the current item's description
                current_item_lines.append(line)
            elif current_section_type is not None:  # First line of the first item in a section
                current_item_lines.append(line)

        _process_and_append_item()  # Process the last item after the loop

        # Combine parts into final HTML
        risk_factors_html = ''.join(risk_factors_html_parts) if risk_factors_html_parts else \
            '<p class="suggestion-item" style="color: var(--danger-color);">蓝心大模型未能提供具体的风险因素，请尝试调整输入或Prompt。</p>'

        suggestions_html = ''.join(suggestions_html_parts) if suggestions_html_parts else \
            '<p class="suggestion-item" style="color: var(--danger-color);">蓝心大模型未能提供具体的改进建议，请尝试调整输入或Prompt。</p>'

    except Exception as e:
        print(f"解析蓝心大模型返回内容出错: {e}")
        traceback.print_exc()
        risk_factors_html = '<p class="suggestion-item" style="color: var(--danger-color);">无法解析蓝心大模型返回的风险因素，请联系管理员。</p>'
        suggestions_html = '<p class="suggestion-item" style="color: var(--danger-color);">无法解析蓝心大模型返回的改进建议，请联系管理员。</p>'

    return risk_factors_html, suggestions_html


@app.route('/api/chat', methods=['POST'])
@login_required  # 聊天也需要登录
def chat_with_ai():
    try:  # Outer try block to catch any unexpected errors before jsonify
        data = request.json
        user_message = data.get('message', '')
        context = data.get('context', {})
        chat_history = data.get('chatHistory', [])

        if not user_message:
            return jsonify({'success': False, 'error': '消息内容不能为空'}), 400

        messages = [{"role": "system",
                     "content": "你是一个专业的企业风险评估AI助手，能够根据提供的企业数据进行深度分析并提供建议。请以友好、专业、详细的语气回答用户问题。"}]

        for msg in chat_history:
            messages.append({"role": msg['role'], "content": msg['content']})

        context_info = ""
        if context.get('lastAnalysis'):
            analysis_type = context['lastAnalysis'].get('type')
            bluelm_output = context['lastAnalysis'].get('bluelmOutput', '未提供详细报告内容。')

            if analysis_type == 'dashboard_assessment':
                company_name = context['lastAnalysis']['companyName']
                context_info = f"用户最近对企业 '{company_name}' 进行了风险评估。以下是评估的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'qcc_verification':
                qcc_data_obj = context['lastAnalysis'].get('qccData', {})
                company_name = qcc_data_obj.get('Name', context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了企查查信息核验。以下是核验和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'industrial_info_query':
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('keyword', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了企业工商信息查询。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'fuzzy_search_query':
                search_key = context['lastAnalysis'].get('searchKey', '未知')
                context_info = f"用户最近进行了关键词 '{search_key}' 的企业模糊搜索。以下是搜索和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'tax_invoice_query':
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('keyword', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了税号开票信息查询。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'kyc_verify':  # New context for KYC page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了客户身份识别（KYC）查询。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'certification':  # New context for Certification page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了资质证书查询。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'trademark':  # New context for Trademark page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('keyword', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了全国商标查询。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'patent':  # New context for Patent page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了专利查询。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'annual_report':  # New context for Annual Report page
                company_name = context['lastAnalysis'].get('companyName', context['lastAnalysis'].get('key_no', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了企业年报信息查询。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'comprehensive_risk':  # New context for Comprehensive Risk page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了综合风险排查。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'shixin_check':  # New context for Shixin Check page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了失信核查。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'exception_check':  # New context for Exception Check page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了经营异常核查。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'zhixing_check':  # New context for Zhixing Check page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了被执行人核查。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'serious_illegal_check':  # New context for Serious Illegal Check page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了严重违法核查。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'judgment_doc_check':  # New context for Judgment Doc Check page
                company_name = context['lastAnalysis'].get('companyName',
                                                           context['lastAnalysis'].get('searchKey', '未知'))
                context_info = f"用户最近对企业 '{company_name}' 进行了裁决文书核查。以下是查询和AI分析的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"
            elif analysis_type == 'report_view':  # New context for report page
                company_name = context['lastAnalysis']['companyName']
                # The report type is also passed for more specific context if needed
                report_type_display = context['lastAnalysis'].get('reportType', '未知类型')
                context_info = f"用户当前正在查看企业 '{company_name}' 的详细报告（类型: {report_type_display}）。以下是报告的详细原始结果：\n{bluelm_output}\n\n请基于此信息回答用户的问题。"

        if context_info:
            messages.append({"role": "system", "content": context_info})

        messages.append({"role": "user", "content": user_message})

        full_prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

        params = {
            'requestId': str(uuid.uuid4())
        }

        api_data_for_completions = {
            'prompt': full_prompt,
            'model': config.BLUE_LM_MODEL_NAME,
            'sessionId': str(uuid.uuid4()),
            'extra': {
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 1024
            }
        }

        url = f'https://{DOMAIN}{URI_COMPLETIONS}'

        try:  # Inner try block for requests
            app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
            app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
            current_app_id = app_id_setting.value if app_id_setting else config.BLUE_LM_APP_ID
            current_app_key = app_key_setting.value if app_key_setting else config.BLUE_LM_APP_KEY

            headers = gen_sign_headers(current_app_id, current_app_key, METHOD, URI_COMPLETIONS, params)
            headers['Content-Type'] = 'application/json'

            print(f"Sending chat request to BlueLM: {url}")
            response = requests.post(url, json=api_data_for_completions, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            res_obj = response.json()
            print(f"Received chat response from BlueLM: {res_obj}")

            if res_obj['code'] == 0 and res_obj.get('data'):
                ai_response = res_obj['data']['content']
                return jsonify({'success': True, 'response': ai_response})
            else:
                error_msg = res_obj.get('msg', '蓝心大模型返回未知错误')
                print(f"蓝心大模型聊天返回错误: code={res_obj.get('code')}, msg={error_msg}")
                return jsonify({'success': False, 'error': f'蓝心大模型服务错误: {error_msg}'}), 500

        except requests.exceptions.Timeout:
            print("请求蓝心大模型聊天 API 超时。")
            return jsonify({'success': False, 'error': '请求蓝心大模型聊天 API 超时，请稍后再试。'}), 504
        except requests.exceptions.ConnectionError:
            print("无法连接到蓝心大模型聊天 API。")
            return jsonify({'success': False, 'error': '无法连接到蓝心大模型聊天 API，请检查网络连接。'}), 503
        except requests.exceptions.HTTPError as e:
            print(f'请求蓝心大模型聊天 API 返回 HTTP 错误: {e.response.status_code} - {e.response.text}')
            return jsonify(
                {'success': False,
                 'error': f'蓝心大模型聊天 API 返回错误: {e.response.status_code}'}), e.response.status_code
        except Exception as e:  # Catch any other error in the inner try block
            print(f'服务器内部错误 (Chatbot - inner request): {e}')
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'服务器内部错误: {e}'}), 500

    except Exception as e:  # Catch any error in the outer try block (e.g., parsing request.json)
        print(f'服务器内部错误 (Chatbot - outer function): {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'服务器内部错误: {e}'}), 500


# --- 平台管理路由 ---
@app.route('/admin/users', methods=['GET', 'POST'], endpoint='admin_users')
@login_required
@permission_required('admin_users')
def admin_users():
    users = User.query.all()
    form = UserForm()  # This form is for editing, not adding. Add user has its own route.
    return render_template('admin/users.html', title='用户管理', users=users, form=form)


@app.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
@permission_required('admin_users')
def admin_add_user():
    form = RegistrationForm()  # Reuse registration form for adding

    # Dynamically add role field to RegistrationForm for admin context
    # This is a workaround if RegistrationForm doesn't naturally have a role field.
    # A better approach might be to have a dedicated AdminAddUserForm.
    if not hasattr(form, 'role'):
        roles = Role.query.order_by('name').all()
        form.role = SelectField('角色', coerce=int, choices=[(r.id, r.name) for r in roles],
                                validators=[DataRequired()])
        form.is_active = BooleanField('是否活跃', default=True)  # Add is_active for new users

    if form.validate_on_submit():
        user_role = Role.query.get(form.role.data)
        if not user_role:
            flash('系统错误：所选用户角色不存在。', 'danger')
            return redirect(url_for('admin_add_user'))

        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password, role=user_role,
                    is_active=form.is_active.data)
        db.session.add(user)
        db.session.commit()
        flash(f'用户 {user.username} 添加成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='添加用户', details=f'添加用户 {user.username}',
                             ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_users'))

    return render_template('admin/add_user.html', title='添加用户', form=form)


@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin_users')
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(original_username=user.username, original_email=user.email,
                    obj=user)  # Populate form with user object
    if form.validate_on_submit():
        form.populate_obj(user)  # Update user object from form data
        db.session.commit()
        flash(f'用户 {user.username} 更新成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='编辑用户',
                             details=f'编辑用户 {user.username} (ID: {user.id})', ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_users'))
    # GET request will automatically populate form fields due to obj=user in form initialization
    return render_template('admin/edit_user.html', title='编辑用户', form=form, user=user)


@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
@permission_required('admin_users')
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('您不能删除自己的账户！', 'danger')
        return redirect(url_for('admin_users'))

    # 删除用户的相关审计日志
    AuditLog.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f'用户 {user.username} 已删除。', 'success')
    audit_log = AuditLog(user_id=current_user.id, action='删除用户',
                         details=f'删除用户 {user.username} (ID: {user.id})', ip_address=request.remote_addr)
    db.session.add(audit_log)
    db.session.commit()
    return redirect(url_for('admin_users'))


@app.route('/admin/user/reset_password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin_users')
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(f'用户 {user.username} 的密码已重置成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='重置用户密码',
                             details=f'重置用户 {user.username} (ID: {user.id}) 的密码', ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_users'))
    return render_template('admin/reset_password.html', title='重置密码', form=form, user=user)


@app.route('/admin/roles', methods=['GET', 'POST'], endpoint='admin_roles')
@login_required
@permission_required('admin_roles')
def admin_roles():
    roles = Role.query.all()
    form = RoleForm()
    if form.validate_on_submit():
        new_role = Role(name=form.name.data, description=form.description.data)
        db.session.add(new_role)
        db.session.commit()
        flash(f'角色 {new_role.name} 添加成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='添加角色', details=f'添加角色 {new_role.name}',
                             ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_roles'))
    return render_template('admin/roles.html', title='角色管理', roles=roles, form=form)


@app.route('/admin/role/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin_roles')
def admin_edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    form = RoleForm(original_name=role.name, obj=role)  # Populate form with role object
    if form.validate_on_submit():
        form.populate_obj(role)  # Update role object from form data
        db.session.commit()
        flash(f'角色 {role.name} 更新成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='编辑角色',
                             details=f'编辑角色 {role.name} (ID: {role.id})', ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_roles'))
    # GET request will automatically populate form fields due to obj=role in form initialization
    return render_template('admin/edit_role.html', title='编辑角色', form=form, role=role)


@app.route('/admin/role/delete/<int:role_id>', methods=['POST'])
@login_required
@permission_required('admin_roles')
def admin_delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.users:
        flash(f'无法删除角色 {role.name}，因为有用户属于此角色。', 'danger')
        return redirect(url_for('admin_roles'))
    db.session.delete(role)
    db.session.commit()
    flash(f'角色 {role.name} 已删除。', 'success')
    audit_log = AuditLog(user_id=current_user.id, action='删除角色', details=f'删除角色 {role.name} (ID: {role.id})',
                         ip_address=request.remote_addr)
    db.session.add(audit_log)
    db.session.commit()
    return redirect(url_for('admin_roles'))


@app.route('/admin/role/permissions/<int:role_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin_roles')
def admin_role_permissions(role_id):
    role = Role.query.get_or_404(role_id)
    all_permissions = Permission.query.order_by(Permission.name).all()  # Order permissions for consistent display
    if request.method == 'POST':
        selected_permission_ids = [int(x) for x in request.form.getlist('permissions')]
        role.permissions = [p for p in all_permissions if p.id in selected_permission_ids]
        db.session.commit()
        flash(f'角色 {role.name} 的权限已更新！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='更新角色权限',
                             details=f'更新角色 {role.name} (ID: {role.id}) 的权限', ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_roles'))

    # 获取当前角色拥有的权限ID
    role_permission_ids = {p.id for p in role.permissions}
    return render_template('admin/role_permissions.html', title=f'管理角色 {role.name} 的权限', role=role,
                           all_permissions=all_permissions, role_permission_ids=role_permission_ids)


@app.route('/admin/settings', methods=['GET', 'POST'], endpoint='admin_settings')
@login_required
@permission_required('admin_settings')
def admin_settings():
    settings = SystemSetting.query.all()
    form = SystemSettingForm()
    if form.validate_on_submit():
        new_setting = SystemSetting(key=form.key.data, value=form.value.data, description=form.description.data)
        db.session.add(new_setting)
        db.session.commit()
        flash(f'设置 {new_setting.key} 添加成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='添加系统设置', details=f'添加设置 {new_setting.key}',
                             ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_settings'))
    return render_template('admin/settings.html', title='系统设置', settings=settings, form=form)


@app.route('/admin/setting/edit/<int:setting_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin_settings')
def admin_edit_setting(setting_id):
    setting = SystemSetting.query.get_or_404(setting_id)
    form = SystemSettingForm(original_key=setting.key, obj=setting)  # Populate form with setting object
    if form.validate_on_submit():
        form.populate_obj(setting)  # Update setting object from form data
        db.session.commit()
        flash(f'设置 {setting.key} 更新成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='编辑系统设置',
                             details=f'编辑设置 {setting.key} (ID: {setting.id})', ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_settings'))
    # GET request will automatically populate form fields due to obj=setting in form initialization
    return render_template('admin/edit_setting.html', title='编辑设置', form=form, setting=setting)


@app.route('/admin/setting/delete/<int:setting_id>', methods=['POST'])
@login_required
@permission_required('admin_settings')
def admin_delete_setting(setting_id):
    setting = SystemSetting.query.get_or_404(setting_id)
    db.session.delete(setting)
    db.session.commit()
    flash(f'设置 {setting.key} 已删除。', 'success')
    audit_log = AuditLog(user_id=current_user.id, action='删除系统设置',
                         details=f'删除设置 {setting.key} (ID: {setting.id})', ip_address=request.remote_addr)
    db.session.add(audit_log)
    db.session.commit()
    return redirect(url_for('admin_settings'))


@app.route('/admin/audit_logs', methods=['GET'], endpoint='admin_audit_logs')
@login_required
@permission_required('view_audit_logs')
def admin_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin/audit_logs.html', title='审计日志', logs=logs)


@app.route('/admin/external_links', methods=['GET', 'POST'], endpoint='admin_external_links')
@login_required
@permission_required('manage_external_links')
def admin_external_links():
    form = ExternalLinkForm()
    if form.validate_on_submit():
        new_link = ExternalLink(
            name=form.name.data,
            url=form.url.data,
            description=form.description.data,
            category=form.category.data,
            icon=form.icon.data,
            is_active=form.is_active.data
        )
        db.session.add(new_link)
        db.session.commit()
        flash(f'外部链接 "{new_link.name}" 添加成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='添加外部链接', details=f'添加链接 {new_link.name}',
                             ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_external_links'))

    # 获取所有活跃的外部链接
    all_external_links = ExternalLink.query.filter_by(is_active=True).all()

    # 对 all_external_links 进行排序，以确保表格中图片图标按数字顺序显示
    all_external_links.sort(key=lambda x: (
        x.category, # 首先按分类排序
        # 提取图标文件名中的数字部分进行排序，非数字或非.png的排在后面
        int(x.icon.split('.')[0]) if x.icon and x.icon.endswith('.png') and x.icon.split('.')[0].isdigit() else float('inf'),
        x.name # 最后按名称排序，处理非数字图标和相同数字图标的情况
    ))

    return render_template('admin/external_links.html', title='外部链接管理', form=form,
                           all_external_links=all_external_links)

    # 获取所有外部链接
    all_external_links = ExternalLink.query.filter_by(is_active=True).all() # 不再在这里进行复杂的排序，只获取活跃链接

    # --- 新增：对 all_external_links 进行排序，以确保表格中图片图标按数字顺序显示 ---
    all_external_links.sort(key=lambda x: (
        x.category, # 首先按分类排序
        int(x.icon.split('.')[0]) if x.icon and x.icon.endswith('.png') and x.icon.split('.')[0].isdigit() else float('inf'), # 然后按数字图标排序
        x.name # 最后按名称排序，处理非数字图标和相同数字图标的情况
    ))
    # --- 新增结束 ---

    # The context processor `inject_global_data` already prepares `categorized_links` and `category_icons`
    # for all templates. We can directly use them in the template.
    # Note: `categorized_links` and `category_icons` are passed implicitly by the context processor.
    # If you need them explicitly in this view's template for some reason, you'd fetch them here too.
    return render_template('admin/external_links.html', title='外部链接管理', form=form,
                           all_external_links=all_external_links)


@app.route('/admin/external_link/edit/<int:link_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_external_links')
def admin_edit_external_link(link_id):
    link = ExternalLink.query.get_or_404(link_id)
    form = ExternalLinkForm(obj=link)  # Populate form with existing data
    if form.validate_on_submit():
        form.populate_obj(link)  # Update link object from form data
        db.session.commit()
        flash(f'外部链接 "{link.name}" 更新成功！', 'success')
        audit_log = AuditLog(user_id=current_user.id, action='编辑外部链接',
                             details=f'编辑链接 {link.name} (ID: {link.id})', ip_address=request.remote_addr)
        db.session.add(audit_log)
        db.session.commit()
        return redirect(url_for('admin_external_links'))
    return render_template('admin/edit_external_link.html', title='编辑外部链接', form=form, link=link)


@app.route('/admin/external_link/delete/<int:link_id>', methods=['POST'])
@login_required
@permission_required('manage_external_links')
def admin_delete_external_link(link_id):
    link = ExternalLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash(f'外部链接 "{link.name}" 已删除。', 'success')
    audit_log = AuditLog(user_id=current_user.id, action='删除外部链接',
                         details=f'删除链接 {link.name} (ID: {link.id})', ip_address=request.remote_addr)
    db.session.add(audit_log)
    db.session.commit()
    return redirect(url_for('admin_external_links'))


# --- 历史记录导出 API (已修改为从数据库获取) ---
@app.route('/api/export_report/<int:record_id>', methods=['GET'])
@login_required
@permission_required('export_reports')
def export_report(record_id):
    audit_log = AuditLog.query.get(record_id)

    if not audit_log:
        return jsonify({'error': 'Report not found'}), 404

    # 确保用户只能导出自己的报告，或者管理员可以导出所有报告
    if audit_log.user_id != current_user.id and not (current_user.role and current_user.role.name == 'Admin'):
        return jsonify({'error': 'Unauthorized to export this report'}), 403

    try:
        record = json.loads(audit_log.details)
        report_type = record.get('type', 'assessment')
        company_name = record.get('company_name', '未知企业')

        df_main = pd.DataFrame()
        df_ai_analysis = pd.DataFrame()

        # 根据报告类型提取数据
        if report_type == 'assessment':
            input_data = record.get('input_data', {})
            preliminary_risk = record.get('preliminary_risk', {})

            flat_data = {}
            for k, v in input_data.items():
                flat_data[f'输入数据 - {INPUT_DATA_KEY_MAP.get(k, k)}'] = v
            for k, v in preliminary_risk.items():
                flat_data[f'风险得分 - {k_map_risk.get(k, k)}'] = v

            df_main = pd.DataFrame([flat_data])

            ai_analysis_text = html_to_plain_text(record.get('risk_factors_html', '无'))
            ai_suggestions_text = html_to_plain_text(record.get('suggestions_html', '无'))
            df_ai_analysis = pd.DataFrame({
                'AI风险分析': [ai_analysis_text],
                'AI改进建议': [ai_suggestions_text]
            })

        elif report_type in ['qcc_verify', 'industrial_info', 'tax_invoice', 'kyc_verify', 'comprehensive_risk']:
            qcc_data = record.get('qcc_data', {})
            if qcc_data:
                df_main = pd.json_normalize(qcc_data)
            else:
                df_main = pd.DataFrame([{"信息": "无数据"}])

            ai_analysis_text = html_to_plain_text(record.get('risk_factors_html', '无'))
            ai_suggestions_text = html_to_plain_text(record.get('suggestions_html', '无'))
            df_ai_analysis = pd.DataFrame({
                'AI风险分析': [ai_analysis_text],
                'AI改进建议': [ai_suggestions_text]
            })

        elif report_type in ['fuzzy_search', 'certification', 'trademark', 'patent', 'annual_report', 'shixin_check',
                             'exception_check', 'zhixing_check', 'serious_illegal_check', 'judgment_doc_check']:
            data_list_key = {
                'fuzzy_search': 'qcc_data_list',
                'certification': 'certification_data_list',
                'trademark': 'trademark_data_list',
                'patent': 'patent_data_list',
                'annual_report': 'annual_report_data_list',
                'shixin_check': 'shixin_data_list',
                'exception_check': 'exception_data_list',
                'zhixing_check': 'zhixing_data_list',
                'serious_illegal_check': 'serious_illegal_data_list',
                'judgment_doc_check': 'judgment_doc_list',
            }.get(report_type)

            data_list = record.get(data_list_key, [])
            if data_list:
                df_main = pd.json_normalize(data_list)
            else:
                df_main = pd.DataFrame([{"信息": "无数据"}])

            ai_analysis_text = html_to_plain_text(record.get('risk_factors_html', '无'))
            ai_suggestions_text = html_to_plain_text(record.get('suggestions_html', '无'))
            df_ai_analysis = pd.DataFrame({
                'AI风险分析': [ai_analysis_text],
                'AI改进建议': [ai_suggestions_text]
            })
        else:
            return jsonify({'error': 'Unsupported report type for export'}), 400

        # 创建一个内存中的Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_main.to_excel(writer, index=False, sheet_name='报告数据')
            if not df_ai_analysis.empty:
                df_ai_analysis.to_excel(writer, index=False, sheet_name='AI分析和建议')

        output.seek(0)  # 将文件指针移到开头

        filename = f"{company_name}_{report_type}_{audit_log.timestamp.strftime('%Y%m%d%H%M%S')}.xlsx"
        return send_file(output, download_name=filename, as_attachment=True,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        app.logger.error(f"Error exporting report {record_id}: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to export report: {str(e)}'}), 500


if __name__ == '__main__':
    # 在运行应用前创建instance文件夹（如果不存在）
    if not os.path.exists('instance'):
        os.makedirs('instance')

    # 在应用上下文（application context）中执行数据库初始化
    with app.app_context():
        db.create_all()  # 创建所有数据库表

        # 检查并创建默认角色和权限
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin', description='系统管理员')
            db.session.add(admin_role)
        user_role = Role.query.filter_by(name='User').first()
        if not user_role:
            user_role = Role(name='User', description='普通用户')
            db.session.add(user_role)
        db.session.commit()

        # 检查并创建默认权限
        permissions_data = [
            # Dashboard & Assessment
            {'name': 'view_dashboard', 'description': '查看风险评估仪表盘'},
            {'name': 'perform_assessment', 'description': '执行企业风险评估'},
            {'name': 'view_assessment_report', 'description': '查看风险评估报告'},
            # Smart Search (Q1)
            {'name': 'q1_qiyexinxihecha', 'description': '企业信息核验'},
            {'name': 'q1_gongshangxinxi', 'description': '企业工商信息'},
            {'name': 'q1_mohusousuo', 'description': '企业模糊搜索'},
            {'name': 'q1_shuihaokaipiao', 'description': '税号开票信息'},
            # Smart Search (Q2)
            {'name': 'q2_kehushenfenshibie', 'description': '客户身份识别 (KYC)'},
            {'name': 'q2_zizhizhengshu', 'description': '资质证书查询'},
            {'name': 'q2_shangbiaochaxun', 'description': '全国商标查询'},
            {'name': 'q2_zhuanlichaxun', 'description': '专利查询'},
            {'name': 'q2_nianbaoxinxi', 'description': '企业年报信息'},
            # Smart Search (Q3)
            {'name': 'q3_zonghefengxianpaizha', 'description': '综合风险排查'},
            {'name': 'q3_shixinhecha', 'description': '失信核查'},
            {'name': 'q3_jingyinyichanghecha', 'description': '经营异常核查'},
            {'name': 'q3_beizhixingrenhecha', 'description': '被执行人核查'},
            {'name': 'q3_yanzhongweifahecha', 'description': '严重违法核查'},
            {'name': 'q3_caipanwenshuhecha', 'description': '裁判文书核查'},
            # Admin Panel
            {'name': 'admin_users', 'description': '管理用户账户'},
            {'name': 'admin_roles', 'description': '管理角色与权限'},
            {'name': 'admin_settings', 'description': '管理系统设置'},
            {'name': 'view_audit_logs', 'description': '查看审计日志'},
            {'name': 'manage_external_links', 'description': '管理外部链接'},
            {'name': 'export_reports', 'description': '导出报告'}
        ]
        for p_data in permissions_data:
            if not Permission.query.filter_by(name=p_data['name']).first():
                permission = Permission(name=p_data['name'], description=p_data['description'])
                db.session.add(permission)
        db.session.commit()
        print("Permissions created.")

        # 给Admin角色分配所有权限
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            all_permissions = Permission.query.all()
            for perm in all_permissions:
                if perm not in admin_role.permissions:
                    admin_role.permissions.append(perm)
            db.session.commit()
            print("Admin role updated with all permissions.")

        # 给User角色分配基本权限
        user_role = Role.query.filter_by(name='User').first()
        if user_role:
            user_permissions_names = [
                'view_dashboard', 'perform_assessment', 'view_assessment_report', 'export_reports',
                'q1_qiyexinxihecha', 'q1_gongshangxinxi', 'q1_mohusousuo', 'q1_shuihaokaipiao',
                'q2_kehushenfenshibie', 'q2_zizhizhengshu', 'q2_shangbiaochaxun', 'q2_zhuanlichaxun', 'q2_nianbaoxinxi',
                'q3_zonghefengxianpaizha',
                'q3_shixinhecha', 'q3_jingyinyichanghecha', 'q3_beizhixingrenhecha', 'q3_yanzhongweifahecha',
                'q3_caipanwenshuhecha'
            ]
            for perm_name in user_permissions_names:
                perm = Permission.query.filter_by(name=perm_name).first()
                if perm and perm not in user_role.permissions:
                    user_role.permissions.append(perm)
            db.session.commit()
            print("User role updated with basic permissions.")

        # 检查并创建默认管理员用户
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@example.com', role=admin_role)
            admin_user.set_password('admin123')  # 默认密码，生产环境请修改！
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created: admin/admin123")

        # 检查并创建默认普通用户
        if not User.query.filter_by(username='user').first():
            user_role = Role.query.filter_by(name='User').first()
            normal_user = User(username='user', email='user@example.com', role=user_role)
            normal_user.set_password('user123')  # 默认密码，生产环境请修改！
            db.session.add(normal_user)
            db.session.commit()
            print("Default normal user created: user/user123")

        # 检查并创建默认系统设置 (例如企查查API密钥)
        qcc_appkey_setting = SystemSetting.query.filter_by(key='QICHACHA_APPKEY').first()
        if not qcc_appkey_setting:
            db.session.add(
                SystemSetting(key='QICHACHA_APPKEY', value=config.QICHACHA_APPKEY, description='企查查API AppKey'))
        else:
            qcc_appkey_setting.value = config.QICHACHA_APPKEY  # 确保数据库中的值与config一致

        qcc_secretkey_setting = SystemSetting.query.filter_by(key='QICHACHA_SECRETKEY').first()
        if not qcc_secretkey_setting:
            db.session.add(SystemSetting(key='QICHACHA_SECRETKEY', value=config.QICHACHA_SECRETKEY,
                                         description='企查查API SecretKey'))
        else:
            qcc_secretkey_setting.value = config.QICHACHA_SECRETKEY  # 确保数据库中的值与config一致

        # 针对蓝心大模型API密钥的默认设置
        blue_lm_app_id_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_ID').first()
        if not blue_lm_app_id_setting:
            db.session.add(SystemSetting(key='BLUE_LM_APP_ID', value=config.BLUE_LM_APP_ID, description='蓝心大模型API AppID'))
        else:
            blue_lm_app_id_setting.value = config.BLUE_LM_APP_ID  # Ensure current default value

        blue_lm_app_key_setting = SystemSetting.query.filter_by(key='BLUE_LM_APP_KEY').first()
        if not blue_lm_app_key_setting:
            db.session.add(
                SystemSetting(key='BLUE_LM_APP_KEY', value=config.BLUE_LM_APP_KEY, description='蓝心大模型API AppKey'))
        else:
            blue_lm_app_key_setting.value = config.BLUE_LM_APP_KEY  # Ensure current default value

        db.session.commit()
        print("Default system settings for QCC and BlueLM API keys configured.")

        # Add some example external links if not exists
        if not ExternalLink.query.first():
            example_links_data = [
                # 项目管理和协作工具
                {'name': 'PingCode', 'description': '项目管理', 'url': 'https://pingcode.com',
                 'category': '项目管理和协作工具', 'icon': '1.png'},  # <-- 确保这里是 '1.png'
                {'name': 'Worktile', 'description': '通用项目管理', 'url': 'https://worktile.com',
                 'category': '项目管理和协作工具', 'icon': '2.png'},  # <-- '2.png'
                {'name': 'Coding', 'description': '研发项目管理', 'url': 'https://coding.net',
                 'category': '项目管理和协作工具', 'icon': '3.png'},  # <-- '3.png'
                {'name': 'Slack', 'description': '团队沟通', 'url': 'https://slack.com',
                 'category': '项目管理和协作工具', 'icon': '4.png'},  # <-- '4.png'
                {'name': 'Jira', 'description': '敏捷项目管理', 'url': 'https://atlassian.com/software/jira',
                 'category': '项目管理和协作工具', 'icon': '5.png'},  # <-- '5.png'
                {'name': 'Trello', 'description': '看板任务管理', 'url': 'https://trello.com',
                 'category': '项目管理和协作工具', 'icon': '6.png'},  # <-- '6.png'
                {'name': 'Asana', 'description': '任务管理', 'url': 'https://asana.com',
                 'category': '项目管理和协作工具', 'icon': '7.png'},  # <-- '7.png' (新增)
                {'name': 'Monday.com', 'description': '工作管理', 'url': 'https://monday.com',
                 'category': '项目管理和协作工具', 'icon': '8.png'},  # <-- '8.png' (新增)

                # 文档管理和网盘工具
                {'name': '语雀', 'description': '文档协作', 'url': 'https://yuque.com',
                 'category': '文档管理和网盘工具', 'icon': '1.png'},  # 这里的 '1.png' 会是该分类下的第一个
                {'name': '联想Filez', 'description': '企业网盘', 'url': 'https://filez.lenovo.com',
                 'category': '文档管理和网盘工具', 'icon': '2.png'},
                {'name': '亿方云', 'description': '云文档存储', 'url': 'https://yifangyun.com',
                 'category': '文档管理和网盘工具', 'icon': '3.png'},
                # ... (其他分类的链接，也请确保 icon 字段是图片文件名) ...
            ]
            for link_data in example_links_data:
                # 检查链接是否已存在，避免重复添加
                if not ExternalLink.query.filter_by(name=link_data['name'], category=link_data['category']).first():
                    link = ExternalLink(**link_data)
                    db.session.add(link)
            db.session.commit()
            print("Example external links added.")
        else:
            print("External links already exist, skipping initial population.")

        app.run(debug=True, host='0.0.0.0', port=5013)

