# 智企云盾

智企云盾是一个基于 Flask 的企业风险评估与信息核验平台，支持首页仪表盘、企查查查询、历史记录、管理后台和 AI 风险分析。

## 特性

- 企业风险评估仪表盘
- 企查查多类查询功能
- 历史记录与报告导出
- 用户、角色、系统设置、外部链接管理
- AI 模型可切换

## 环境变量

将 `.env.example` 复制为 `.env`，并填写真实值：

- `SECRET_KEY`
- `QICHACHA_APPKEY`
- `QICHACHA_SECRETKEY`
- `BLUE_LM_APP_ID`
- `BLUE_LM_APP_KEY`
- `BLUE_LM_MODEL_NAME`

`BLUE_LM_MODEL_NAME` 可以切换不同的蓝心模型名，例如：

- `vivo-BlueLM-TB-Pro`
- `vivo-BlueLM-TB-S`
- `vivo-BlueLM-TB`

## 启动

```bash
pip install -r requirements.txt
python app.py
```

默认会监听 `http://127.0.0.1:5013`。

## GitHub 发布建议

- 不要提交 `.env`
- 不要提交本地数据库文件和 `.venv`
- 如果你要公开仓库，建议先确认 `QICHACHA_APPKEY`、`QICHACHA_SECRETKEY` 和蓝心大模型密钥都已从代码里移除
