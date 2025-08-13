import schedule
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import feedparser
from transformers import pipeline
import os

# RSS feed sources
industry_news_sources = [
    'https://www.artnews.com/feed',
    'https://variety.com/feed/',
    'https://wwd.com/feed/',
    'https://wwd.com/menswear-news/feed/',
    'https://wwd.com/footwear-news/feed/',
    'https://wwd.com/beauty-industry-news/feed/',
    'https://www.hollywoodreporter.com/feed/',
    'https://www.adweek.com/feed/',
    'https://feeds.harvardbusiness.org/harvardbusiness',
    'https://www.commarts.com/feed/',
    'https://animationmagazine.net/feed/',
    'https://core77.com/blog/rss.xml',
    'https://gamedeveloper.com/rss.xml',
    'https://awn.com/news/rss.xml',
]

# Sites without RSS feeds for scraping
additional_sites = [
    'https://www.voguebusiness.com/',
    'https://www.vogue.com/',
    'https://www.architecturalrecord.com/',
    'https://luxurydaily.com/',
    'https://interiordesign.net/',
    'https://sourcingjournal.com/',
    'https://hospitalitydesign.com/',
    'https://www.textiles.org/',
    'https://instoremag.com/',
    'https://xra.org/',
    'https://www.bifma.org/',
]

# Initialize summarizer (load once)
summarizer = None

def get_summarizer():
    global summarizer
    if summarizer is None:
        print("Loading summarizer model...")
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    return summarizer

def filter_for_industry_insights(title, text_preview=""):
    """Filter for strategic industry insights"""
    title_lower = title.lower()
    text_preview_lower = text_preview.lower() if text_preview else ""
    
    # Strategic keywords based on your research interests
    industry_insight_keywords = [
        'market report', 'industry report', 'state of', 'outlook', 'forecast',
        'market analysis', 'trend report', 'market outlook', 'industry outlook',
        'slowdown', 'headwinds', 'economic', 'disruptions', 'growth',
        'sales expected', 'market to stay', 'confronts', 'doldrums',
        'industry not doing well', 'market softens', 'flat in 2025',
        'remain flat', 'industry resilience', 'market disruptions',
        'future of', 'trends to watch', 'six disruptions', 'next decade',
        'transforming', 'scaling', 'market could reach',
        'executives need to know', 'what to watch', 'priorities in',
        'strategies defining', 'leaders will soon', 'market penetration',
        'retailers', 'prices', 'tariff', 'revenue'
    ]
    
    # Exclude company-specific news
    exclude_company_news = [
        'announces', 'launches', 'hires', 'opens', 'partnership with',
        'ceo says', 'company reports', 'names new', 'appoints',
        'ralph lauren', 'mascot', 'art thief', 'animated film', 'polo bear',
        'crunchyroll', 'layoffs', 'member groups', 'steel city interactive',
        'undisputed developer', 'leamington studio', 'unionized', 'team has'
    ]
    
    # Check exclusions first
    combined_text = title_lower + " " + text_preview_lower
    for exclusion in exclude_company_news:
        if exclusion in combined_text:
            return False
    
    # Check for strategic keywords
    for keyword in industry_insight_keywords:
        if keyword in title_lower or keyword in text_preview_lower:
            return True
    
    return False

def get_article_text(url):
    """Extract article text from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find the title
        title = soup.find('title')
        title = title.get_text().strip() if title else "No title found"
        
        # Try to find article content
        content_selectors = ['article', '.article-body', '.story-body', '.content', 'p']
        
        text = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                text = ' '.join([elem.get_text().strip() for elem in elements])
                break
        
        # Clean up the text
        text = ' '.join(text.split())
        
        return title, text[:3000]  # Limit length
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None, None

def get_latest_articles(rss_url, limit=5):
    """Get latest articles from RSS feed"""
    try:
        feed = feedparser.parse(rss_url)
        articles = []
        
        for entry in feed.entries[:limit]:
            articles.append({
                'title': entry.title,
                'url': entry.link
            })
        return articles
    except Exception as e:
        print(f"Error parsing RSS feed {rss_url}: {e}")
        return []

def scrape_site_headlines(url):
    """Scrape headlines from sites without RSS"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for headlines
        headline_selectors = [
            'h1 a', 'h2 a', 'h3 a',
            '.headline a', '.title a',
            'article h1', 'article h2'
        ]
        
        headlines = []
        for selector in headline_selectors:
            elements = soup.select(selector)[:3]
            for elem in elements:
                href = elem.get('href')
                title = elem.get_text().strip()
                if href and title and len(title) > 10:
                    if href.startswith('/'):
                        href = url.rstrip('/') + href
                    elif href.startswith('http'):
                        pass
                    else:
                        continue
                    
                    headlines.append({
                        'title': title,
                        'url': href
                    })
            if headlines:
                break
        
        return headlines[:2]
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def run_industry_insights_agent():
    """Main agent function to gather industry insights"""
    print("🚀 Starting industry insights agent...")
    industry_headlines = []
    
    # Process RSS feeds
    print("📡 Processing RSS feeds...")
    for source in industry_news_sources:
        print(f"Checking: {source}")
        articles = get_latest_articles(source, 5)
        
        for article in articles:
            title, text_preview = get_article_text(article['url'])
            if title:
                preview = text_preview[:200] if text_preview else ""
                
                if filter_for_industry_insights(title, preview):
                    industry_headlines.append({
                        'title': title,
                        'url': article['url'],
                        'source': source
                    })
            
            time.sleep(1)
    
    # Process additional sites
    print("🌐 Processing additional sites...")
    for site in additional_sites:
        print(f"Scraping: {site}")
        headlines = scrape_site_headlines(site)
        
        for headline in headlines:
            title, text_preview = get_article_text(headline['url'])
            if title:
                preview = text_preview[:200] if text_preview else ""
                
                if filter_for_industry_insights(title, preview):
                    industry_headlines.append({
                        'title': title,
                        'url': headline['url'],
                        'source': site
                    })
            
            time.sleep(2)
    
    return industry_headlines

