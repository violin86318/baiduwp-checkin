# Baidu Wangpan Check-in

精简版百度网盘会员签到仓库，适合直接跑在 GitHub Actions。

## 功能

- 会员成长值签到
- 每日答题
- 查询当前会员等级和成长值
- 支持多账号

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

## Cookie 获取

1. 登录百度网盘
2. 打开 [会员成长值任务页](https://pan.baidu.com/wap/svip/growth/task)
3. 复制完整请求 Cookie
4. 填到 `BAIDUWP_ACCOUNTS`

## 运行

### GitHub Actions

- 工作流文件: `.github/workflows/baiduwp.yml`
- 默认执行时间: UTC `01:10`
- 按上海时区计算: 每天 `09:10`
- 也支持手动触发 `workflow_dispatch`

### 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BAIDUWP_ACCOUNTS='[{"cookie":"BDUSS=xxx; STOKEN=xxx; ..."}]'
python baiduwp.py
```

## 注意

- GitHub 托管 runner 可能比本机更容易触发风控
- Cookie 失效后需要手动更新
- 如果百度修改接口返回格式，脚本可能需要跟着调整
