#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""读取公开微信公众号文章（mp.weixin.qq.com/s/...），输出 Markdown/JSON。

用法：
    python wechat_read.py "https://mp.weixin.qq.com/s/..."
    python wechat_read.py "<url>" --json

只读公开文章；不读聊天记录、不自动化微信搜一搜。
如果微信返回反爬/验证页，脚本会输出空内容并提示“请人贴正文/截图”。
"""
import argparse
import datetime
import html as htmlmod
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


MAX_PAGE_BYTES = 5 * 1024 * 1024


def fetch(url, timeout=30):
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "mp.weixin.qq.com":
        raise ValueError("only https://mp.weixin.qq.com URLs are allowed")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        final = urlparse(resp.geturl())
        if final.scheme != "https" or (final.hostname or "").lower() != "mp.weixin.qq.com":
            raise ValueError("redirected outside https://mp.weixin.qq.com")
        raw = resp.read(MAX_PAGE_BYTES + 1)
        if len(raw) > MAX_PAGE_BYTES:
            raise ValueError("page too large (>5MB)")
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, "ignore")


class ContentParser(HTMLParser):
    """收集 <div id="js_content"> 内的文本，处理嵌套 div。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_content = False
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and attrs.get("id") == "js_content":
            self.in_content = True
            self.depth = 1
            return
        if not self.in_content:
            return
        if tag == "div":
            self.depth += 1
        elif tag in ("p", "br", "section"):
            self.parts.append("\n")
        elif tag in ("li",):
            self.parts.append("\n- ")
        elif tag in ("h1", "h2", "h3", "h4"):
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if not self.in_content:
            return
        if tag == "div":
            self.depth -= 1
            if self.depth <= 0:
                self.in_content = False
        elif tag in ("p", "section", "li"):
            self.parts.append("\n")
        elif tag in ("h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_content:
            self.parts.append(data)


def strip_tags(s):
    s = re.sub(r"<script.*?</script>", "", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", "", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>", "\n\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extract(page):
    title = None
    m = re.search(r'<h1[^>]*id="activity-name"[^>]*>(.*?)</h1>', page, re.S)
    if m:
        title = strip_tags(m.group(1))

    account = None
    m = re.search(r'id="js_name"[^>]*>(.*?)</a>', page, re.S)
    if m:
        account = strip_tags(m.group(1))

    date = None
    m = re.search(r'var ct = "(\d+)"', page)
    if m:
        try:
            date = datetime.datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d")
        except Exception:
            pass

    parser = ContentParser()
    parser.feed(page)
    content = "".join(parser.parts)
    content = re.sub(r"[ \t]+", " ", content)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()

    # 反爬/验证页识别
    blocked = (
        "环境异常" in page
        or "完成验证" in page
        or "access_denied" in page
        or not content
    )
    return {
        "url": "",
        "title": title,
        "account": account,
        "date": date,
        "content": content,
        "images": [],
        "image_ocr": [],
        "blocked": blocked,
    }


def extract_images(page):
    urls = []
    for m in re.finditer(r'<img[^>]+(?:data-src|src)="([^"]+)"', page, re.I):
        u = htmlmod.unescape(m.group(1))
        host = (urlparse(u).hostname or "").lower()
        if u.startswith("http") and (host == "mmbiz.qpic.cn" or host.endswith(".mmbiz.qpic.cn")):
            if u not in urls:
                urls.append(u)
    return urls


def download_image(url, path):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "mmbiz.qpic.cn" or host.endswith(".mmbiz.qpic.cn")):
        raise ValueError("only https://mmbiz.qpic.cn images are allowed")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        final = urlparse(resp.geturl())
        fhost = (final.hostname or "").lower()
        if final.scheme != "https" or not (fhost == "mmbiz.qpic.cn" or fhost.endswith(".mmbiz.qpic.cn")):
            raise ValueError("image redirected outside https://mmbiz.qpic.cn")
        data = resp.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("image too large (>10MB)")
    with open(path, "wb") as f:
        f.write(data)


def ocr_images(urls, outdir, limit=30):
    from rapidocr_onnxruntime import RapidOCR
    os.makedirs(outdir, exist_ok=True)
    engine = RapidOCR()
    rows = []
    for i, url in enumerate(urls[:limit], 1):
        path = os.path.join(outdir, f"img_{i:02d}.jpg")
        try:
            download_image(url, path)
            result, _ = engine(path)
            text = "\n".join(t for _, t, _ in result or [])
        except Exception as e:
            text = f"[OCR error: {type(e).__name__}]"
        rows.append({"url": url, "path": path, "text": text})
    return rows


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ocr-images", action="store_true",
                    help="下载文章图片并 OCR（奖项名单常在图里）")
    ap.add_argument("--image-dir", default="wechat_images")
    args = ap.parse_args()

    parsed = urlparse(args.url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "mp.weixin.qq.com":
        print("only https://mp.weixin.qq.com URLs are allowed", file=sys.stderr)
        sys.exit(1)

    image_dir = os.path.abspath(args.image_dir)
    cwd = os.path.abspath(os.getcwd())
    try:
        inside = os.path.commonpath([image_dir, cwd]) == cwd
    except ValueError:
        inside = False
    if not inside:
        print("image-dir must be inside the current working directory", file=sys.stderr)
        sys.exit(1)
    args.image_dir = image_dir
    try:
        page = fetch(args.url)
    except Exception as e:
        print(f"fetch error: {e}", file=sys.stderr)
        sys.exit(1)
    data = extract(page)
    data["url"] = args.url
    data["images"] = extract_images(page)
    if args.ocr_images:
        data["image_ocr"] = ocr_images(data["images"], args.image_dir)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("#", data["title"] or "(no title)")
        print("Account:", data["account"] or "(unknown)")
        print("Date:", data["date"] or "(unknown)")
        print("Blocked:", data["blocked"])
        print()
        print(data["content"][:20000])
        if data["image_ocr"]:
            print("\n## 图片 OCR")
            for i, row in enumerate(data["image_ocr"], 1):
                print(f"\n### 图片 {i}\n{row['text'][:4000]}")
    if data["blocked"]:
        print("\n[!] 内容为空或被验证页拦截：请人贴正文/截图，不要重试超过 2 次。",
              file=sys.stderr)


if __name__ == "__main__":
    main()
