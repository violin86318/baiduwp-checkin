# n8n 百度网盘工作流修正建议

这份说明基于你当前导出的工作流，优先修正真正影响安全性和稳定性的地方。

参考：
- n8n 官方文档说明 `Code` 节点支持返回 Promise，并支持 `console.log`：[Code node docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code/)
- n8n 官方文档说明 `Code` 节点输出数据会自动补 `json` 包装，但为了兼容性和可读性，仍建议显式返回 `[{ json: ... }]`：[Data structure docs](https://docs.n8n.io/data/data-structure/)

## 1. 最优先修正

### A. 不要把 Cookie 写死在工作流里

你现在的 `初始化配置1` 节点把完整 `BDUSS` / `STOKEN` 明文硬编码在 JSON 里，这会导致：

- 导出工作流时泄露登录态
- 截图、备份、同步时泄露
- 后面很难轮换 Cookie

建议改成从环境变量读取，例如在 n8n 运行环境里配置：

```bash
BAIDUWP_COOKIE=BDUSS=xxx; STOKEN=xxx; ...
```

然后把 `初始化配置1` 改成：

```js
const COOKIES = $env.BAIDUWP_COOKIE || '';

if (!COOKIES.trim()) {
  throw new Error('缺少环境变量 BAIDUWP_COOKIE');
}

const HEADERS = {
  Connection: 'keep-alive',
  Accept: 'application/json, text/plain, */*',
  'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
  'X-Requested-With': 'XMLHttpRequest',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Dest': 'empty',
  Referer: 'https://pan.baidu.com/wap/svip/growth/task',
  'Accept-Encoding': 'gzip, deflate',
  'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
  Cookie: COOKIES,
};

console.log('初始化百度网盘签到配置');

return [{
  json: {
    headers: HEADERS,
    cookies: COOKIES,
    timestamp: new Date().toISOString(),
  },
}];
```

### B. 把定时器改成“每天一次”

你当前的 `每日定时触发1`：

```json
"interval": [
  {
    "triggerAtMinute": 3
  }
]
```

这更像“每小时第 3 分钟触发”，不是“每日一次”。

建议在 n8n UI 里直接改成以下任一方式：

- `Every Day`，时间设为 `09:03`
- 或 `Custom (Cron)`，填 `3 9 * * *`

如果你的 n8n 实例时区是 `Asia/Shanghai`，这就是每天北京时间 `09:03`。

## 2. 逻辑修正

### C. “无题可答”不要算失败

你现在的 `跳过答题1` 会返回：

```js
success: false
```

后面的 `输出整理` 会把它统计成失败，导致每天都可能出现假告警。

把 `跳过答题1` 改成：

```js
const previousData = $input.first().json;

const answerResult = {
  success: true,
  skipped: true,
  message: '今日无答题任务',
  score: 0,
  timestamp: new Date().toISOString(),
};

console.log('[答题结果] 今日无答题任务');

return [{
  json: {
    headers: previousData.headers,
    cookies: previousData.cookies,
    signinResult: previousData.signinResult,
    questionResult: previousData.questionResult,
    answerResult,
  },
}];
```

### D. 汇总节点不要把 `skipped` 记为失败

把 `输出整理` 里这段：

```js
if (answer.success === false) {
  failReasons.push(`Item#${idx+1} 答题失败：${esc(answer.message || '（无消息）')}`);
}
```

改成：

```js
if (answer.success === false && !answer.skipped) {
  failReasons.push(`Item#${idx+1} 答题失败：${esc(answer.message || '（无消息）')}`);
}
```

再把这段：

```js
if (summary.answerSuccess) answerSuccessCount++; else answerFailCount++;
```

改成：

```js
if (details.answer?.skipped) {
  // 无题可答，不算成功也不算失败
} else if (summary.answerSuccess) {
  answerSuccessCount++;
} else {
  answerFailCount++;
}
```

以及把答题展示文案这段：

```js
blockLines.push(
  `答题: ${answer.success ? '✅' : '❌'} ${esc(answer.message || '')} (得分:${esc(answer.score != null ? answer.score : 0)})`
);
```

改成：

```js
const answerIcon = answer.skipped ? '➖' : (answer.success ? '✅' : '❌');
blockLines.push(
  `答题: ${answerIcon} ${esc(answer.message || '')} (得分:${esc(answer.score != null ? answer.score : 0)})`
);
```

## 3. 结果输出修正

### E. `输出整理` 显式返回 `json`

虽然新版 n8n 会自动补 `json` 包装，但建议统一显式写法，避免跨版本行为差异。

把 `输出整理` 最后返回值：

```js
return [{
  text,
  meta: {
    totalItems,
    totalPoints,
    signInSuccessCount,
    signInFailCount,
    answerSuccessCount,
    answerFailCount,
    earliestExec,
    latestExec,
    generatedAt: new Date().toISOString()
  }
}];
```

改成：

```js
return [{
  json: {
    text,
    meta: {
      totalItems,
      totalPoints,
      signInSuccessCount,
      signInFailCount,
      answerSuccessCount,
      answerFailCount,
      earliestExec,
      latestExec,
      generatedAt: new Date().toISOString(),
    },
  },
}];
```

## 4. 可选优化

### F. 用 `Wait` 节点代替 `等待间隔` 里的 `setTimeout`

你现在这样写也能跑：

```js
await new Promise(resolve => setTimeout(resolve, 3000));
```

但更推荐：

- 删除这个 `Code` 节点里的 sleep 逻辑
- 用 n8n 自带 `Wait` 节点等待 `3 seconds`

这样更清晰，也不会让 `Code` 节点自己占着执行时长。

### G. 签到失败时增加更明确的风控提示

你可以在 `处理签到结果1` 和 `处理问题结果1` 里补一层关键词判断，比如：

```js
if (responseText.includes('未登录') || responseText.includes('登录')) {
  signinResult.message = '签到失败: Cookie 可能失效或触发登录校验';
}
```

同理也可以对答题、用户信息查询做一样的提示，这样通知里更容易区分：

- 接口挂了
- Cookie 失效了
- 只是今天已经做过了

## 我最建议你先改的顺序

1. `初始化配置1` 改成环境变量
2. `每日定时触发1` 改成每天一次
3. `跳过答题1` 改成 `success: true, skipped: true`
4. `输出整理` 不再把 `skipped` 算失败
5. `输出整理` 显式返回 `json`

