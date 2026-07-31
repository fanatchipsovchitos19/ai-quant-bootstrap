"""
AI Quant Bootstrap — AI Client
Supports RouterAI (OpenAI-compatible) and Ollama (local).
"""

import sys
import os
import io
import json
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ requests not installed. Run: pip install requests")
    sys.exit(1)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.helpers import is_default_api_key


class AIClient:
    """
    AI client supporting:
    - RouterAI (OpenAI-compatible API)
    - Ollama (local, optional)
    """

    def __init__(self, config, logger=None):
        """
        Args:
            config: AppConfig object from lib.config
            logger: Optional logger instance
        """
        self.logger = logger

        # RouterAI
        self.router_key = getattr(config.api_keys, 'routerai_api_key', config.api_keys.openai_api_key)
        self.router_url = "https://routerai.ru/api/v1"
        self.model_complex = getattr(config.api_keys, 'routerai_model_complex', 'deepseek/deepseek-chat')
        self.model_fast = getattr(config.api_keys, 'routerai_model_fast', 'openai/gpt-4o-mini')
        self.router_enabled = bool(self.router_key) and not is_default_api_key(self.router_key)

        # Ollama
        self.ollama_url = getattr(config.api_keys, 'ollama_url', 'http://localhost:11434')
        self.ollama_model = getattr(config.api_keys, 'ollama_model', 'llama3.2')
        self.ollama_enabled = getattr(config.api_keys, 'ollama_enabled', False) and self._check_ollama()

        if self.logger:
            if self.router_enabled:
                self.logger.info(f"AI: RouterAI ready (complex: {self.model_complex}, fast: {self.model_fast})")
            if self.ollama_enabled:
                self.logger.info(f"AI: Ollama ready (model: {self.ollama_model})")
            if not self.router_enabled and not self.ollama_enabled:
                self.logger.warning("AI: No providers available. Using heuristics.")

        self.enabled = self.router_enabled or self.ollama_enabled

    def _check_ollama(self) -> bool:
        """Checks if Ollama is running locally."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    # ============================================================
    # Core Methods
    # ============================================================

    def _ask_routerai(self, prompt: str, system: str = "", model: str = None,
                      temperature: float = 0.3, max_tokens: int = 300) -> Optional[str]:
        """Sends request to RouterAI (OpenAI-compatible)."""
        if not self.router_enabled:
            return None

        if model is None:
            model = self.model_complex

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = requests.post(
                f"{self.router_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.router_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                if self.logger:
                    self.logger.error(f"RouterAI error: {resp.status_code} — {resp.text[:200]}")
                return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"RouterAI request failed: {e}")
            return None

    def _ask_ollama(self, prompt: str, system: str = "", temperature: float = 0.1) -> Optional[str]:
        """Sends request to local Ollama with retry."""
        if not self.ollama_enabled:
            return None

        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "temperature": temperature
                    },
                    timeout=60
                )
                if resp.status_code == 200:
                    text = resp.json()["response"].strip()
                    while text.count("{") < text.count("}"):
                        text = text[:-1]
                    return text
                else:
                    if self.logger:
                        self.logger.error(f"Ollama error: {resp.status_code}")
            except Exception as e:
                if self.logger and attempt < 2:
                    self.logger.warning(f"Ollama attempt {attempt+1}/3 failed: {e}. Retrying...")
                    time.sleep(5)
                elif self.logger:
                    self.logger.error(f"Ollama failed after 3 attempts: {e}")
        return None
    def _ask_json(self, prompt: str, system: str = "", use_ollama: bool = False) -> Optional[dict]:
        """Asks AI and parses response as JSON."""
        if use_ollama:
            response = self._ask_ollama(prompt, system, temperature=0.1)
        else:
            response = self._ask_routerai(prompt, system, temperature=0.1, max_tokens=300)

        if not response:
            return None

        # Try to parse JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown block
            if "```json" in response:
                try:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                except:
                    pass
            # Try to find { } block
            if "{" in response and "}" in response:
                try:
                    start = response.index("{")
                    end = response.rindex("}") + 1
                    return json.loads(response[start:end])
                except:
                    pass

        if self.logger:
            self.logger.error(f"Failed to parse AI JSON: {response[:200]}")
        return None

    # ============================================================
    # Specialized Methods for Bots
    # ============================================================

    def evaluate_sentiment(self, tweet_text: str, author: str = "") -> Optional[dict]:
        """Sentiment analysis for Bot 1 (Sentiment Sniper)."""
        prompt = f"""You are a crypto sentiment analyst. Evaluate this tweet.

