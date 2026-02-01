"""
Main entry point for NewsieAI System.
Refactored to start all MCP services globally.
"""

import asyncio
import sys
import os
import json
import re
import tools
import requests
from tools import start_mcp
from datetime import datetime
from dotenv import load_dotenv
# 导入 requests
# 导入 Agents
try:
    from agents.retriv import retriv_run_agent
    from agents.accountant import run_accountant_service
    from agents.personal_assistant import run_personal_assistant
except ImportError as e:
    print(f" Import Error: {e}")
    print("Ensure you are running from the project root")
    sys.exit(1)

from tools.start_mcp import MCPServiceManager 

# Import database initialization
try:
    from database import init_database
except ImportError as e:
    print(f"Warning: Database module not available: {e}")
    init_database = None

load_dotenv()

# =================================================================

async def test_news_agent():
    """Wrapper for News Retrieval Agent Test"""
    print("\n" + "="*50)
    print("TESTING: NEWS RETRIEVAL AGENT")
    print("="*50)


    print("Enter context for news search (or press Enter for default):")
    print("   Ex: 'Latest news about Tesla (TSLA)'")
    context = input("   > ").strip()
    
    if not context:
        context = "Search for news about Apple Inc. (AAPL) and recent technology developments"
        print(f"   Using default: {context}")

    print(f"Agent is running... (Context: {context})")

    # Build a simple user_context for testing
    user_context = {
        "user_id": "test_user",
        "timezone": "UTC",
        "content_preferences": [],
        "description": []
    }
    
    result = await retriv_run_agent(user_context, context)
    
    print("\n" + "-"*50)
    print("AGENT RESPONSE:")
    print("-"*50)
    print(result)


async def test_accountant_agent():
    """Wrapper for Accountant Agent Test"""
    print("\n" + "="*50)
    print("TESTING: ACCOUNTANT AGENT (Full Cycle)")
    print("="*50)

    vip_profile = {
        "user_id": "main_tester_01",
        "tier": "VIP_PLATINUM",
        "custom_budget_limit": 0.1,
        "preference": "the user is very interested in crypto market"
    }

    server_url = "http://localhost:8000/premium-content"
    print(f"Connecting to Content Server: {server_url}")
    
    try:
        resp = requests.get(server_url)
    except requests.exceptions.ConnectionError:
        print(" Connection Failed: Could not reach test_server.py.")
        print(" TIP: Open a new terminal and run: python test_server.py")
        return

    if resp.status_code == 402:
        print(" 402 Payment Required triggered.")
        bill_data = resp.json()
        print(bill_data)
        
        print(f"\n  Invoking Accountant Agent (Budget: {vip_profile['custom_budget_limit']} SOL)...")
        
        # 调用 Agent
        agent_res = await run_accountant_service(bill_data, user_profile=vip_profile)
        print(f" Agent Decision:\n{agent_res}")
        
        if "PAYMENT_SUCCESSFUL" in agent_res:
            match = re.search(r"PAYMENT_SUCCESSFUL:\s*([A-Za-z0-9]+)", agent_res)
            if match:
                tx_hash = match.group(1).strip()
                print(f"\n  Payment Hash Found: {tx_hash}")
                print(" Waiting 10s for chain confirmation...")
                await asyncio.sleep(10)
                
                print("  Redeeming Content...")
                final_resp = requests.get(server_url, headers={"Authorization": f"Bearer {tx_hash}"})
                
                if final_resp.status_code == 200:
                    print("\n SUCCESS! Content Retrieved:")
                    print(json.dumps(final_resp.json(), indent=2, ensure_ascii=False))
                else:
                    print(f" Verification Failed: {final_resp.text}")
        else:
            print("\n  Agent did not execute payment.")
    
    elif resp.status_code == 200:
        print("  Server returned 200 OK (Is it already paid/free?)")
    else:
        print(f" Unexpected status code: {resp.status_code}")


async def test_personal_assistant_agent():
    """Wrapper to test the Personal Assistant Agent."""
    print("\n" + "="*50)
    print("TESTING: PERSONAL ASSISTANT AGENT")
    print("="*50)

    # ---- User Profile Collection ----
    print("\n[User Profile]")
    user_id = input("User ID (default: demo_user): ").strip() or "demo_user"
    timezone = input("Timezone (default: UTC): ").strip() or "UTC"

    user_profile = {
        "user_id": user_id,
        "timezone": timezone,
        "preferred_notification_times": [],
        "content_preferences": [],
    }

    # ---- Schedule Log ----
    schedule_log = []
    
    # ---- Input ----
    input_content = input("What do you want to explore? (default: today's key news): ").strip() or "today's key news"

    print("\n Running Personal Assistant Agent...")
    
    # 调用 Agent
    res = await run_personal_assistant(
        user_profile=user_profile,
        schedule_log=schedule_log,
        input_time=None,
        input_content=input_content,
        user_ip=None,
    )

    print("\n" + "-"*50)
    print("PERSONAL ASSISTANT SUMMARY:")
    print("-"*50)
    summary = dict(res)
    gathered_full = summary.pop("gathered_info_full", None)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if gathered_full:
        save_dir = r"D:\ICP\newsieai\datalog"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(save_dir, f"news_{timestamp}.txt")
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(gathered_full))
            print(f" Full content saved to: {file_path}")
        except Exception as e:
            print(f" Failed to save file: {e}")

# =================================================================
# 🎮 新的主菜单逻辑
# =================================================================

def main():
    # 1. Initialize database
    if init_database:
        print("Initializing database...")
        init_database()
        print("Database ready!")
    else:
        print("Warning: Database initialization skipped (module not available)")
    
    # 2. 全局初始化 MCP 管理器
    manager = MCPServiceManager()
    print("runtest")
    try:
        # 3. 启动所有服务 (blocking=False，这样代码会继续往下走)
        manager.start_all_services(blocking=False)
        
        while True:
            print("\n" + "="*40)
            print("   NewsieAI Agent Control Center")
            print("   (MCP Services are Running in Background)")
            print("="*40)
            print("1. Test News Retrieval Agent (Search)")
            print("2. Test Accountant Agent (Payment)")
            print("3. Test Personal Assistant Agent")
            print("4. Exit (Stop All Services)")
            
            choice = input("\nSelect an option (1-4): ").strip()
            
            if choice == "1":
                try:
                    asyncio.run(test_news_agent())
                except Exception as e:
                    print(f" Error during test: {e}")
                    
            elif choice == "2":
                print("\n  Ensure 'python test_server.py' is running elsewhere!")
                asyncio.run(test_accountant_agent())

            elif choice == "3":
                print("runtestall")
                asyncio.run(test_personal_assistant_agent())

            elif choice == "4":
                print("Exiting...")
                break # 跳出循环，进入 finally 块
            else:
                print(" Invalid selection.")

    except KeyboardInterrupt:
        print("\n Interrupted by user.")
    except Exception as e:
        print (f"caught error {e}")

    finally:
        # 3. 无论如何退出（正常退出或报错），都关闭所有服务
        print("\nCleaning up resources...")
        manager.stop_all_services()
        sys.exit(0)

if __name__ == "__main__":
    main()