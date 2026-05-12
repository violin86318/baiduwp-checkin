# Baidu Wangpan Check-in

精简版百度网盘会员签到仓库，适合直接跑在 GitHub Actions。

## 功能

- 会员成长值签到
- 每日答题
- 查询当前会员等级和成长值
- 支持多账号
- 支持 Telegram Bot 通知
- 支持飞书机器人通知

## 配置

在 GitHub 仓库里添加一个 `Actions secret`:

- 名称: `BAIDUWP_ACCOUNTS`
- 值: JSON 数组

示例:

```json
[
  {
    "cookie": "BDUSS=xxx; STOKEN=xxx; ..."
  }
]
```

可选通知 Secrets：

- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `TELEGRAM_CHAT_ID`: Telegram 接收消息的 chat id
- `FEISHU_WEBHOOK_URL`: 飞书自定义机器人 Webhook
- `FEISHU_WEBHOOK_SECRET`: 飞书机器人签名密钥，可选

## Cookie 获取

1. 登录百度网盘
2. 打开 [会员成长值任务页](https://pan.baidu.com/wap/svip/growth/task)
3. 复制完整请求 Cookie
4. 填到 `BAIDUWP_ACCOUNTS`

## 运行

### GitHub Actions

- 工作流文件: `.github/workflows/baiduwp.yml`
- 默认执行时间: UTC `16:17` 和 `03:18`
- 按上海时区计算: 每天 `00:17` 和 `11:18`
- 也支持手动触发 `workflow_dispatch`

### 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BAIDUWP_ACCOUNTS='[{"cookie":"BDUSS=xxx; STOKEN=xxx; ..."}]'
export TELEGRAM_BOT_TOKEN='123456:abcdef'
export TELEGRAM_CHAT_ID='123456789'
export FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'
export FEISHU_WEBHOOK_SECRET='xxx'
python baiduwp.py
```

## 通知说明

- 如果只配置 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID`，会只发 Telegram
- 如果只配置 `FEISHU_WEBHOOK_URL`，会只发飞书
- 两边都配置，就会同时发送
- 即使签到流程失败，也会尽量发送失败通知

## 注意

- GitHub 托管 runner 可能比本机更容易触发风控
- Cookie 失效后需要手动更新
- 如果百度修改接口返回格式，脚本可能需要跟着调整