Tweet: {tweet_text}
Author: {author if author else "Unknown"}

Rate sentiment from 0 (extremely bearish) to 1 (extremely bullish) for any crypto token mentioned.
Extract the token ticker (like BTC, DOGE, ETH).
Respond ONLY with valid JSON:

{{"score": 0.85, "token_mentioned": "DOGE", "reasoning": "Short reason"}}

If no crypto token is mentioned, use "token_mentioned": "NONE"."""

        return self._ask_json(prompt)

    def check_news_sentiment(self, news_list: list[str], symbol: str) -> Optional[dict]:
        """News check for Bot 3 (DCA)."""
        news_text = "\n".join(f"- {n}" for n in news_list[:10]) if news_list else "No news available."

        prompt = f"""You are a crypto risk manager. Analyze recent news and decide 
whether to continue DCA buying {symbol} or pause.

Recent news:
{news_text}

Red flags that should trigger a PAUSE:
- Major exchange hack or protocol exploit
- Negative regulatory news (bans, lawsuits)
- Project founder exit or arrest
- Critical blockchain vulnerability

Respond ONLY with valid JSON:
{{"should_buy": true, "confidence": 0.9, "reasoning": "Short reason"}}"""

        return self._ask_json(prompt)

    def classify_token_scam(self, token_name: str, token_symbol: str, chain: str = "bsc") -> Optional[dict]:
        """Scam detection for Bot 5 (DEX Sniper). Uses Ollama if available for speed/cost."""
        prompt = f"""Analyze this new token for scam indicators.

Token Name: {token_name}
Token Symbol: {token_symbol}
Blockchain: {chain}

Scam indicators (weigh these heavily):
- Name imitates famous brands or people (ElonDoge, PepeCash)
- Symbol contains hype words without meaning (AI, GPT, ELON)
- Obvious misspellings of popular tokens
- Name suggests it's a "2.0" or "new" version of something

Respond ONLY with valid JSON:
{{"is_scam": true, "risk_level": "HIGH", "reasoning": "Short reason"}}"""

        # Use Ollama for speed if available
        return self._ask_json(prompt, use_ollama=self.ollama_enabled)

    def extract_ticker_from_tweet(self, tweet_text: str) -> Optional[str]:
        """Extracts crypto ticker from tweet using AI."""
        prompt = f"""Extract the crypto ticker mentioned in this tweet.
Return ONLY the ticker symbol (like BTC, ETH, DOGE). If none found, return NONE.

Tweet: {tweet_text}"""

        response = self._ask_routerai(prompt, temperature=0.1, max_tokens=20)
        if response and response.upper() != "NONE":
            return response.upper().strip()
        return None


# ============================================================
# Quick Test
# ============================================================
if __name__ == "__main__":
    print("=== AI Client Test ===\n")

    # Test with config
    from lib.config import load_config
    config = load_config("config.yaml")
    ai = AIClient(config)

    print(f"RouterAI enabled: {ai.router_enabled}")
    print(f"Ollama enabled: {ai.ollama_enabled}")
    print(f"Overall enabled: {ai.enabled}\n")

    if ai.router_enabled:
        print("Testing RouterAI...")
        response = ai._ask_routerai("Say 'Hello from RouterAI!' in one short sentence.")
        print(f"  Response: {response}")

        # Test sentiment
        result = ai.evaluate_sentiment("Elon Musk: DOGE to the moon! 🚀", "elonmusk")
        print(f"  Sentiment: {result}")
    else:
        print("⚠️  RouterAI not configured. Set routerai.api_key in config.yaml")