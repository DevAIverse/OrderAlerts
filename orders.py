import requests
import json
import time
import datetime
import yfinance as yf
import os
import csv
import PyPDF2
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===================== Configuration =====================
BSE_API_URL = os.getenv("BSE_API_URL")
BSE_PDF_BASE_URL_LIVE = os.getenv("BSE_PDF_BASE_URL_LIVE")
BSE_PDF_BASE_URL_HIST = os.getenv("BSE_PDF_BASE_URL_HIST")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL")
    
# Filter limits (in crores)
MIN_MKCAP = int(os.getenv("MIN_MKCAP"))
MAX_MKCAP = int(os.getenv("MAX_MKCAP"))

# Poll interval in seconds
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL"))

# File paths
PROCESSED_FILE = "processed_announcements.json"
LOG_FILE = "ai_logs.csv"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_BOT_TOKEN_2 = os.getenv("TELEGRAM_BOT_TOKEN_2")
TELEGRAM_CHAT_ID_2 = os.getenv("TELEGRAM_CHAT_ID_2")

# Cerebras system prompt
SYSTEM_PROMPT = """
You are a financial order impact analyzer.
Task: Read the SEBI disclosure text and return ONLY JSON with:

{
  "impact_note": "<Impact label + Order amount + Order % of Revenue + Duration + witty remark>"
}

Instructions:
- Extract Order Amount (crores) and Duration (months) from the text.
- Use Revenue and MarketCap provided in the user prompt.
- Compute Order % of Revenue = (Order Amount / Revenue) * 100.
- Apply rules:
  - If Order % > 20% AND Duration ≤ 24 → BIG
  - If Order % > 20% AND Duration > 24 → MEDIUM
  - If 10% ≤ Order % ≤ 20% → MEDIUM
  - If Order % < 10% → SMALL
- The impact_note must include:
  - The impact label (BIG / MEDIUM / SMALL)
  - The extracted Order amount (crores)
  - The computed Order % of Revenue
  - The extracted Duration (months)
  - A short witty remark (casual tone, emoji allowed)
- Keep the response concise, single-line JSON.
"""





# ===================== Helper Functions =====================

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r") as f:
            return json.load(f).get("processed", [])
    return []

def save_processed(processed_list):
    with open(PROCESSED_FILE, "w") as f:
        json.dump({"processed": processed_list}, f)

def log_ai_output(timestamp, company, sc_code, impact, telegram_sent, ai_note, tokens_used=0):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Company", "SC_CODE", "Impact", "Telegram Sent", "Tokens Used", "AI Note"])
        writer.writerow([timestamp, company, sc_code, impact, telegram_sent, tokens_used, ai_note])

def fetch_bse_announcements():
    """
    Fetch today's 'Receipt of Order' announcements from BSE with pagination.
    Returns a list of announcement dicts.
    """
    today = datetime.date.today()
    date_str = today.strftime("%Y%m%d")  # BSE API expects YYYYMMDD format
    prev_str = '20250913'  # Fixed past date to ensure full day coverage

    page = 1
    all_results = []

    while True:
        params = {
            "pageno": page,
            "strCat": "Company Update",
            "strPrevDate": prev_str,
            "strToDate": date_str,
            "strScrip": "",
            "strSearch": "P",     # Press release / PDF
            "strType": "C",
            "subcategory": "Award of Order / Receipt of Order"  # Filter for orders
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Referer": "https://www.bseindia.com/",
            "Origin": "https://www.bseindia.com",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }

        try:
            resp = requests.get(BSE_API_URL, headers=headers, params=params, timeout=10)
            if resp.status_code == 404:
                break  # No more pages available
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as req_err:
            print(f"❌ Request failed on page {page}: {req_err}")
            break
        except ValueError as json_err:
            print(f"❌ Failed to decode JSON (Page {page}): {json_err}")
            break

        announcements = data.get("Table", [])
        if not announcements:
            break

        all_results.extend(announcements)
        page += 1  # Move to next page

    print(f"📰 Fetched {len(all_results)} 'Receipt of Order' announcements for {date_str}")
    return all_results

