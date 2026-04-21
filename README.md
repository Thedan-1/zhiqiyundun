# 智企云盾 (ZhiQiYunDun)

智企云盾是一款基于大模型与大数据分析的综合企业风险管理与评估平台。系统集成了企业信息查询、风险排查、大模型智能分析辅助等多项功能，旨在为企业提供安全、智能、便捷的风控摸排方案。

## 🌟 核心功能
- **智能企查**：对接企查查API，一键查阅企业工商信息、股东架构、经营异常等。
- **全景风险排查**：多维度进行客户身份识别、行政处罚、失信被执行人等综合风险筛查。
- **智能AI助手**：集成蓝心大模型 (BlueLM)，提供智能风控问答、政策解读以及风险评估意见。
- **可视化数据面板**：借助可视化仪表盘与报告生成功能，直观洞察企业风险指标。
- **权限与账号管理**：搭载完善的 Admin/User 多角色管理机制与安全审计日志。

## 🛠️ 技术栈
- **后端框架**：Python, Flask, Flask-SQLAlchemy, Flask-Login, WTForms
- **前端页面**：HTML5, CSS3, JavaScript, Jinja2 模板引擎
- **数据库**：SQLite (适合轻量及开箱即用)
- **大模型集成**：vivo 蓝心大模型 API
- **API 集成**：企查查企业信用 API

## 🚀 快速启动

### 1. 环境准备
确保本机已安装 Python 3.8+ 环境。

### 2. 下载与依赖安装
克隆此仓库并安装必要的 Python 依赖包：
`ash
git clone https://github.com/Thedan-1/zhiqiyundun.git
cd zhiqiyundun
pip install -r requirements.txt
`

### 3. 配置环境变量
为了保护您的 API 密钥安全，项目中已剔除了所有硬编码敏感信息。
请在项目根目录找到 .env.example 文件，将其复制一份并重命名为 .env。随后打开该文件填入您的真实密钥：

`env
# Flask 安全密钥
SECRET_KEY=您的高强度随机密钥

# 蓝心大模型 API 密钥配置
BLUE_LM_APP_ID=your_blue_lm_id
BLUE_LM_APP_KEY=your_blue_lm_key
BLUE_LM_MODEL_NAME=vivo-BlueLM-TB-Pro

# 企查查 API 密钥配置
QICHACHA_APPKEY=your_qcc_key
QICHACHA_SECRETKEY=your_qcc_secret
`

### 4. 运行服务
执行以下命令启动 Flask 后端程序：
`ash
python app.py
`
如无报错，系统将运行在 http://127.0.0.1:5013。

**预置测试账号：**
- 网站管理员：账号 dmin，密码 dmin123
- 普通用户：账号 user，密码 user123

## 🔒 隐私与安全声明
本项目专为 GitHub 进行了敏感数据脱敏处理，去除了所有明文存放的第三方商用 API 凭证。强烈建议配置 .gitignore 保护 .env 与数据库文件 site.db 免受意外上传的风险。