# AutoCoin - Bitcoin Auto Trading Bot

비트코인 자동매매 봇 프로그램입니다.

## 📋 Features

- Binance API를 통한 실시간 거래
- Telegram Bot을 통한 원격 제어
- 다양한 매매 전략 지원 (돌파매매, 스캘핑, 추세추종)
- 자동 손절/익절 관리
- 전략 추천 시스템

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- Binance Account (with API access)
- Telegram Bot Token

### 2. Installation

```bash
# Clone repository
git clone https://github.com/yourusername/autoCoin.git
cd autoCoin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. Testing

Run tests to verify setup:
```bash
python -m pytest tests/test_binance.py -v
```

## 📁 Project Structure

```
autoCoin/
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── logger.py          # Logging system
│   └── exchange/
│       ├── __init__.py
│       └── binance_client.py  # Binance API wrapper
├── tests/
│   └── test_binance.py    # API tests
├── logs/                  # Log files
├── data/                  # Data storage
├── requirements.txt       # Dependencies
├── .env.example          # Environment template
└── README.md
```

## ⚙️ Configuration

The bot uses environment variables for sensitive data and a JSON file for strategy configurations.

### Environment Variables (.env)

- `BINANCE_API_KEY`: Your Binance API key
- `BINANCE_API_SECRET`: Your Binance API secret
- `USE_TESTNET`: Use Binance testnet (true/false)
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Authorized Telegram chat ID

### Strategy Configuration (config.json)

Strategies can be configured in `config.json` file (auto-generated on first run).

## 📊 Trading Strategies

1. **Breakout Strategy**: 돌파매매 전략
2. **Scalping Strategy**: 스캘핑 전략
3. **Trend Following**: 추세추종 전략

## 🔒 Security

- API keys are stored in environment variables
- Telegram bot uses chat ID authentication
- All sensitive data is excluded from version control

## 📝 Development Phases

- ✅ Phase 1: Basic Infrastructure (Complete)
- ⏳ Phase 2: Telegram Bot Implementation
- ⏳ Phase 3: Trading Strategies
- ⏳ Phase 4: Trading Engine
- ⏳ Phase 5: Strategy Recommendation System
- ⏳ Phase 6: Integration & Optimization
- ⏳ Phase 7: Deployment & Operations

## ⚠️ Disclaimer

This bot is for educational purposes. Always test thoroughly with testnet before using real funds. Cryptocurrency trading carries significant risks.

## 📄 License

MIT License