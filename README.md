# Order Alerts

Automated BSE order announcement monitoring and analysis system with AI-powered impact assessment.

## Features

- Monitors BSE for "Receipt of Order" announcements
- Extracts and analyzes PDF content using AI
- Calculates order impact based on company financials
- Sends alerts via Telegram
- Filters companies by market cap

## Setup

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd OrderAlerts
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file from template:
```bash
cp .env.example .env
```

4. Configure your environment variables in `.env`:
- `CEREBRAS_API_KEY`: Your Cerebras AI API key
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID
- Other optional configurations

5. Run the application:
```bash
python orders.py
```

### GitHub Deployment

1. Fork this repository
2. Go to Settings > Secrets and variables > Actions
3. Add the following secrets:

#### Required Secrets:
- `CEREBRAS_API_KEY`: Your Cerebras AI API key
- `TELEGRAM_BOT_TOKEN`: Your primary Telegram bot token
- `TELEGRAM_CHAT_ID`: Your primary Telegram chat ID

#### Required Secrets:
- `BSE_API_URL`: BSE API endpoint
- `BSE_PDF_BASE_URL_LIVE`: BSE PDF live URL
- `BSE_PDF_BASE_URL_HIST`: BSE PDF history URL
- `CEREBRAS_MODEL`: AI model name
- `MIN_MKCAP`: Minimum market cap filter
- `MAX_MKCAP`: Maximum market cap filter
- `POLL_INTERVAL`: Polling interval in seconds

#### Optional Secrets:
- `TELEGRAM_BOT_TOKEN_2`: Secondary Telegram bot token
- `TELEGRAM_CHAT_ID_2`: Secondary Telegram chat ID

4. The workflow will run automatically on push to main branch

## Configuration

### Market Cap Filters
- `MIN_MKCAP`: Minimum market cap in crores (default: 300)
- `MAX_MKCAP`: Maximum market cap in crores (default: 20000)

### Polling
- `POLL_INTERVAL`: How often to check for new announcements in seconds (default: 120 = 2 minutes)

## API Keys Required

1. **Cerebras AI API Key**: Get from [Cerebras AI](https://cerebras.ai/)
2. **Telegram Bot Token**: Create a bot via [@BotFather](https://t.me/botfather)
3. **Telegram Chat ID**: Get your chat ID from [@userinfobot](https://t.me/userinfobot)

## File Structure

- `orders.py`: Main application
- `.env.example`: Environment variables template
- `requirements.txt`: Python dependencies
- `.github/workflows/deploy.yml`: GitHub Actions workflow
- `processed_announcements.json`: Tracks processed announcements (auto-generated)
- `ai_logs.csv`: AI analysis logs (auto-generated)