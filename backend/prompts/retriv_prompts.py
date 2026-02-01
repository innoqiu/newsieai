import os

from dotenv import load_dotenv

load_dotenv()
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

STOP_SIGNAL = "<Finished>"
# 细节上的把控需要进行优化，是进行检索还是
agent_system_prompt = f"""
You are a information retrieval assistant for {topic} news on platform {platform}.

Your goals are:
- fetch information from {platform}.
- Think and reason by calling available tools.
- You need to think about what information the user is looking for.
- Before making decisions what information to return, gather as much information as possible through search tools to aid decision-making.
- If you have gathered all the information the user might interested in, return the information in a structured format.

The information you retrived should meets the following standards:
- If the user provide a specific query. Being relevant to the user's query is the first priority.
- The information should be accurate.
- The information should be up to date.
- You should provide 

Notes:
- You don't need to request user permission during operations, you can execute directly
- You must execute operations by calling tools, directly output operations will not be accepted

Here is the information you need:

Current time:
{date}

When you think your task is complete, output
{Finished}
"""

# The Schedual of the day:
# {schedual}

# Current balance of the portfolio:
# {balance}

def get_agent_system_prompt(
    today_date: str, signature: str, market: str = "us", stock_symbols: Optional[List[str]] = None
) -> str:
    print(f"signature: {signature}")
    print(f"today_date: {today_date}")
    print(f"market: {market}")

    # Auto-select stock symbols based on market if not provided
    if stock_symbols is None:
        stock_symbols = all_sse_50_symbols if market == "cn" else all_nasdaq_100_symbols

    # Get yesterday's buy and sell prices
    # yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(
    #     today_date, stock_symbols, market=market
    # )
    # today_buy_price = get_open_prices(today_date, stock_symbols, market=market)
    # today_init_position = get_today_init_position(today_date, signature)
    # yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    
    return agent_system_prompt.format(
        date=today_date,
        positions=today_init_position,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_sell_prices,
        today_buy_price=today_buy_price,
        # yesterday_profit=yesterday_profit
    )


if __name__ == "__main__":
    # today_date = get_config_value("TODAY_DATE")
    # signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))
