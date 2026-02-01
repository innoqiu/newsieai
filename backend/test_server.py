import os
import json
import uvicorn
import time
from fastapi import FastAPI, Header, HTTPException, Response
from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.signature import Signature




load_dotenv()


SERVER_SECRET_STR = os.getenv("SERVER_SECRETKEY")
if not SERVER_SECRET_STR:
    print("❌ 严重错误: 未在 .env 文件中找到 'SERVER_SECRETKEY'。")
    print("请确保 .env 文件存在且包含该变量。")
    exit(1)

# 3. 恢复服务端钱包
try:

    SERVER_KEYPAIR = Keypair.from_base58_string(SERVER_SECRET_STR)
    SERVER_PUBKEY = str(SERVER_KEYPAIR.pubkey())
    

    env_pub = os.getenv("SERVER_PUBKEY")
    if env_pub and env_pub != SERVER_PUBKEY:
        print(f"⚠️ 警告: .env 中的公钥与私钥推导出的公钥不匹配！以私钥为准。")
        
    print(f"✅ 服务端已启动 | 收款账户: {SERVER_PUBKEY}")
except Exception as e:
    print(f"❌ 钱包加载失败，请检查 .env 中的私钥格式: {e}")
    exit(1)

# 4. 连接 Solana 网络 (Devnet)
SOLANA_RPC_URL = "https://api.devnet.solana.com"
client = Client(SOLANA_RPC_URL)

# 定义商品价格
PRICE_SOL = 0.01
expected_lamports = int(PRICE_SOL * 1_000_000_000)

app = FastAPI()

# ================= 路由逻辑 =================

@app.get("/")
def home():
    return {"message": "X402 Payment Server is Running", "wallet": SERVER_PUBKEY}

@app.get("/premium-content")
def get_premium_content(authorization: str = Header(None)):
    """
    核心接口：通过 X402 协议保护的机密数据
    """
    # 这里要解决一下playback attack, 从服务端生成一个单次交易码，单次返回就报废，后续任何返回都不进行交易，防止使用单次hash进行多次交易
# 402 sneding
    content_price = 0.0001
    if not authorization:
        print(f"received")
        
        payment_request = {
            "error": "Payment Required",
            "message": "This is a top secret about BitCoin Trend. Access restricted. Please pay to proceed.",
            "payment_info": {
                #define chain and payment and encapsule
                "address": SERVER_PUBKEY,     
                "amount": PRICE_SOL,          
                "currency": "SOL",
                "chain": "solana-devnet"
            }
        }
        
        # 返回 402 状态码
        return Response(
            status_code=402, 
            content=json.dumps(payment_request), 
            media_type="application/json"
        )

    # verify the transaction.
    try:
        # 提取签名字符串
        if "Bearer " in authorization:
            tx_sig_str = authorization.split("Bearer ")[1].strip()
        else:
            tx_sig_str = authorization.strip()

        print(f" 收到凭证 (Tx): {tx_sig_str[:8]}... 正在链上核查...")
        

        sig = Signature.from_string(tx_sig_str)


        verified = False
        for i in range(5): # check 5 times for 2 s each to allow time 
            
            try:

                # max_supported_transaction_version=0 是必须的，以支持现代 Solana 交易, 要及时更新solana，后续包装一下，以适配其他链
                tx_info = client.get_transaction(sig, max_supported_transaction_version=0)
                
                if tx_info.value:
                    transaction_data = tx_info.value.transaction
                    meta = transaction_data.meta


                    #  交易是否存在且状态成功

                    if meta.err is not None:
                        print(f"❌ 交易存在但执行失败: {meta.err}")
                        raise HTTPException(status_code=400, detail="Transaction failed on chain.")

                    # 获取账户列表，以便找到我们在其中的位置
                    account_keys = transaction_data.transaction.message.account_keys
                    keys_str_list = [str(k) for k in account_keys]

                    if SERVER_PUBKEY not in keys_str_list:
                        print(f" 警告: 交易中没有服务端地址")
                        raise HTTPException(status_code=400, detail="Invalid receiver.")
                    
                    # =================================================
                    # 交易金额是否正确 (查余额变动)
                    # 1. 找到服务端地址在交易中的索引 (Index)
                    my_index = keys_str_list.index(SERVER_PUBKEY)

                    # 2. 获取交易前后的余额
                    pre_bal = meta.pre_balances[my_index]
                    post_bal = meta.post_balances[my_index]

                    # 3. 计算实际收到的金额
                    received_lamports = post_bal - pre_bal
                    
                    print(f" 余额变动核算: 前 {pre_bal} -> 后 {post_bal} | 净增: {received_lamports}")

                    # 4. 判定金额是否达标
                    # 
                    if received_lamports >= expected_lamports:
                        verified = True
                        print(f" 验证通过！收到 {received_lamports/1e9} SOL (预期: {PRICE_SOL})")
                        break
                    else:
                        print(f" 金额不足: 只收到 {received_lamports/1e9} SOL, 需要 {PRICE_SOL} SOL")
                        raise HTTPException(status_code=402, detail=f"Insufficient payment. Received {received_lamports/1e9} SOL.")
                else:
                    # 交易可能还在确认中
                    pass
            except HTTPException as he:
                raise he
            except Exception as e:
                # 忽略网络错误，
                pass
            
            print(f"等待链上确认 ({i+1}/5)...")
            time.sleep(2)

        if not verified:
            raise HTTPException(status_code=402, detail="Payment verification timed out or failed.")

        # 验证通过，交付机密内容 ---
        return {
            "status": "success",
            "access_granted": True,
            "data": {
                "secret_message": "【内部绝密】比特币即将暴涨到20万美金一颗",
                "valid_until": "2025-12-31"
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f" 系统错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid authorization format.")

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)