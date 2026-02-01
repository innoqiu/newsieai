import asyncio
import json
import os
import sys
import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union


from dotenv import load_dotenv

import re
from pathlib import Path
from typing import Any, Dict, Optional



# 引入 requests 用于测试 HTTP 交互
try:
    import requests
except ImportError:
    print("❌ 请先安装 requests 库: pip install requests")
    sys.exit(1)

from dotenv import load_dotenv

# 使用 LangChain 的标准 Agent 构建器
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

# --- 路径配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent # 定位到 D:\ICP\newsieai
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

#test use



class AccountantAgent:
    """
    [Accountant]: 财务专员 Agent。
    位置: agents/accountant.py
    职责: 结合 用户画像(User Profile) 和 402 支付请求，评估预算，执行 MCP 支付。
    """

    def __init__(self, payment_context: Union[str, Dict[str, Any]], user_profile: Optional[Dict[str, Any]] = None):
        self.raw_payment_context = payment_context  # 保存原始输入（str 或 dict）
        self.payment_context = None  # 后面会变成规范化 dict
        """
        初始化 Agent
        :param payment_context: 包含支付信息的原始字典 (来自 402 响应)
        :param user_profile: 用户配置信息 (如 VIP 等级、自定义限额、白名单等)
        """
        print(payment_context)
        
        # 默认的用户画像 (如果未提供)
        self.user_profile = user_profile or {
            "user_id": "default_guest",
            "tier": "standard",
            "custom_budget_limit": 0.05, # 默认 0.05 SOL
            "risk_tolerance": "low"
        }
        
        # 1. 检查 OpenAI Key
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️ Warning: OPENAI_API_KEY not found in environment.")
        
        # 2. 配置大脑
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0
        )
        
        self.mcp_client = None
        self.agent_runnable = None

    async def setup_mcp_client(self):
        """连接到 'pay' MCP 服务"""
        pay_port = os.getenv("PAY_HTTP_PORT", "8007")
        mcp_config = {
            "pay_service": {
                "url": f"http://localhost:{pay_port}/mcp",
                "transport": "streamable-http"
            }
        }
        self.mcp_client = MultiServerMCPClient(mcp_config)

    def _wrap_context_to_prompt(self) -> str:
        """
        [关键步骤] 将 支付账单 和 用户画像 同时打包进 Prompt。
        """
        raw_bill_str = self.raw_payment_context
        # bill_str = json.dumps(self.raw_payment_context, indent=2, ensure_ascii=False)
        profile_str = json.dumps(self.user_profile, indent=2, ensure_ascii=False)
        print(f"agent got a bill request from 402: {raw_bill_str}")
        print("\n" + "="*50)
        print(f"agent got a user profile: {profile_str}")
        
        return f"""
SYSTEM EVENT: INCOMING PAYMENT REQUEST (HTTP 402)
------------------------------------------------
1. USER PROFILE (WHO IS PAYING):
{profile_str}

2. BILL DETAILS (WHAT TO PAY):
{raw_bill_str}
------------------------------------------------
ENVIRONMENT:
- Current Network: Solana Devnet
- Role: Wallet Accountant

TASK:
Evaluate the bill against the User Profile's constraints and execute payment if valid. 
"""

    async def create_agent_graph(self):
        """构建 Agent 图"""
        if not self.mcp_client:
            await self.setup_mcp_client()
        
        try:
            tools = await self.mcp_client.get_tools()
        except Exception as e:
            print(f"❌ Error connecting to MCP Server: {e}")
            raise e
        
        # --- System Prompt 中增加了对 Profile 的引用逻辑 ---
        system_prompt = f"""You are the Accountant Agent. You have access to a tool named `pay_solana`. and `reaccess_payed_content`

### DECISION PROTOCOL:


1. **Analyze Context**:
   - Read the `USER PROFILE` to find the `custom_budget_limit` and `tier`.
   - Read the `BILL DETAILS` to find the `amount` and `receiver_id` (or something like `address`), `payment url`
   - If the context shows a payment successful message, it means that the payment has been made, and you are suppose to reaccess the information that user has payed for, ignore item 2-4 and jump to item 5.

2. **Evaluate Logic**:
   - **Rule 1 (Budget)**: Compare bill `amount` vs User's `custom_budget_limit`.
     - IF bill amount <= limit: **APPROVE**.
     - IF bill amount > limit: **DENY** (Reason: Exceeds user budget).
   
   - **Rule 2 (Safety)**: Ensure `receiver_id` looks like a valid Solana address (Base58 string).

   - **Rule 3 (Preference)**: Analyze the user's profile, and make decisionn based on the result of reasoning.
     - Based on the provided user profile, perform step-by-step reasoning to infer the user’s latent intentions, priorities, and likely decision patterns. Treat the user profile as contextual evidence rather than absolute truth. Clearly articulate how each inference is derived from specific attributes of the profile. Avoid stereotyping or overgeneralization. When multiple interpretations are possible, surface alternatives and explain why one is more plausible in context.
     - If you think the user is not interested in the content: **DENY** (Reason: User might not be intesested in the information).
3. **Execute (If Approved)**:
   - Call `pay_solana` tool IMMEDIATELY.


4. **Execution**:
   - If approved, call `pay_solana` immediately.
    - **Parameter Mapping**:
     - map JSON `address` or `receiver_id` -> tool argument `to_address`
     - map JSON `amount` -> tool argument `amount`
     - tool argument `reason` -> "User Tier: [Insert Tier] | Auto-payment"
   - Wait for tool execution.
   - If payment fails or is rejected, output:
     - PAYMENT_FAILED: reason
     - PAYMENT_REJECTED: reason

5. **Reaccess Paid Content (MANDATORY)**:
   - If `pay_solana` succeeds and returns a transaction hash:
     - Immediately call `reaccess_payed_content` with:
       - payment url
       - tx_hash
   - The FINAL output must be:
     - ONLY a structured out put of the retrieved paid content and the tx_hash
   - Output "PAYMENT_SUCCESSFUL: Content: 'payed content'; tx_hash:'tx_hash'." with the corresponding content replaced as the final answer.
"""
        self.agent_runnable = create_agent(self.llm, tools, system_prompt=system_prompt)

    async def run(self) -> str:
        """
        执行 Agent 主流程
        1. 评估是否支付
        2. 如果支付成功，自动重试URL获取内容
        3. 如果拒绝，返回拒绝消息
        """
        if not self.agent_runnable:
            await self.create_agent_graph()
        
        user_msg = self._wrap_context_to_prompt()
        inputs = {"messages": [HumanMessage(content=user_msg)]}
        
        print(f"🤖 Accountant 正在根据用户画像 [{self.user_profile.get('tier', 'N/A')}] 评估账单...")
        try:
            result = await self.agent_runnable.ainvoke(inputs)
            payment_result = result["messages"][-1].content
            print(f"\n✅ Payment result: {payment_result}")


            # Check if payment was successful
            if "PAYMENT_SUCCESSFUL" in payment_result:
                # Extract transaction hash
                import re
                match = re.search(r"PAYMENT_SUCCESSFUL:\s*([A-Za-z0-9]+)", payment_result)
                if match:
                    print(f"\n✅ Payment result: {payment_result}")
                    
                    return f"Payment processed successfully. Content retieved:{payment_result}"
                else:
                    return f"Payment processed but could not extract transaction hash.\n{payment_result}"
            elif "PAYMENT_REJECTED" in payment_result:
                # Payment was rejected - return rejection message with URL
                # url = self.payment_context.get("url") or self.payment_context.get("source_url")
                return f"No valuable information recognized by the agent in terms of \n{payment_result}"
            elif "PAYMENT_FAILED" in payment_result:
                return payment_result
            else:
                return payment_result
        except Exception as e:
            return f"AGENT_ERROR: {str(e)}"
    
    async def _retry_content_retrieval(self, url: str, tx_hash: str) -> str:
        """
        使用支付成功的交易哈希重新访问URL获取内容
        
        Args:
            url: 目标URL
            tx_hash: 交易哈希（用作授权令牌）
        
        Returns:
            格式化后的内容，或错误消息
        """
        try:
            headers = {"Authorization": f"Bearer {tx_hash}"}
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # 成功获取内容
                content_data = response.json()
                
                # 提取内容信息
                secret_message = content_data.get("data", {}).get("secret_message", "")
                valid_until = content_data.get("data", {}).get("valid_until", "")
                
                # 格式化为新闻文章格式
                result = f"""Premium News Content Retrieved:

Title: Premium News Content
Source: Bitserver (Paid Content)
Valid Until: {valid_until}

Content:
{secret_message}

Transaction Hash: {tx_hash}
"""
                return result
            elif response.status_code == 402:
                return f"""Payment was processed (tx: {tx_hash}), but content still requires payment.
This may indicate the transaction hasn't been confirmed yet, or there was an issue with verification.

Response: {response.text}"""
            else:
                return f"""Payment successful (tx: {tx_hash}), but content retrieval failed.
Status: {response.status_code}
Response: {response.text}"""
                
        except requests.exceptions.RequestException as e:
            return f"""Payment successful (tx: {tx_hash}), but failed to retrieve content from {url}.
Error: {str(e)}

You can manually retry with: Authorization: Bearer {tx_hash}"""

    async def cleanup(self):
        if self.mcp_client:
            try:
                await self.mcp_client.disconnect()
            except:
                pass

async def run_accountant_service(payment_data: Dict[str, Any], user_profile: Dict[str, Any] = None) -> str:
    """外部调用入口 (支持传入 User Profile)"""
    agent = AccountantAgent(payment_data, user_profile)
    try:
        return await agent.run()
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    pass