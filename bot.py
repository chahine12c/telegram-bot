from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import re
import requests
import time
import hashlib
from urllib.parse import urlparse, parse_qs, unquote

BOT_TOKEN = "7754314760:AAGQo3ieE17vOibQUqcKmgTxIxuVYbYLKmw"
APP_KEY = "509038"
APP_SECRET = "gbDEssB1M3LYH8abuIQB57sQDrO47hln"
TRACKING_ID = "default"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Connection": "keep-alive"
}

def resolve_real_url(short_url):
    try:
        session = requests.Session()
        response = session.get(short_url, allow_redirects=True, timeout=10)
        for r in response.history + [response]:
            if "BundleDeals" in r.url or "/ssr/" in r.url:
                return r.url
        qs = parse_qs(urlparse(response.url).query)
        if "redirectUrl" in qs:
            return unquote(qs["redirectUrl"][0])
        return response.url
    except:
        return None

def extract_product_id(url: str):
    try:
        match = re.search(r'/item/(\d+)\.html', url)
        if match:
            return match.group(1)
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "productIds" in qs:
            return qs["productIds"][0].split(",")[0]
    except:
        pass
    return None

def get_title_from_item(product_id):
    try:
        url = f"https://www.aliexpress.com/item/{product_id}.html"
        resp = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'<meta property="og:title" content="([^"]+)"', resp.text)
        if match:
            return match.group(1)
    except:
        pass
    return "❌ ما قدرناش نجيبو عنوان المنتج."

def get_image_from_item(product_id):
    try:
        url = f"https://www.aliexpress.com/item/{product_id}.html"
        resp = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'<meta property="og:image" content="([^"]+)"', resp.text)
        if match:
            return match.group(1)
    except:
        pass
    return None

def generate_affiliate_link(original_url):
    timestamp = str(int(time.time() * 1000))
    api_url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.link.generate",
        "timestamp": timestamp,
        "sign_method": "md5",
        "format": "json",
        "v": "1.0",
        "promotion_link_type": "2",
        "source_values": original_url,
        "tracking_id": TRACKING_ID
    }

    def generate_signature(params, secret):
        sorted_params = sorted(params.items())
        base_string = secret + ''.join(f"{k}{v}" for k, v in sorted_params) + secret
        return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()

    params["sign"] = generate_signature(params, APP_SECRET)

    try:
        response = requests.get(api_url, params=params, timeout=10)
        data = response.json()
        return data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"]["promotion_link"][0]["promotion_link"]
    except:
        return None

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("http"):
        await update.message.reply_text("🔗 أرسل رابط من نوع AliExpress فقط.")
        return

    waiting = await update.message.reply_text("⏳ جاري معالجة الرابط...")

    real_url = resolve_real_url(text)
    if not real_url:
        await waiting.edit_text("❌ ما قدرناش نجيبو رابط حقيقي.")
        return

    product_id = extract_product_id(real_url)
    if not product_id:
        await waiting.edit_text("❌ ما قدرناش نستخرجو ID المنتج.")
        return

    title = get_title_from_item(product_id)
    image_url = get_image_from_item(product_id)

    urls = {
        "💸 رابط العملات المباشر": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=620&channel=coin",
        "💰 رابط العملات العامة": f"https://m.aliexpress.com/p/coin-index/index.html?productIds={product_id}",
        "🌐 رابط الباندل": f"https://www.aliexpress.com/ssr/300000512/BundleDeals2?productIds={product_id}",
        "🔥 رابط Super Deals": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=562",
        "🧨 رابط Big Save": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=680",
        "⚡ رابط العرض المحدود": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=561"
    }

    links = {label: generate_affiliate_link(url) for label, url in urls.items()}

    caption = f"🏷️ {title}\n\n"
    for label, link in links.items():
        if link:
            caption += f"{label}:\n{link}\n\n"

    await waiting.delete()
    if image_url:
        await update.message.reply_photo(image_url, caption=caption[:1024])
    else:
        await update.message.reply_text(caption.strip())

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ البوت شغال بنجاح على Render 🚀")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())