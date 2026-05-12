import base64
import html
import hashlib
import hmac
import json
import os
import re
import sys
import time

import requests


class BaiduWP:
    def __init__(self, cookie: str):
        self.cookie = cookie.strip()
        self.session = requests.Session()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/90.0.4430.91 Mobile Safari/537.36"
            ),
            "Referer": "https://pan.baidu.com/wap/svip/growth/task",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": self.cookie,
        }

    def signin(self):
        url = "https://pan.baidu.com/rest/2.0/membership/level?app_id=250528&web=5&method=signin"
        resp = self.session.get(url, headers=self.headers, timeout=30)
        sign_point = None
        signin_error_msg = ""
        if resp.status_code == 200:
            match = re.search(r'points":(\d+)', resp.text)
            if match:
                sign_point = match.group(1)
            error_match = re.search(r'"error_msg":"(.*?)",', resp.text)
            if error_match:
                signin_error_msg = error_match.group(1)
        else:
            signin_error_msg = f"签到请求失败: HTTP {resp.status_code}"
        return sign_point, signin_error_msg

    def get_question(self):
        url = "https://pan.baidu.com/act/v2/membergrowv2/getdailyquestion?app_id=250528&web=5"
        resp = self.session.get(url, headers=self.headers, timeout=30)
        answer = None
        ask_id = None
        if resp.status_code == 200:
            answer_match = re.search(r'"answer":(\d+),', resp.text)
            if answer_match:
                answer = answer_match.group(1)
            ask_id_match = re.search(r'"ask_id":(\d+),', resp.text)
            if ask_id_match:
                ask_id = ask_id_match.group(1)
        return ask_id, answer

    def answer_question(self, ask_id, answer):
        url = (
            "https://pan.baidu.com/act/v2/membergrowv2/answerquestion"
            f"?app_id=250528&web=5&ask_id={ask_id}&answer={answer}"
        )
        resp = self.session.get(url, headers=self.headers, timeout=30)
        answer_score = None
        answer_msg = ""
        if resp.status_code == 200:
            score_match = re.search(r'"score":(\d+)', resp.text)
            if score_match:
                answer_score = score_match.group(1)
            msg_match = re.search(r'"show_msg":"(.*?)"', resp.text)
            if msg_match:
                answer_msg = msg_match.group(1)
        return answer_score, answer_msg

    def get_userinfo(self):
        url = "https://pan.baidu.com/rest/2.0/membership/user?app_id=250528&web=5&method=query"
        resp = self.session.get(url, headers=self.headers, timeout=30)
        current_value = None
        current_level = None
        if resp.status_code == 200:
            value_match = re.search(r'current_value":(\d+),', resp.text)
            if value_match:
                current_value = value_match.group(1)
            level_match = re.search(r'current_level":(\d+),', resp.text)
            if level_match:
                current_level = level_match.group(1)
        return current_level, current_value

    def run(self):
        sign_point, signin_error_msg = self.signin()
        time.sleep(3)
        ask_id, answer = self.get_question()
        answer_score, answer_msg = (None, "")
        if ask_id and answer:
            answer_score, answer_msg = self.answer_question(ask_id, answer)
        current_level, current_value = self.get_userinfo()
        return {
            "sign_point": sign_point,
            "signin_error_msg": signin_error_msg,
            "answer_score": answer_score,
            "answer_msg": answer_msg,
            "current_level": current_level,
            "current_value": current_value,
        }


def is_benign_signin_message(message: str) -> bool:
    normalized = (message or "").strip().lower()
    if not normalized:
        return True
    benign_markers = [
        "已签到",
        "repeat signin",
        "success",
    ]
    return any(marker in normalized for marker in benign_markers)


def is_benign_answer_message(message: str) -> bool:
    normalized = (message or "").strip().lower()
    if not normalized:
        return True
    benign_markers = [
        "已答",
        "重复答题",
        "repeat",
        "exceeded limit",
        "num exceeded limit",
    ]
    return any(marker in normalized for marker in benign_markers)


def load_accounts():
    raw = os.getenv("BAIDUWP_ACCOUNTS", "").strip()
    if not raw:
        raise ValueError("Missing BAIDUWP_ACCOUNTS secret")

    data = json.loads(raw)
    if not isinstance(data, list) or not data:
        raise ValueError("BAIDUWP_ACCOUNTS must be a non-empty JSON array")

    cookies = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Account #{index} must be a JSON object")
        cookie = str(item.get("cookie", "")).strip()
        if not cookie:
            raise ValueError(f"Account #{index} is missing cookie")
        cookies.append(cookie)
    return cookies


