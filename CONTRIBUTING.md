# 贡献指南

欢迎 PR 和 Issue!

## 快速上手

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai
pip install -r requirements.txt
cp .env.example .env
# 填 DEEPSEEK_API_KEY 和 TUSHARE_TOKEN
python3 serve_http.py
```

## 提 Issue 前

1. 先搜一下有没有相同问题
2. 使用问题 → [飞书群](README.md#-一起玩) 或 [Discussions](../../discussions), 会更快
3. Bug/Feature → 用对应模板提

## 提 PR 前

1. Fork + 建分支
2. 保持一次 PR 一件事(小步快跑)
3. 改动核心引擎 → 至少加一个测试
4. 改动文档 → 用浏览器渲染看排版
5. 提交前跑一下 `python3 serve_http.py` 确认没崩

## 代码风格

- Python: ruff 默认规则 + 中文注释鼓励(项目主用户是中文开发者)
- 命令行输出: 面向新手, 每步说清"要看到什么"
- 引擎输出: 结论前置, 直接干脆(见 core/persona.py)

## 特别欢迎的贡献

- 新的接入示例 (Dify / Anthropic Workbench / Continue.dev 等)
- 数据源扩展 (港股/期货, 独立成新的 core/data/xxx.py)
- 手把手教程翻译成英文
- Bug fix
- 测试覆盖

## 维护者响应

- Bug: 尽力 3 天内响应
- Feature: 一周内评估
- Question: 建议先去飞书群, 那里回复更快

## 授权

提 PR 视为同意作品按 [Apache 2.0](LICENSE) 授权。