def send_weekly_email(insights):
    """Send the weekly email with insights"""
    gmail_address = os.environ.get('GMAIL_ADDRESS')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
    
    if not gmail_address or not gmail_password:
        print("❌ Gmail credentials not found in environment variables")
        return False
    
    try:
        # Create HTML message
        msg = MIMEMultipart('alternative')
        msg['From'] = gmail_address
        msg['To'] = "jfunderb@scad.edu"
        msg['Subject'] = "Josh's Weekly Market Insights Report"
        
        # HTML email body with your formatting
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; margin: 20px; line-height: 1.15; }}
        .title {{ font-size: 16pt; font-weight: bold; color: #003366; text-align: left; margin-bottom: 10px; }}
        .date {{ font-size: 11pt; color: #555555; text-align: left; margin-bottom: 20px; }}
        .divider {{ border-bottom: 1px solid #003366; margin-bottom: 30px; }}
        .section-header {{ font-size: 14pt; font-weight: bold; color: #003366; margin-bottom: 20px; }}
        .headline {{ margin-bottom: 25px; font-size: 11pt; }}
        .headline-title {{ font-weight: bold; color: #003366; margin-bottom: 8px; }}
        .headline-url {{ color: #00AEEF; }}
        .footer {{ background-color: #f5f5f5; padding: 15px; margin-top: 30px; border-left: 4px solid #00AEEF; }}
    </style>
</head>
<body>
    <div class="title">WEEKLY MARKET INSIGHTS REPORT</div>
    <div class="date">Date: {datetime.now().strftime('%B %d, %Y')}</div>
    <div class="divider"></div>
    
    <div class="section-header">📰 Strategic Industry Headlines & Market Intelligence</div>
"""
        
        # Add headlines
        for i, item in enumerate(insights, 1):
            html_body += f"""
    <div class="headline">
        <div class="headline-title">{i}. {item['title']}</div>
        <div class="headline-url">{item['url']}</div>
    </div>
"""
        
        # Add footer
        html_body += """
    <div class="footer">
        <strong>About This Report:</strong> This automated briefing scans 28+ leading industry publications each week to deliver strategic business intelligence for decision-makers.
    </div>
</body>
</html>
"""
        
        # Send email
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, "jfunderb@scad.edu", msg.as_string())
        server.quit()
        
        print(f"✅ Weekly email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def automated_weekly_report():
    """The complete automated weekly process"""
    print(f"🚀 AUTOMATED WEEKLY REPORT - {datetime.now()}")
    
    try:
        # Get insights
        insights = run_industry_insights_agent()
        
        if insights:
            print(f"📊 Found {len(insights)} strategic insights")
            # Send email
            send_weekly_email(insights)
        else:
            print("❌ No insights found this week")
            
    except Exception as e:
        print(f"❌ Weekly report error: {e}")

def main():
    """Main function for cloud deployment"""
    print("🚀 Starting Weekly News Agent on Google Cloud...")
    
    # Schedule the weekly report
    schedule.every().monday.at("08:00").do(automated_weekly_report)
    
    print("⏰ Scheduler active - running every Monday at 8:00 AM")
    
    # Run once immediately for testing
    print("🧪 Running test report...")
    automated_weekly_report()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

if __name__ == "__main__":
    main()