def extract_pdf_text(pdf_filename):
    """Download and extract text from BSE PDF"""
    if not pdf_filename:
        return "No PDF attachment available"
    
    # Try AttachLive first, then AttachHist
    base_urls = [
        BSE_PDF_BASE_URL_LIVE,
        BSE_PDF_BASE_URL_HIST
    ]
    
    for base_url in base_urls:
        pdf_url = f"{base_url}{pdf_filename}"
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bseindia.com/"
            }
            resp = requests.get(pdf_url, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                # Extract text using PyPDF2
                pdf_file = io.BytesIO(resp.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                if text.strip():
                    return text.strip()
        
        except Exception as e:
            continue
    
    return "Failed to download PDF from both AttachLive and AttachHist"

def search_nse_symbol(company_name):
    # Clean company name by removing common suffixes
    clean_name = company_name
    suffixes = [" Ltd", " Limited", " Pvt Ltd", " Private Limited", "-$"]
    for suffix in suffixes:
        clean_name = clean_name.replace(suffix, "")
    clean_name = clean_name.strip()
    
    url = f"https://www.nseindia.com/api/search/autocomplete?q={clean_name}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/"
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        symbols = data.get("symbols", [])
        for s in symbols:
            if s.get("result_sub_type") == "equity":
                return s.get("symbol")
    except:
        pass
    return None

def get_financials(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        mkcap = info.get("marketCap", 0) / 1e7  # in crores
        revenue = info.get("totalRevenue", 0) / 1e7  # in crores
        return mkcap, revenue
    except Exception as e:
        print(f"❌ Error fetching financials for {symbol}: {e}")
        return None, None

def call_cerebras_api(user_prompt, timeout=10):
    headers = {
        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 5000,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        tokens_used = result.get("usage", {}).get("total_tokens", 0)
        return content, tokens_used
    except Exception as e:
        print(f"❌ Error calling Cerebras API: {e}")
        return None, 0

def send_telegram_alert(message):
    success_count = 0
    
    # Send to first bot
    url1 = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data1 = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        resp1 = requests.post(url1, data=data1)
        if resp1.status_code == 200:
            success_count += 1
    except:
        pass
    
    # Send to second bot
    url2 = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_2}/sendMessage"
    data2 = {"chat_id": TELEGRAM_CHAT_ID_2, "text": message}
    try:
        resp2 = requests.post(url2, data=data2)
        if resp2.status_code == 200:
            success_count += 1
    except:
        pass
    
    return success_count > 0

# ===================== Main Loop =====================

if __name__ == "__main__":
    processed_announcements = load_processed()
    
    while True:
        announcements = fetch_bse_announcements()
        
        print(f"📰 Found {len(announcements)} announcements ")
        
        for i, ann in enumerate(announcements):
            # Debug: Print first announcement structure
            if i == 0:
                print(f"📋 Sample announcement keys: {list(ann.keys())}")
            
            sc_code = ann.get("SCRIP_CD")
            company_name = ann.get("SLONGNAME")
            ann_date = ann.get("DT_TM", "")
            print(company_name)
            ann_id = ann.get("NEWSID", "")
            
            # Skip if essential data is missing
            if not sc_code or not company_name:
                print(f"⚠️ Skipping announcement {i+1}: Missing SCRIP_CD or SLONGNAME")
                continue
                
            unique_id = f"{sc_code}_{ann_id}"
            
            if unique_id in processed_announcements:
                print(f"⏭️ Skipping already processed: {company_name}")
                continue
            
            pdf_link = ann.get("ATTACHMENTNAME")
            print(f"🔍 Processing: {company_name} ({sc_code})")
            
            # Search for NSE symbol using company name
            nse_symbol = search_nse_symbol(company_name)
            
            mkcap, revenue = None, None
            if nse_symbol:
                ticker_nse = f"{nse_symbol}.NS"
                print(f"🔍 Found NSE symbol: {nse_symbol}")
                mkcap, revenue = get_financials(ticker_nse)
            
            # Fallback to BSE code if NSE search failed
            if not mkcap:
                ticker_ns = f"{sc_code}.NS"
                ticker_bo = f"{sc_code}.BO"
                mkcap, revenue = get_financials(ticker_ns)
                if not mkcap:
                    mkcap, revenue = get_financials(ticker_bo)
            
            if not mkcap:
                print(f"❌ No market cap data for {company_name}, skipping")
                processed_announcements.append(unique_id)
                continue
            if mkcap < MIN_MKCAP or mkcap > MAX_MKCAP:
                print(f"❌ Market cap {mkcap:.0f} Cr outside range for {company_name}, skipping")
                processed_announcements.append(unique_id)
                continue
            if revenue < 10:
                print(f"❌ Revenue {revenue:.1f} Cr too low for {company_name}, skipping")
                processed_announcements.append(unique_id)
                continue
            
            print(f"✅ {company_name}: MarketCap={mkcap:.0f} Cr, Revenue={revenue:.0f} Cr")
            
            # Extract actual PDF text
            print(f"📄 Extracting PDF: {pdf_link}")
            pdf_text = extract_pdf_text(pdf_link)
            print(f"📄 PDF Text Length: {len(pdf_text)} chars")
            print(f"📄 PDF Preview: {pdf_text[:200]}...")
            
            # Round values for AI analysis
            mkcap_rounded = round(mkcap)
            revenue_rounded = round(revenue)
            
            # Build prompt for AI
            user_prompt = f"""
                PDF Text:
                {pdf_text}

                Additional Context:
                Revenue: {revenue_rounded} crores
                MarketCap: {mkcap_rounded} crores
            """
            response, tokens_used = call_cerebras_api(user_prompt)
            
            telegram_sent = False
            impact_value = "UNKNOWN"
            ai_note = response if response else ""
            
            if response:
                try:
                    parsed = json.loads(response)
                    impact_note = parsed.get("impact_note", "")
                    impact_value = "BIG" if "BIG" in impact_note.upper() else "MEDIUM" if "MEDIUM" in impact_note.upper() else "SMALL"
                    
                    # Send Telegram only if BIG
                    if impact_value == "BIG":
                        message = f"📋 ORDER ALERT\n\n📈 {company_name}\n📅 {ann_date}\n\n{impact_note}\n\n💰 Revenue: {revenue_rounded} Cr\n🏢 Market Cap: {mkcap_rounded} Cr"
                        telegram_sent = send_telegram_alert(message)
                        print(f"📢 TELEGRAM SENT: {company_name} - {impact_value}")
                    else:
                        print(f"🔕 No telegram (Impact: {impact_value}) for {company_name}")
                    
                    print(f"✅ Processed {company_name}, Impact: {impact_value}, Tokens: {tokens_used}, Telegram sent: {telegram_sent}")
                
                except:
                    print(f"⚠️ {company_name} Raw AI Response: {response}")
            
            # Update processed and log
            processed_announcements.append(unique_id)
            log_ai_output(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          company_name, sc_code, impact_value, telegram_sent, ai_note, tokens_used)
            
            # Save processed immediately to avoid reprocessing on crash
            save_processed(processed_announcements)

            # 1 second delay between announcements
            time.sleep(0.5)
        
        print(f"⏱ Sleeping for {POLL_INTERVAL} seconds...\n")
        time.sleep(POLL_INTERVAL)
