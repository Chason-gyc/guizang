"""Read public articles with an isolated browser, without user cookies."""
from urllib.parse import urlparse


def fetch_rendered_page(url: str) -> tuple[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ValueError("浏览器读取需要安装 playwright，并安装 Microsoft Edge") from exc
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True, ignore_default_args=["--headless=old"], args=["--headless=new"])
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                host = urlparse(url).hostname
                selector = "#content_views" if host == "blog.csdn.net" else "article"
                article = page.locator(selector).first
                article.wait_for(state="visible", timeout=15000)
                body = article.inner_text().strip()
                if len(body) < 100:
                    raise ValueError("浏览器未取得完整正文")
                return page.title(), body
            finally:
                browser.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("浏览器仍未取得正文，页面可能要求登录、验证或暂不可用") from exc
