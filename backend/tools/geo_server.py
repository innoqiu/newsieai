from dotenv import load_dotenv
import httpx
import os
import json
from fastmcp import FastMCP
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import pytz

# 配置日志
logger = logging.getLogger(__name__)

# 初始化 FastMCP
# 这里给服务起个名字 "geo-time-server"
mcp = FastMCP("geo-time-server")
load_dotenv()

@mcp.tool()
async def get_location_and_time(ip_address: str) -> str:
    """
    根据 IP 地址获取地理位置、时区和当前的本地时间。
    
    Args:
        ip_address: 目标 IP 地址
        
    Returns:
        JSON 格式的字符串，包含位置、时区和本地时间信息
    """
    try:
        # 1. 使用 ip-api.com 获取位置和时区 (免费版，非商业用途)
        url = f"http://ip-api.com/json/{ip_address}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            data = resp.json()

        if data.get("status") != "success":
            logger.warning(f"Failed to retrieve data for IP: {ip_address}")
            return json.dumps({"error": f"Could not retrieve data for IP {ip_address}"})

        timezone_str = data.get("timezone", "UTC")
        city = data.get("city", "Unknown")
        country = data.get("country", "Unknown")
        
        # 2. 根据时区计算当前时间
        try:
            tz = pytz.timezone(timezone_str)
            local_time = datetime.now(tz).isoformat()
        except Exception as e:
            logger.error(f"Timezone conversion error: {e}")
            local_time = datetime.now().isoformat()

        result = {
            "ip": ip_address,
            "location": f"{city}, {country}",
            "timezone": timezone_str,
            "current_local_time": local_time
        }
        
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in get_location_and_time: {str(e)}")
        return f"Error processing request: {str(e)}"


if __name__ == "__main__":
    # 使用 streamable-http 模式运行，支持通过环境变量配置端口
    # 对应 start_mcp.py 中的 "date_time": int(os.getenv("DATE_TIME_HTTP", "8002"))
    port = int(os.getenv("DATE_TIME_HTTP", "8002"))
    print(f" Running Geo Time Server on port {port}")
    
    # 关键：使用 transport="streamable-http" 适配 start_mcp.py 的检测逻辑
    mcp.run(transport="streamable-http", port=port)