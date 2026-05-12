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


def main():
    cookies = load_accounts()
    failed = False

    for index, cookie in enumerate(cookies, start=1):
        result = BaiduWP(cookie).run()
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

        if (
            result["signin_error_msg"]
            and "已签到" not in result["signin_error_msg"]
            and "success" not in result["signin_error_msg"].lower()
        ):
            failed = True

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
