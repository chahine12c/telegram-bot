from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import requests
import time
import hashlib
import re
from urllib.parse import urlparse, parse_qs, unquote

BOT_TOKEN = "7754314760:AAGQo3ieE17vOibQUqcKmgTxIxuVYbYLKmw"
APP_KEY = "509038"
APP_SECRET = "gbDEssB1M3LYH8abuIQB57sQDrO47hln"
TRACKING_ID = "default"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Connection": "keep-alive"
}

def resolve_real_url(short_url):
    try:
        res = requests.get(short_url, allow_redirects=True, timeout=6)
        for r in res.history + [res]:
            if "BundleDeals" in r.url or "/ssr/" in r.url:
                return r.url
        qs = parse_qs(urlparse(res.url).query)
        if "redirectUrl" in qs:
            return unquote(qs["redirectUrl"][0])
        return res.url
    except:
        return None

def extract_product_id(url: str):
    match = re.search(r'/item/(\d+)\.html', url)
    if match:
        return match.group(1)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "productIds" in qs:
        return qs["productIds"][0].split(",")[0]
    return None

def get_title_image_price(product_id):
    try:
        url = f"https://www.aliexpress.com/item/{product_id}.html"
        res = requests.get(url, headers=HEADERS, timeout=10)
        html = res.text
        title_match = re.search(r'<meta property="og:title" content="([^"]+)">', html)
        image_match = re.search(r'<meta property="og:image" content="([^"]+)">', html)
        price_match = re.search(r'"price":\{"value":"(\d+\.\d+)"', html)

        title = title_match.group(1) if title_match else "❌ ما قدرناش نجيبو عنوان المنتج."
        image = image_match.group(1) if image_match else None
        price = price_match.group(1) + " $" if price_match else "❌ السعر غير متوفر"
        return title, image, price
    except:
        return "❌ ما قدرناش نجيبو عنوان المنتج.", None, "❌ السعر غير متوفر"

def generate_affiliate_link(url):
    try:
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
            "source_values": url,
            "tracking_id": TRACKING_ID
        }

        def generate_signature(params, secret):
            sorted_params = sorted(params.items())
            base_string = secret + ''.join(f"{k}{v}" for k, v in sorted_params) + secret
            return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()

        params["sign"] = generate_signature(params, APP_SECRET)
        res = requests.get(api_url, params=params, timeout=8)
        data = res.json()
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
        await waiting.edit_text("❌ ما قدرناش نجيبو رابط المنتج الحقيقي.")
        return

    product_id = extract_product_id(real_url)
    if not product_id:
        await waiting.edit_text("❌ ما قدرناش نستخرجو ID المنتج.")
        return

    title, image, price = get_title_image_price(product_id)

    urls = {
        "💸 رابط العملات المباشر": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=620&channel=coin",
        "💰 رابط العملات العامة": f"https://m.aliexpress.com/p/coin-index/index.html?productIds={product_id}",
        "🌐 رابط الباندل": f"https://www.aliexpress.com/ssr/300000512/BundleDeals2?productIds={product_id}",
        "🔥 رابط Super Deals": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=562",
        "🧨 رابط Big Save": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=680",
        "⚡ رابط العرض المحدود": f"https://vi.aliexpress.com/item/{product_id}.html?sourceType=561"
    }

    caption = f"🏷️ {title}\n💵 السعر: {price}\n\n"
    for label, url in urls.items():
        link = generate_affiliate_link(url)
        if link and len(caption + f"{label}:\n{link}\n\n") < 1000:
            caption += f"{label}:\n{link}\n\n"

    await waiting.delete()
    if image:
        await update.message.reply_photo(image, caption=caption.strip()[:1024])
    else:
        await update.message.reply_text(caption.strip())

# تشغيل البوت
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
print("✅ البوت شغال على Render ويجيب العنوان والسعر والصورة")
app.run_polling()
