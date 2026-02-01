import subprocess
import time
import requests
import sys
import os
import signal
import json
from pathlib import Path


# project_root/
#   ├── wallet/
#   │   └── wallet.py
#   ├── server.py
#   └── test_x402_flow.py
try:
    from wallet.wallet import AgentWallet
except ImportError:
    sys.path.append(os.getcwd())
    from wallet.wallet import AgentWallet


SERVER_URL = "http://localhost:8000/premium-content"
SERVER_SCRIPT = "test_server.py"
AGENT_NAME = "Test_Auto_Bot"

def start_server():
    """在后台启动服务端进程"""
    print("\n 正在启动 X402 服务端 (server.py)...")
    # 使用 subprocess 启动 server.py，不阻塞当前脚本
    # stdout=None 打印直接显示在控制台，方便我们观察
    process = subprocess.Popen([sys.executable, SERVER_SCRIPT], stdout=None, stderr=None)
    

    time.sleep(3) 
    return process

def stop_server(process):
    """关闭服务端进程"""
    print("\n🛑 测试结束，正在关闭服务端...")
    if process:
        process.terminate()
        process.wait() # 等待完全关闭
    print("服务端已关闭")

def run_test_flow():
    print("="*50)
    print(" 开始 X402 自动化支付流程测试")
    print("="*50)

    # 1. 初始化钱包
    print("\n[Step 1] 初始化 Agent 钱包...")
    try:
        agent_wallet = AgentWallet()
        balance = agent_wallet.check_balance()
        if balance < 0.02:
            print(f"余额不足 (当前: {balance} SOL)")
            return
    except Exception as e:
        print(f"钱包初始化失败: {e}")
        return

    # 2. 第一次请求 (预期失败)
    print(f"\n[Step 2] 首次尝试访问机密接口: {SERVER_URL}")
    try:
        response = requests.get(SERVER_URL)
    except requests.exceptions.ConnectionError:
        print("❌ 连接被拒绝，请检查 server.py 是否启动成功")
        return

    if response.status_code == 402:
        print(f"✅ 成功触发付费墙 (HTTP 402)")
        
        # 解析返回的 JSON
        try:
            data = response.json()
            print(f"收到的账单: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 提取支付要素 (兼容我们刚才定义的 x402 结构)
            # 优先检查 x402 字段，如果没有则检查 payment_info
            if "x402" in data:
                pay_info = data["x402"]
                target_address = pay_info.get("receiver_id")
                amount = float(pay_info.get("amount"))
            elif "payment_info" in data: # 兼容旧版
                pay_info = data["payment_info"]
                target_address = pay_info.get("address")
                amount = float(pay_info.get("amount"))
            else:
                print(" 无法解析支付信息: 未知的数据结构")
                return

            print(f" 解析支付目标: 向 {target_address} 支付 {amount} SOL")

        except Exception as e:
            print(f"❌ JSON 解析失败: {e}")
            return
    else:
        print(f"❌ 预期是 402，但收到了 {response.status_code}。测试终止。")
        print(response.text)
        return

    # 3. 执行支付
    print(f"\n[Step 3] Agent 正在执行自动支付...")
    tx_hash = agent_wallet.transfer_sol(target_address, amount, AGENT_NAME)

    if not tx_hash:
        print("❌ 支付失败，测试终止。")
        return

    # 4. 等待确认 (关键步骤)
    # 因为链上确认需要时间，服务端查得太快可能会查不到
    wait_seconds = 15
    print(f"\n[Step 4]  等待 {wait_seconds} 秒，让交易在 Solana 网络传播...")
    for i in range(wait_seconds):
        print(f".", end="", flush=True)
        time.sleep(1)
    print(" done.")

    # 5. 重试请求 (携带凭证)
    print(f"\n[Step 5] 携带凭证重试请求...")
    headers = {
        "Authorization": f"Bearer {tx_hash}"
    }
    
    final_response = requests.get(SERVER_URL, headers=headers)

    # 6. 验证结果
    if final_response.status_code == 200:
        print("\n" + "="*50)
        print(" 测试通过！成功获取机密内容！")
        print("="*50)
        result_data = final_response.json()
        print(f" 响应内容:\n{json.dumps(result_data, indent=2, ensure_ascii=False)}")
    else:
        print(f"\n❌ 测试失败: 服务端依然拒绝 (Status: {final_response.status_code})")
        print(f"原因: {final_response.text}")

def main():
    server_process = None
    try:
        # 启动 Server
        server_process = start_server()
        
        # 运行测试逻辑
        run_test_flow()
        
    except KeyboardInterrupt:
        print("\n用户手动中断")
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}")
    finally:
        # 关掉 Server
        stop_server(server_process)

if __name__ == "__main__":
    main()