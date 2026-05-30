# config.py

import os # 导入 os 模块

from dotenv import load_dotenv

load_dotenv()

# 内部数据库 API 配置
QICHACHA_APPKEY = os.getenv('QICHACHA_APPKEY', '') # 从环境变量读取，避免提交到 GitHub
QICHACHA_SECRETKEY = os.getenv('QICHACHA_SECRETKEY', '') # 从环境变量读取，避免提交到 GitHub
QICHACHA_API_BASE_URL = 'https://api.qichacha.com'

# Flask 应用配置
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-before-deploy') # 从环境变量读取

# 蓝心大模型配置
BLUE_LM_APP_ID = os.getenv('BLUE_LM_APP_ID', '')
BLUE_LM_APP_KEY = os.getenv('BLUE_LM_APP_KEY', '')
BLUE_LM_MODEL_NAME = os.getenv('BLUE_LM_MODEL_NAME', 'vivo-BlueLM-TB-Pro')

# 可选的模型名候选，便于在不同环境间切换
BLUE_LM_MODEL_OPTIONS = [
	'vivo-BlueLM-TB-Pro',
	'vivo-BlueLM-TB-S',
	'vivo-BlueLM-TB',
]


SQLALCHEMY_TRACK_MODIFICATIONS = False