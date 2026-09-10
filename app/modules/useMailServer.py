"""
メール処理モジュール

IMAPサーバーから未読メールを取得し、
YouTubeやTwitchからの通知メールに含まれるURLを処理します。
"""

import imaplib
import email
from email.header import decode_header
import webbrowser
from bs4 import BeautifulSoup, Comment
import os
from datetime import datetime, timedelta
import html
import logging


logger = logging.getLogger(__name__)


username = os.getenv('EMAIL_USERNAME')
password = os.getenv('EMAIL_PASSWORD')
imap_server = os.getenv('IMAP_SERVER')


if not all([username, password, imap_server]):
    raise ValueError("メールアカウントの情報が環境変数に設定されていません。")


def fetch_html_body(msg):
    """
    メール本文からHTML部分を取得する。
    """
    html_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if (
                content_type == "text/html"
                and "attachment" not in content_disposition
            ):
                try:
                    html_body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8",
                        errors="replace"
                    )
                except Exception:
                    logger.exception("HTMLメール本文のデコード中にエラーが発生しました")

                break

    elif msg.get_content_type() == "text/html":
        try:
            html_body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8",
                errors="replace"
            )
        except Exception:
            logger.exception("HTMLメール本文のデコード中にエラーが発生しました")

    return html_body


def sanitize_html(html_content):
    """
    HTMLから不要な要素を削除する。
    """
    soup = BeautifulSoup(html_content, "html.parser")

    for element in soup(["script", "style"]):
        element.decompose()

    for comment in soup.find_all(
        string=lambda text: isinstance(text, Comment)
    ):
        comment.extract()

    return str(soup)


def check_email():
    """
    IMAPサーバーに接続し、未読メールを処理する。
    """
    try:
        logger.info("IMAPサーバに接続を試みます")

        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        mail.select("inbox")

        logger.info("IMAPサーバに接続しました")

    except Exception:
        logger.exception("IMAP接続エラー")
        return

    try:
        logger.info("メールを検索します")

        yesterday = (
            datetime.now() - timedelta(1)
        ).strftime("%d-%b-%Y")

        result, email_ids = mail.search(
            None,
            f"(UNSEEN SINCE {yesterday})"
        )

        if result != "OK":
            logger.error(f"メール検索エラー: {result}")
            return

        email_ids = email_ids[0].split()

        logger.info(f"未読メール数: {len(email_ids)}")

    except Exception:
        logger.exception("メール検索中のエラー")
        return

    for email_id in email_ids:
        try:
            status, msg_data = mail.fetch(
                email_id,
                "(RFC822)"
            )

            if status != "OK":
                logger.error(
                    f"メールフェッチエラー: {status}"
                )
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(
                        response_part[1]
                    )

                    sender = msg["From"]

                    if sender and "noreply@youtube.com" in sender:
                        handle_youtube_email(msg)

                    elif sender and "no-reply@twitch.tv" in sender:
                        handle_twitch_email(msg)

        except Exception:
            logger.exception(
                f"メール処理中のエラー (ID: {email_id})"
            )

    logger.info("メール処理が完了しました")

    try:
        mail.close()
        mail.logout()

    except Exception:
        logger.exception("IMAP切断エラー")


def handle_youtube_email(msg):
    """
    YouTubeからのメールを処理する。
    """
    try:
        # 元のYouTubeメール処理
        # ...

        logger.info(f"YouTube URL: {url}")

        webbrowser.open(url)

    except Exception:
        logger.exception("YouTubeメール処理中のエラー")


def handle_twitch_email(msg):
    """
    Twitchからのメールを処理する。
    """
    try:
        # 元のTwitchメール処理
        # ...

        logger.info(f"Twitch URL: {url}")

        webbrowser.open(url)

    except Exception:
        logger.exception("Twitchメール処理中のエラー")


def extract_links(html_content):
    """
    HTMLからリンクを抽出する。
    """
    # 元の処理をそのまま使用
    ...


def extract_links_with_text(html_content):
    """
    HTMLからリンクとテキストを抽出する。
    """
    # 元の処理をそのまま使用
    ...


if __name__ == "__main__":
    check_email()
