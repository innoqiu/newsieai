import os
import sys
import json
import uvicorn
from fastmcp import FastMCP
from typing import Optional

# --- 路径配置 ---
# 确保能导入 wallet 模块 (假设 wallet 文件夹在当前目录下)
from walletx import execute_agent_payment

# Import requests for HTTP requests
try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library is required. Install via: pip install requests")
    requests = None


# --- 初始化 MCP 服务 ---
# 定义服务名称
mcp = FastMCP("Pay Service")

# --- 定义工具 (Tool) ---
@mcp.tool()
def reaccess_payed_content(payment_url: str, tx_hash: str) -> str:
    """
    Reaccess paid content from a URL using a transaction hash as authorization token.
    
    This tool is used after a successful payment to retrieve the premium content
    that was protected by HTTP 402 Payment Required protocol.
    
    Args:
        payment_url: The URL endpoint that requires payment (e.g., "http://localhost:8000/premium-content")
        tx_hash: The transaction hash from the successful payment (used as Bearer token)
    
    Returns:
        A JSON string containing the retrieved content, or an error message if retrieval fails.
    """
    if not requests:
        return json.dumps({
            "status": "error",
            "message": "requests library not available. Cannot retrieve content."
        }, ensure_ascii=False)
    
    print(f"[MCP Tool] Reaccessing paid content from: {payment_url}")
    print(f"[MCP Tool] Using transaction hash: {tx_hash[:16]}...")
    
    try:
        # Make HTTP GET request with Authorization header
        headers = {"Authorization": f"Bearer {tx_hash}"}
        response = requests.get(payment_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Successfully retrieved content
            content_data = response.json()
            
            # Extract the actual content
            secret_message = content_data.get("data", {}).get("secret_message", "")
            valid_until = content_data.get("data", {}).get("valid_until", "")
            
            result = {
                "status": "success",
                "content": secret_message,
                "valid_until": valid_until,
                "tx_hash": tx_hash,
                "url": payment_url,
                "message": "Content successfully retrieved after payment verification."
            }
            
            print(f"[MCP Tool] Content retrieved successfully")
            return json.dumps(result, ensure_ascii=False)
            
        elif response.status_code == 402:
            # Still requires payment (transaction might not be confirmed yet)
            error_detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            result = {
                "status": "error",
                "error_code": 402,
                "message": "Content still requires payment. Transaction may not be confirmed yet.",
                "details": error_detail
            }
            print(f"[MCP Tool] Content still requires payment (402)")
            return json.dumps(result, ensure_ascii=False)
            
        elif response.status_code == 400:
            # Invalid transaction or verification failed
            error_detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            result = {
                "status": "error",
                "error_code": 400,
                "message": "Transaction verification failed or invalid transaction.",
                "details": error_detail
            }
            print(f"[MCP Tool] Transaction verification failed")
            return json.dumps(result, ensure_ascii=False)
            
        else:
            # Other error
            result = {
                "status": "error",
                "error_code": response.status_code,
                "message": f"Failed to retrieve content. Server returned status {response.status_code}.",
                "response": response.text[:500]  # Limit response text length
            }
            print(f"[MCP Tool] Content retrieval failed with status {response.status_code}")
            return json.dumps(result, ensure_ascii=False)
            
    except requests.exceptions.Timeout:
        result = {
            "status": "error",
            "message": "Request timeout. The server may be slow to verify the transaction.",
            "suggestion": "Wait a few seconds and try again, or check if the transaction is confirmed on-chain."
        }
        print(f"[MCP Tool] Request timeout")
        return json.dumps(result, ensure_ascii=False)
        
    except requests.exceptions.ConnectionError:
        result = {
            "status": "error",
            "message": f"Connection error. Could not reach {payment_url}.",
            "suggestion": "Ensure the payment server is running and accessible."
        }
        print(f"[MCP Tool] Connection error")
        return json.dumps(result, ensure_ascii=False)
        
    except requests.exceptions.RequestException as e:
        result = {
            "status": "error",
            "message": f"Request failed: {str(e)}"
        }
        print(f"[MCP Tool] Request exception: {e}")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Unexpected error while retrieving content: {str(e)}"
        }
        print(f"[MCP Tool] Unexpected error: {e}")
        return json.dumps(result, ensure_ascii=False)








@mcp.tool()
def pay_solana(to_address: str, amount: float, reason: str = "MCP Transaction") -> str:
    """
    Executes a SOL payment transaction on the Solana blockchain.
    
    Args:
        to_address: The target Solana public key (Base58 string).
        amount: The amount of SOL to send (e.g., 0.01).
        reason: A short description of why this payment is being made (for logs).
        
    Returns:
        A JSON string containing the transaction status and hash.
    """
    print(f"[MCP Tool] Received request: Send {amount} SOL to {to_address} (Reason: {reason})")

    # 调用底层钱包功能 
    agent_sig = f"MCP_Agent_{reason.replace(' ', '_')}"
    
    tx_hash = execute_agent_payment(
        agent_signature=agent_sig,
        to_address=to_address,
        amount_sol=amount
    )

    # 构造返回信息 
    if tx_hash:
        result = {
            "status": "success",
            "tx_hash": tx_hash,
            "message": "Transaction successfully broadcasted to Solana network.",
            "details": {
                "amount": amount,
                "receiver": to_address,
                "currency": "SOL"
            }
        }
    else:
        result = {
            "status": "failed",
            "message": "Transaction failed. Possible reasons: Insufficient funds, invalid address, or network error."
        }
    
    # 序列化为 JSON 字符串
    return json.dumps(result, ensure_ascii=False)

# --- 启动服务 ---
if __name__ == "__main__":
    # 从环境变量获取端口，默认 8007 (与 start_mcp.py 对应)
    port = int(os.getenv("PAY_HTTP_PORT", "8007"))
    print(f" Pay MCP Service starting on port {port}")
    
    # 使用 mcp.run() 启动，FastMCP 会自动处理 HTTP/SSE 协议
    mcp.run(transport="streamable-http", port=port)