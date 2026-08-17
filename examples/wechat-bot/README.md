# 微信个人号/群机器人接入 xiaocai-stock-ai

**⚠️ 前置说明**: 微信官方不允许个人号自动化操作, 走 UI 自动化方案有账号封禁风险。本方案仅供学习研究, 生产建议用飞书群或公众号客服消息 API。

## 方案 1: wxauto (Windows UI 自动化) [推荐个人测试用]

### 前置

- **Windows 系统**(或 Windows VM, Mac 用户可用 UTM/Parallels)
- **微信 PC 版**登录一个小号(别用主号!)
- Python 3.10+

### 步骤

```powershell
pip install wxauto httpx
```

### 代码骨架(`bot.py`)

```python
import time, httpx
from wxauto import WeChat

API = "https://xiaocai.sque.site/api/ask"  # 或你自部署的地址
TRIGGER_GROUPS = ["你的测试群名"]
wx = WeChat()

def call_xiaocai(question: str) -> str:
    r = httpx.post(API, json={"question": question}, timeout=180)
    return r.json().get("answer", "")

while True:
    # 拉当前所有窗口新消息
    for group in TRIGGER_GROUPS:
        wx.ChatWith(group)
        msgs = wx.GetAllMessage()
        for m in msgs[-5:]:  # 只看最近5条
            if "@小财" in m.content:
                q = m.content.replace("@小财", "").strip()
                if q:
                    a = call_xiaocai(q)
                    wx.SendMsg(a + "\n\n---\n仅供参考, 不构成投资建议")
    time.sleep(10)
```

### 硬约束

- 频率控制: 每群每分钟最多 3 次响应, 别刷屏
- 小号先跑 1-2 周观察, 别上主号
- 触发词严格(`@小财` 加空格), 避免误触发

## 方案 2: 微信公众号客服消息 API [推荐生产]

前置: **已认证的微信服务号**(个人主体 300元/年)

流程:
1. 公众号后台 → 设置与开发 → 基本配置, 拿 AppID/AppSecret
2. 开通客服消息接口权限
3. 参考[官方文档](https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Service_Center_messages.html), 用户 48 小时内主动发过消息, 你可以回消息给他
4. 收到用户消息 → 调 xiaocai API → 通过客服消息 API 回

**优点**: 合规, 不封号, 可持续。**缺点**: 只能私聊, 群内用不了。

## 常见问题

- **wxauto 版本差异**: 微信客户端更新可能导致 UI 变化, wxauto 需相应更新
- **群消息读取延迟**: UI 自动化本质是模拟操作, 有秒级延迟
- **账号安全**: 用小号, 不要上主号, 出问题换号重来
