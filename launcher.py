#!/usr/bin/env python3
"""
AI Quant Bootstrap — Launcher
Run this file to select and start any of the 5 trading bots.
"""

import subprocess
import sys
import os

# UTF-8 fix
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

BOTS = {
    "1": {
        "name": "AI-Sentiment Sniper",
        "file": "bots/bot_1_sentiment_sniper.py",
        "desc": "Мониторит Twitter инфлюенсеров. AI анализирует тональность. Входит в лонг на 15 мин.",
        "emoji": "🐦"
    },
    "2": {
        "name": "Arbitrage Scanner",
        "file": "bots/bot_2_arbitrage_scanner.py",
        "desc": "Сканирует цены на Binance/Bybit/OKX. Спред > 0.4% → сигнал в Telegram.",
        "emoji": "📊"
    },
    "3": {
        "name": "DCA with AI Correction",
        "file": "bots/bot_3_dca_ai.py",
        "desc": "Усредняет вход. ChatGPT проверяет новости перед каждой докупкой.",
        "emoji": "🤖"
    },
    "4": {
        "name": "Grid Bot with ML",
        "file": "bots/bot_4_grid_ml.py",
        "desc": "Торгует в боковике. ML предсказывает диапазон и переставляет ордера.",
        "emoji": "🧠"
    },
    "5": {
        "name": "DEX Sniper",
        "file": "bots/bot_5_dex_sniper.py",
        "desc": "Слушает новые пары на PancakeSwap/Uniswap. AI фильтрует скамы.",
        "emoji": "🎯"
    },
}


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    print("""
╔══════════════════════════════════════════════════════════╗
║        AI QUANT BOOTSTRAP — v1.0                        ║
║        Ваш персональный квантовый трейдер                ║
╚══════════════════════════════════════════════════════════╝
""")


def print_menu():
    print("\nВыберите бота для запуска:\n")
    for key, bot in BOTS.items():
        print(f"  [{key}] {bot['emoji']} {bot['name']}")
        print(f"      {bot['desc']}\n")
    print("  [a] Запустить ВСЕХ ботов сразу")
    print("  [c] Проверить config.yaml")
    print("  [0] Выход")


def run_bot(bot_key: str):
    bot = BOTS[bot_key]
    file = bot["file"]
    
    if not os.path.exists(file):
        print(f"\n❌ Файл {file} не найден.")
        print("Убедитесь, что вы запускаете лаунчер из папки проекта.")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\n{'='*55}")
    print(f"🚀 Запускаю: {bot['emoji']} {bot['name']}")
    print(f"{'='*55}\n")
    
    try:
        subprocess.run([sys.executable, file], cwd=os.path.dirname(os.path.abspath(__file__)))
    except KeyboardInterrupt:
        print("\n\n⏹️  Бот остановлен.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    
    input("\nНажмите Enter для возврата в меню...")


def run_all_bots():
    print(f"\n{'='*55}")
    print("🚀 Запускаю ВСЕХ ботов в отдельных окнах...")
    print(f"{'='*55}\n")
    
    for key, bot in BOTS.items():
        file = bot["file"]
        if os.path.exists(file):
            print(f"  ✅ {bot['emoji']} {bot['name']}")
            subprocess.Popen(
                [sys.executable, file],
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
        else:
            print(f"  ❌ {file} — не найден")
    
    print("\n✅ Все боты запущены в отдельных окнах.")
    print("Закройте каждое окно отдельно или нажмите Ctrl+C в нём.")
    input("\nНажмите Enter для возврата в меню...")


def check_config():
    print("\n📋 Проверяю config.yaml...\n")
    
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print("❌ config.yaml не найден!")
        return
    
    try:
        from lib.config import load_config
        config = load_config(config_path)
        
        print("✅ config.yaml загружен.\n")
        print(f"  Биржа: {config.general.primary_exchange.upper()}")
        print(f"  Тестнет: {'Да' if config.api_keys.binance_testnet else 'НЕТ (боевой!)'}")
        print(f"  Позиция: ${config.general.default_position_size}")
        print(f"  Проскальзывание: {config.general.slippage_percent}%")
        print()
        
        # Check API keys
        checks = []
        if "ВАШ" not in config.api_keys.binance_api_key and config.api_keys.binance_api_key:
            checks.append("✅ Binance API ключ задан")
        else:
            checks.append("⚠️  Binance API ключ не задан (paper trade)")
        
        if "ВАШ" not in config.api_keys.openai_api_key and config.api_keys.openai_api_key:
            checks.append("✅ OpenAI ключ задан")
        else:
            checks.append("⚠️  OpenAI ключ не задан (AI выключен)")
        
        if "ВАШ" not in config.api_keys.telegram_bot_token and config.api_keys.telegram_bot_token:
            checks.append("✅ Telegram ключ задан")
        else:
            checks.append("⚠️  Telegram ключ не задан (уведомления в консоль)")
        
        if "ВАШ" not in config.api_keys.twitter_bearer_token and config.api_keys.twitter_bearer_token:
            checks.append("✅ Twitter ключ задан")
        else:
            checks.append("⚠️  Twitter ключ не задан (симулированные твиты)")
        
        for c in checks:
            print(f"  {c}")
    
    except Exception as e:
        print(f"❌ Ошибка загрузки config.yaml: {e}")
    
    input("\nНажмите Enter для возврата в меню...")


def main():
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        choice = input("\nВаш выбор: ").strip().lower()
        
        if choice == "0":
            print("\n👋 До новых профитов!\n")
            break
        elif choice == "a":
            run_all_bots()
        elif choice == "c":
            check_config()
        elif choice in BOTS:
            run_bot(choice)
        else:
            print("\n⚠️  Неверный выбор. Нажмите Enter и попробуйте снова.")
            input()


if __name__ == "__main__":
    main()