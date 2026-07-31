# AI Quant Bootstrap

5 AI-powered trading bots for cryptocurrency. Download, configure, run. No coding skills needed.

## What's Inside

- 🐦 **Sentiment Sniper** — Monitors Twitter influencers via Twitter API, AI analyzes sentiment, enters long positions
- 📊 **Arbitrage Scanner** — Scans Binance/Bybit/OKX for spreads > 0.4%
- 🤖 **DCA + AI** — Dollar-cost averaging with AI news check before each buy
- 🧠 **Grid ML** — Grid trading with ML-based range prediction
- 🎯 **DEX Sniper** — Snipes new pairs on PancakeSwap, AI filters scams

## Quick Start

```bash
pip install -r requirements.txt
python launcher.py
API Keys Needed (optional — bots work in paper trade mode)
Binance/Bybit — for real trading

Twitter API — for Sentiment Sniper (free tier: 1,500 tweets/month)

RouterAI — for AI analysis (or use local Ollama for free)

Telegram — for notifications

AI Providers
RouterAI — Sentiment analysis & news checking (DeepSeek, GPT-4o-mini)

Ollama — Local AI for scam detection (free, runs on your PC)

Requirements
Python 3.10+

Windows/Mac/Linux