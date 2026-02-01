import os
import sys
import datetime
from pathlib import Path

from dotenv import load_dotenv, set_key
from solana.rpc.api import Client
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer # type: ignore
from solders.keypair import Keypair # type: ignore
from solders.pubkey import Pubkey # type: ignore
from solders.signature import Signature # type: ignore
from solders.message import Message
from solders.hash import Hash
import base58

# --- 配置部分 ---
SOLANA_RPC_URL = "https://api.devnet.solana.com"
# 自动定位到项目根目录 D:\ICP\newsieai
# 假设当前文件在 D:\ICP\newsieai\wallet\wallet.py
BASE_DIR = Path(__file__).resolve().parent.parent 
ENV_FILE_PATH = BASE_DIR / ".env"
LOG_DIR = BASE_DIR / "datalog"
LOG_FILE_PATH = LOG_DIR / "transfer_log.txt"
load_dotenv()
receive_address = os.getenv("SERVER_PUBKEY")
class AgentWallet:
    def __init__(self):
        """
        初始化钱包：
        1. 加载环境变量
        2. 初始化 Solana 客户端
        3. 加载或生成密钥对
        4. 初始化日志目录   
            
        """
        # 加载环境
        load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
        
        # 初始化客户端
        self.client = Client(SOLANA_RPC_URL)
        
        # 加载或生成钱包
        self.keypair = self._get_or_create_keypair()
        self.pubkey = self.keypair.pubkey()
        
        # 确保日志目录存在
        self._ensure_log_dir()

    def _get_or_create_keypair(self) -> Keypair:
        """内部方法：从 env 获取或生成新 Keypair"""
        pub_env = os.getenv("SOLANA_PUBKEY")
        secret_env = os.getenv("SOLANA_SECRETKEY")

        if pub_env and secret_env:
            try:
                kp = Keypair.from_base58_string(secret_env)
                # 简单校验
                if str(kp.pubkey()) != pub_env:
                    print(" 警告: .env 公钥不匹配，以私钥为准。")
                return kp
            except Exception as e:
                print(f"❌ 现有密钥加载失败: {e}，将生成新钱包。")
        
        return self._generate_and_save()

    def _generate_and_save(self) -> Keypair:
        """内部方法：生成并保存新 Keypair"""
        print(" 正在生成新钱包...")
        kp = Keypair()
        
        pub_str = str(kp.pubkey())
        sec_str = base58.b58encode(bytes(kp)).decode("utf-8")
        
        # 保存到 .env
        # 注意：需要创建 .env 如果不存在
        if not ENV_FILE_PATH.exists():
            with open(ENV_FILE_PATH, 'w') as f: pass
            
        set_key(str(ENV_FILE_PATH), "SOLANA_PUBKEY", pub_str)
        set_key(str(ENV_FILE_PATH), "SOLANA_SECRETKEY", sec_str)
        
        print(f"✅ 新钱包已生成并保存: {pub_str}")
        return kp

    def _ensure_log_dir(self):
        """确保日志文件夹存在"""
        if not LOG_DIR.exists():
            LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _log_transaction(self, agent_sig: str, to_addr: str, amount: float, tx_hash: str, status: str):
        """内部方法：写入交易日志"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (
            f"[{timestamp}] "
            f"AGENT: {agent_sig} | "
            f"STATUS: {status} | "
            f"TO: {to_addr} | "
            f"AMOUNT: {amount} SOL | "
            f"TX: {tx_hash}\n"
        )
        
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"❌ 日志写入失败: {e}")

    def check_balance(self) -> float:
        """查询余额"""
        try:
            resp = self.client.get_balance(self.pubkey)
            sol = resp.value / 1_000_000_000
            print(f"当前余额: {sol} SOL ({self.pubkey})")
            return sol
        except Exception as e:
            print(f"❌ 查询余额失败: {e}")
            return 0.0

    def transfer_sol(self, to_address: str, amount: float, agent_signature: str) -> str:
        """
        核心转账功能 (适配 solders 库标准)
        :param to_address: 接收方地址
        :param amount: 金额 (SOL)
        :param agent_signature: 操作该动作的 Agent 签名/ID
        :return: 交易 Hash (Signature) 或 None
        """
        try:
            print(f"🔄 Agent [{agent_signature}] 请求转账: {amount} SOL -> {to_address}")

            #余额检查  Gas fee 
            current_bal = self.check_balance()
            if current_bal < amount + 0.000005: 
                msg = f"余额不足 (需: {amount} + Gas, 拥有的: {current_bal})"
                print(f"❌ {msg}")
                self._log_transaction(agent_signature, to_address, amount, "N/A", f"FAILED: {msg}")
                return None


            # 将地址字符串转换为 Pubkey 对象
            to_pubkey = Pubkey.from_string(to_address)
            # 将 SOL 转换为 Lamports (1 SOL = 10^9 Lamports)
            lamports = int(amount * 1_000_000_000)

            # 转账指令
            ix = transfer(
                TransferParams(
                    from_pubkey=self.pubkey,
                    to_pubkey=to_pubkey,
                    lamports=lamports
                )
            )

            recent_blockhash = self.client.get_latest_blockhash().value.blockhash


            txn = Transaction.new_signed_with_payer(
                instructions=[ix],             # 指令列表
                payer=self.pubkey,             # 付费方 (Fee Payer)
                signing_keypairs=[self.keypair],        # 签名者列表
                recent_blockhash=recent_blockhash
            )

            # send_transaction 
            print(" 广播交易到 Solana 网络...")
            signature = self.client.send_transaction(txn).value
            
            # 将签名对象转换为字符串
            tx_hash = str(signature)
            
            print(f" 交易发送成功! Hash: {tx_hash}")
            print(f"link: https://explorer.solana.com/tx/{tx_hash}?cluster=devnet")
            
            # 7. 记录成功日志
            self._log_transaction(agent_signature, to_address, amount, tx_hash, "SUCCESS")
            return tx_hash

        except Exception as e:
            err_msg = str(e)
            print(f"❌ 转账过程中发生异常: {err_msg}")
            # 记录失败日志
            self._log_transaction(agent_signature, to_address, amount, "N/A", f"ERROR: {err_msg}")
            return None
    
        


# --- 外部调用入口 ---

def execute_agent_payment(agent_signature: str, to_address: str, amount_sol: float):
    """
    :param agent_signature: 谁在花这笔钱？(Agent的名字或ID)
    :param to_address: 给谁转？
    :param amount_sol: 转多少？
    """
    # 实例化钱包 (会自动加载环境)
    wallet = AgentWallet()
    
    # 执行转账并记录日志
    tx = wallet.transfer_sol(to_address, amount_sol, agent_signature)
    
    return tx

# --- 测试代码 ---
if __name__ == "__main__":
    print("--- 正在测试 AgentWallet 类 ---")
    
    test_agent_name = "NewsieAI_Core_Agent_001"
    
    my_wallet = AgentWallet()
    my_wallet.check_balance()
    xinfor = my_wallet.transfer_sol(receive_address, 0.1, test_agent_name)
    print("hash",xinfor)
