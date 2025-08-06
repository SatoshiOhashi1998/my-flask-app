"""
メール処理モジュール

このモジュールは、IMAPを使用して未読のメールをチェックし、特定の送信者（YouTubeおよびTwitch）からのメールを処理します。
メールのHTMLボディを取得し、必要に応じてリンクを抽出してデフォルトのウェブブラウザで開く機能を提供します。

使用方法:
1. 環境変数 'EMAIL_USERNAME', 'EMAIL_PASSWORD', 'IMAP_SERVER' にメールアカウントの情報を設定します。
2. このスクリプトを実行すると、未読メールがチェックされ、特定の条件を満たすメールが処理されます。

依存関係:
- imaplib: IMAPプロトコルを使用するための標準ライブラリ。
- email: メールメッセージの解析と処理のための標準ライブラリ。
- email.header: メールヘッダーのデコードに使用される標準ライブラリ。
- webbrowser: デフォルトのウェブブラウザを使用してURLを開くための標準ライブラリ。
- bs4 (BeautifulSoup): HTML/XMLを解析するためのサードパーティライブラリ。
- os: 環境変数の取得に使用される標準ライブラリ。
- datetime: 日付と時刻を操作するための標準ライブラリ。
- traceback: エラーのトレースバックを取得するための標準ライブラリ。
- html: HTMLの特殊文字を処理するための標準ライブラリ。

エラーログ:
- エラーや情報メッセージは、それぞれ "errorMsg.txt" および "infoMsg.txt" にログとして出力されます。

"""

import imaplib
import email
from email.header import decode_header
import webbrowser
from bs4 import BeautifulSoup, Comment
import os
from datetime import datetime, timedelta
import traceback
import html

# 環境変数からメールアカウントの情報を取得
username = os.getenv('EMAIL_USERNAME')
password = os.getenv('EMAIL_PASSWORD')
imap_server = os.getenv('IMAP_SERVER')

if not all([username, password, imap_server]):
    raise ValueError("メールアカウントの情報が環境変数に設定されていません。")

def log_error(message):
    with open("errorMsg.txt", "a") as error_file:
        error_file.write(f"{datetime.now()} - ERROR: {message}\n")

def log_info(message):
    with open("infoMsg.txt", "a") as info_file:
        info_file.write(f"{datetime.now()} - INFO: {message}\n")

def fetch_html_body(msg):
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            charset = part.get_content_charset()
            return part.get_payload(decode=True).decode(charset or 'utf-8')
    return None

def sanitize_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # 不要なタグを削除
    for script in soup(["script", "style", "iframe", "embed", "object", "applet"]):
        script.decompose()

    # コメントを削除
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # hrefやsrc属性の確認（XSS攻撃対策）
    for tag in soup.findAll(True):
        for attribute in ["href", "src"]:
            if attribute in tag.attrs:
                value = tag[attribute]
                if not value.startswith(('http://', 'https://', 'mailto:')):
                    tag[attribute] = '#'

    return str(soup)

def check_email():
    try:
        log_info("IMAPサーバに接続を試みます")
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        mail.select("inbox")
        log_info("IMAPサーバに接続しました")
    except Exception as e:
        log_error(f"IMAP接続エラー: {traceback.format_exc()}")
        return

    try:
        log_info("メールを検索します")
        yesterday = (datetime.now() - timedelta(1)).strftime("%d-%b-%Y")
        result, email_ids = mail.search(None, '(UNSEEN SINCE {0})'.format(yesterday))
        if result != "OK":
            log_error(f"メール検索エラー: {result}")
            return
        email_ids = email_ids[0].split()
        log_info(f"未読メール数: {len(email_ids)}")
    except Exception as e:
        log_error(f"メール検索中のエラー: {traceback.format_exc()}")
        return

    for email_id in email_ids:
        try:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                log_error(f"メールフェッチエラー: {status}")
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    sender = msg["From"]

                    if sender and 'noreply@youtube.com' in sender:
                        handle_youtube_email(msg)
                    elif sender and 'no-reply@twitch.tv' in sender:
                        handle_twitch_email(msg)
        except Exception as e:
            log_error(f"メール処理中のエラー (ID: {email_id}): {traceback.format_exc()}")

    log_info("メール処理が完了しました")
    try:
        mail.close()
        mail.logout()
    except Exception as e:
        log_error(f"IMAP切断エラー: {traceback.format_exc()}")

def handle_youtube_email(msg):
    try:
        html_body = fetch_html_body(msg)
        if html_body:
            sanitized_html = sanitize_html(html_body)
            urls = extract_links(sanitized_html, 'watch')
            for url in urls:
                log_info(f"YouTube URL: {url}")
                webbrowser.open(url)
                break
    except Exception as e:
        log_error(f"YouTubeメール処理中のエラー: {traceback.format_exc()}")

def handle_twitch_email(msg):
    try:
        html_body = fetch_html_body(msg)
        if html_body:
            sanitized_html = sanitize_html(html_body)
            urls = extract_links_with_text(sanitized_html, '今すぐ視聴')
            for url in urls:
                log_info(f"Twitch URL: {url}")
                webbrowser.open(url)
                break
    except Exception as e:
        log_error(f"Twitchメール処理中のエラー: {traceback.format_exc()}")

def extract_links(html_body, keyword):
    soup = BeautifulSoup(html_body, "html.parser")
    return [link["href"] for link in soup.find_all("a", href=True) if keyword in link.get("href", "")]

def extract_links_with_text(html_body, text):
    soup = BeautifulSoup(html_body, "html.parser")
    return [link["href"] for link in soup.find_all("a", href=True) if link.get_text(strip=True) == text]

if __name__ == '__main__':
    check_email()
