from dotenv import load_dotenv
import requests
import os
from fastmcp import FastMCP
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
load_dotenv()


class StockNews:
    def __init__(self):
        self.api_key = os.environ.get("ALPHAADVANTAGE_API_KEY")

        # 2. 如果没有 Key，直接报错，阻止程序继续运行
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not provided!...")

        # 3. 设置 API 的基础地址
        self.base_url = "https://www.alphavantage.co/query"

    def retrive_news(
        self,
        tickers: Optional[str] = None,
        topics: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
        sort: str = "LATEST",
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles from Alpha Vantage NEWS_SENTIMENT API

        Args:
            tickers: Stock/crypto/forex symbols (e.g., "AAPL" or "COIN,CRYPTO:BTC,FOREX:USD")
            topics: News topics (e.g., "technology" or "technology,ipo")
            time_from: Start time in YYYYMMDDTHHMM format (e.g., "20220410T0130")
            time_to: End time in YYYYMMDDTHHMM format
            sort: Sort order ("LATEST", "EARLIEST", or "RELEVANCE")

        Returns:
            List of news articles
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": self.api_key,
            "sort": sort,
            "limit": 40,  # Fixed limit
        }

        if tickers:
            params["tickers"] = tickers
        if topics:
            params["topics"] = topics
        if time_from:
            params["time_from"] = time_from
        if time_to:
            params["time_to"] = time_to

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            json_data = response.json()

            # Check for API errors
            if "Error Message" in json_data:
                raise Exception(f"Alpha Vantage API error: {json_data['Error Message']}")
            if "Note" in json_data:
                raise Exception(f"Alpha Vantage API note: {json_data['Note']}")

            # Extract feed data
            feed = json_data.get("feed", [])

            if not feed:
                print(f"⚠️ Alpha Vantage API returned empty feed")
                return []

            return feed[:params["limit"]]

        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage API request failed: {e}")
            raise Exception(f"Alpha Vantage API request failed: {e}")
        except Exception as e:
            logger.error(f"Alpha Vantage API error: {e}")
            raise

class BitcoinNews:
    def __init__(self):
        self.api_key = os.environ.get("BITSERVER_API_KEY")
        self.base_url = os.environ.get("BITSERVER_URL", "http://localhost:8000/premium-content")

    def retrive_news(self, auth_token: Optional[str] = None):
        """
        Retrieve news articles from the Bitserver endpoint.

        Args:
            auth_token: Optional authorization token (transaction hash) for paid content

        Returns:
            List[dict]: List containing news articles, or raises PaymentRequiredException if 402
        """
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = requests.get(self.base_url, headers=headers, timeout=30)
            
            if response.status_code == 402:
                # Payment required - extract payment data and raise exception
                payment_data = response.json()
                logger.warning("Bitserver: Payment required. Returning payment data.")
                raise PaymentRequiredException(payment_data)
            
            response.raise_for_status()
            json_data = response.json()

            # Process the successful response as news
            secret_message = json_data.get("data", {}).get("secret_message", "")
            valid_until = json_data.get("data", {}).get("valid_until", "")
            if not secret_message:
                logger.warning("Bitserver: No premium message found.")
                return []

            return [{
                "title": "Bitserver Premium News",
                "summary": secret_message,
                "url": self.base_url,
                "source": "Bitserver",
                "time_published": valid_until,
            }]
        except PaymentRequiredException:
            logger.info(f"Rising Payment required: {payment_data}")
            # Re-raise payment required exceptions
            raise
        except Exception as e:
            logger.error(f"Bitserver API error: {e}")
            return [{
                "title": "Error fetching Bitserver news",
                "summary": f"Error: {e}",
                "url": self.base_url,
                "source": "Bitserver"
            }]


class PaymentRequiredException(Exception):
    """Exception raised when a 402 Payment Required response is received."""
    def __init__(self, payment_data: Dict[str, Any]):
        self.payment_data = payment_data
        super().__init__("Payment required for this resource")