def build_account_lines(index: int, result: dict) -> list[str]:
    return [
        f"账号 {index}",
        f"签到: {result['sign_point'] or ''}{result['signin_error_msg'] or ''}",
        f"答题: {result['answer_score'] or ''}{result['answer_msg'] or ''}",
        f"等级/成长值: {result['current_level'] or ''}/{result['current_value'] or ''}",
    ]


def render_text_summary(results: list[dict], failed: bool, error_message: str = "") -> str:
    lines = []
    lines.append("百度网盘签到结果")
    lines.append(f"状态: {'失败' if failed else '成功'}")
    if error_message:
        lines.append(f"错误: {error_message}")

    for index, result in enumerate(results, start=1):
        lines.append("")
        lines.extend(build_account_lines(index, result))

    return "\n".join(lines)


def render_telegram_html(results: list[dict], failed: bool, error_message: str = "") -> str:
    lines = []
    lines.append("<b>百度网盘签到结果</b>")
    lines.append(f"状态: {'失败' if failed else '成功'}")
    if error_message:
        lines.append(f"错误: <code>{html.escape(error_message)}</code>")

    for index, result in enumerate(results, start=1):
        lines.append("")
        lines.append(f"<b>账号 {index}</b>")
        lines.append(
            f"签到: <code>{html.escape(str(result['sign_point'] or '') + str(result['signin_error_msg'] or ''))}</code>"
        )
        lines.append(
            f"答题: <code>{html.escape(str(result['answer_score'] or '') + str(result['answer_msg'] or ''))}</code>"
        )
        lines.append(
            f"等级/成长值: <code>{html.escape(str(result['current_level'] or ''))}/{html.escape(str(result['current_value'] or ''))}</code>"
        )

    return "\n".join(lines)


def send_telegram_message(message_html: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message_html,
            "parse_mode": "HTML",
        },
        timeout=30,
    )
    response.raise_for_status()


def build_feishu_sign(secret: str) -> tuple[str, str]:
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    sign = base64.b64encode(
        hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")
    return timestamp, sign


def send_feishu_message(message_text: str):
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    webhook_secret = os.getenv("FEISHU_WEBHOOK_SECRET", "").strip()
    if not webhook_url:
        return

    payload = {
        "msg_type": "text",
        "content": {
            "text": message_text,
        },
    }
    if webhook_secret:
        timestamp, sign = build_feishu_sign(webhook_secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign

    response = requests.post(webhook_url, json=payload, timeout=30)
    response.raise_for_status()


def send_notifications(results: list[dict], failed: bool, error_message: str = ""):
    telegram_message = render_telegram_html(results=results, failed=failed, error_message=error_message)
    feishu_message = render_text_summary(results=results, failed=failed, error_message=error_message)
    errors = []

    try:
        send_telegram_message(telegram_message)
    except Exception as exc:
        errors.append(f"Telegram 通知失败: {exc}")

    try:
        send_feishu_message(feishu_message)
    except Exception as exc:
        errors.append(f"飞书通知失败: {exc}")

    for error in errors:
        print(error)


def main():
    results = []
    failed = False
    error_message = ""

    try:
        cookies = load_accounts()

        for index, cookie in enumerate(cookies, start=1):
            result = BaiduWP(cookie).run()
            results.append(result)
            print(f"== Account {index} ==")
            print(
                "签到获得"
                f"{result['sign_point'] or ''}"
                f"{result['signin_error_msg'] or ''}"
            )
            print(
                "答题获得"
                f"{result['answer_score'] or ''}"
                f"{result['answer_msg'] or ''}"
            )
            print(
                f"当前会员等级{result['current_level'] or ''}，"
                f"成长值{result['current_value'] or ''}"
            )

            if not is_benign_signin_message(result["signin_error_msg"]):
                failed = True

            if not is_benign_answer_message(result["answer_msg"]):
                failed = True
    except Exception as exc:
        failed = True
        error_message = str(exc)
        print(f"执行失败: {error_message}")
    finally:
        send_notifications(results=results, failed=failed, error_message=error_message)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
