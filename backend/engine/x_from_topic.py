"""
Engine function for processing x-from-topic blocks.
"""

from typing import Dict, Any, Optional
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
import requests

load_dotenv()
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
BASE_URL = os.getenv("BASE_URL")

def extract_media_urls(tweet: Dict[str, Any]) -> List[str]:
    """
    从 tweet 中提取可直链下载的媒体 URL
    """
    media_urls = []

    entities = tweet.get("extendedEntities", {})
    for media in entities.get("media", []):
        url = media.get("media_url_https")
        if url:
            media_urls.append(url)

    return media_urls


def search_x_topic(topic: List[str]) -> str:
    if isinstance(topic, str):
        # split(',') 把 "space,spacex,bitcoin" 变成 ["space", "spacex", "bitcoin"]
        # strip() 去除可能存在的空格（比如 "space, spacex" 中的空格）
        topic_list = [t.strip() for t in topic.split(',') if t.strip()]
    else:
        # 如果传进来的已经是 list，就直接用
        topic_list = topic
    print(f"topic_list: {topic_list}")
    print(f"checking time...")
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_str = since_24h.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    print(f"Full query: {since_str}")
    

    user_query = " OR ".join([f"{u}" for u in topic_list])

    full_query = f"{user_query} since:{since_str}"
    print(f"Full query: {full_query}")

    try:
        headers = {"X-API-Key": TWITTER_API_KEY}
        params = {"query": full_query, "queryType": "Latest"}
        print(f"Params: {params},base_url: {BASE_URL},headers: {headers}")
        response = requests.get(BASE_URL, headers=headers, params=params)
        print(f"Got Response: {response.json()}")
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

    # 4️⃣ 结构化输出
    # API 原样返回 tweets[], has_next_page 等字段。
    return {
        "queried_topic": topic,
        "query": full_query,
        "results": "Da",
    }

def extract_tweet_items(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    遍历 raw["results"]["tweets"]，提取 tweet + quoted_tweet 信息
    """
    items = []
    print(f"+" *50)
    print(f"getting now")
    tweets = raw.get("results", {}).get("tweets", [])
    print(f"=" *50)
    print(f"\nTweets: {tweets}")
    for tweet in tweets:
        try:
            # 原 tweet
            url = tweet.get("twitterUrl")
            author = tweet.get("author", {}).get("name")
            text = tweet.get("text")
            created_at = tweet.get("createdAt")

            # quoted tweet（可能不存在 or 是字符串 "None"）
            quoted = tweet.get("quoted_tweet")
            if isinstance(quoted, dict):
                quoted_text = quoted.get("text")
                quoted_author = quoted.get("author", {}).get("name")
            else:
                quoted_text = None
                quoted_author = None

            # 媒体（主 tweet + quoted tweet）
            media_urls = extract_media_urls(tweet)
            if isinstance(quoted, dict):
                media_urls.extend(extract_media_urls(quoted))

            item = {
                "url": url,
                "author": author,
                "text": text,
                "created_at": created_at,
                "quoted_author": quoted_author,
                "quoted_text": quoted_text,
                "media_urls": media_urls,
            }

            items.append(item)

        except Exception as e:
            print(f"Error parsing tweet {tweet.get('id')}: {e}")
            continue

    return items


def process_x_from_topic(user_context: Dict[str, Any], tags: List[str], mode: str) -> Dict[str, Any]:
    """
    Process an x-from-topic block.
    
    Args:
        user_context: User profile data retrieved from database user_profiles table
        body: The body/content from the thread block (topic/search query)
        mode: The 'ai' value from the thread block (e.g., 'selective', 'newest', 'natural')
    
    Returns:
        Dict containing the processed results
    """
    # TODO: Implement x-from-topic logic
    print(f"[Engine] Processing x-from-topic block - body: {tags}, mode: {mode}")
    result = search_x_topic(tags)
    if result:
        tweets = extract_tweet_items(result)
        print(f"Extracted tweets: {tweets}")
        return {
            "status": "success",
            "block_type": "x-from-user",
            "body": tags,
            "mode": mode,
            "user_context": user_context,
            "tweets": tweets
        }
    else:
        print(f"[Engine] No results from search_x_usernames")
        return {
            "status": "error",
            "block_type": "x-from-user",
            "body": tags,
            "mode": mode,
            "user_context": user_context,
            "error": "Failed to retrieve tweets"
        }

