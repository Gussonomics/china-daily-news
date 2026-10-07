import os
import requests
import feedparser
from datetime import datetime
import pytz

# ========== Config ==========
def get_env(key):
    value = os.environ.get(key)
    if not value:
        print(f"❌ ERROR: {key} is not set!")
        print("   Please set it in GitHub Secrets")
        exit(1)
    return value

# รับค่าจาก GitHub Secrets
TELEGRAM_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_env("TELEGRAM_CHAT_ID")
DEEPSEEK_API_KEY = get_env("DEEPSEEK_API_KEY")

# ========== News Sources ==========
SOURCES = {
    "technology": ["https://www.techinasia.com/feed"],
    "economy": ["http://www.chinadaily.com.cn/rss/business_rss.xml"],
    "politics": ["https://www.scmp.com/rss/4/feed"]
}

# ========== 1. ดึงข่าว ==========
def fetch_news():
    print("📰 Fetching news from RSS feeds...")
    all_news = {}
    
    for category, feeds in SOURCES.items():
        articles = []
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:3]:
                    # เช็คว่าเกี่ยวกับจีน
                    text = f"{entry.title} {entry.get('summary', '')}".lower()
                    china_words = ["china", "chinese", "beijing", "shanghai", "จีน", "ปักกิ่ง"]
                    if any(word in text for word in china_words):
                        articles.append({
                            "title": entry.title[:150],
                            "link": entry.link,
                            "summary": entry.get('summary', '')[:100]
                        })
            except:
                continue
        
        all_news[category] = articles[:2]  # 2 ข่าวต่อ category
    
    return all_news

# ========== 2. สรุปด้วย DeepSeek ==========
def summarize_news(news):
    if not any(news.values()):
        return "วันนี้ไม่มีข่าวจีนใหม่จากแหล่งที่ติดตาม"
    
    print("🧠 Summarizing with DeepSeek AI...")
    
    # สร้าง prompt
    prompt = "สรุปข่าวจีนวันนี้เป็นภาษาไทย สั้นๆ อ่านง่าย:\n\n"
    for category, articles in news.items():
        if articles:
            prompt += f"{category}:\n"
            for article in articles:
                prompt += f"- {article['title']}\n"
    
    prompt += "\nคำสั่ง: สรุปเป็น 3 ส่วน (เทคโนโลยี/เศรษฐกิจ/การเมือง) แต่ละส่วน 2-3 บรรทัด ใช้ emoji"
    
    # เรียก API
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "คุณเป็นผู้ช่วยสรุปข่าวจีน"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            summary = response.json()["choices"][0]["message"]["content"]
            print("✅ Summary created!")
            return summary
        else:
            return f"API Error: {response.status_code}"
            
    except Exception as e:
        return f"Connection Error: {str(e)}"

# ========== 3. ส่ง Telegram ==========
def send_telegram(message):
    print("📤 Sending to Telegram...")
    
    # เพิ่ม header
    today = datetime.now(pytz.timezone('Asia/Bangkok')).strftime("%d/%m/%Y")
    full_message = f"🇨🇳 สรุปข่าวจีนประจำวัน\n📅 {today}\n\n{message}\n\nส่งจาก GitHub Actions 🤖"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": full_message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            print("✅ Sent to Telegram successfully!")
            return True
        else:
            print(f"❌ Telegram error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

# ========== 4. Main Function ==========
def main():
    print("=" * 50)
    print("🤖 China Daily News Bot")
    print("=" * 50)
    
    # 1. ดึงข่าว
    news = fetch_news()
    total = sum(len(articles) for articles in news.values())
    print(f"✅ Found {total} news articles")
    
    # 2. สรุปข่าว
    summary = summarize_news(news)
    
    # 3. ส่ง Telegram
    success = send_telegram(summary)
    
    if success:
        print("\n🎉 Mission accomplished!")
        return 0
    else:
        print("\n❌ Failed to send to Telegram")
        return 1

if __name__ == "__main__":
    exit(main())