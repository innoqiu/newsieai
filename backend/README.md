# NewsieAI - Intelligent News Retrieval & Payment System

A comprehensive AI-powered system that combines intelligent news retrieval, automated payment processing, and personal assistant capabilities using LangChain agents and the Model Context Protocol (MCP).

## Overview

NewsieAI is a multi-agent system built on LangChain that provides:
- **Intelligent News Retrieval**: Context-aware news gathering from Alpha Vantage API
- **Automated Payment Processing**: Solana blockchain payments with budget-aware decision making
- **Personal Assistant**: Time-aware content orchestration with location-based scheduling
- **X402 Payment Protocol**: HTTP 402-based micropayment system for premium content

## Architecture

The system follows a modular architecture with three main components:

### 1. **Agents** (`agents/`)
LangChain-based intelligent agents that orchestrate tasks:
- **News Retrieval Agent** (`retriv.py`): Searches and summarizes market news
- **Accountant Agent** (`accountant.py`): Evaluates payment requests and executes Solana transactions
- **Personal Assistant Agent** (`personal_assistant.py`): Orchestrates content delivery based on user profile and schedule

### 2. **MCP Tools** (`tools/`)
FastMCP servers exposing tools via HTTP:
- **Retrieval Tools** (`retrival_tools.py`): Market news and Web3 news search
- **Payment Tool** (`tool_pay.py`): Solana payment execution
- **Geo/Time Server** (`geo_server.py`): IP-based location and timezone detection
- **MCP Service Manager** (`start_mcp.py`): Unified service launcher

### 3. **Wallet System** (`wallet/`)
Solana blockchain integration:
- **Agent Wallet** (`wallet.py`): Keypair management and transaction execution
- **Wallet Utilities** (`tools/walletx.py`): Payment wrapper functions

## Project Structure

```
newsieai/
├── agents/                    # LangChain agents
│   ├── retriv.py             # News retrieval agent
│   ├── accountant.py         # Payment decision agent
│   ├── personal_assistant.py # Content orchestration agent
│   └── scaffold              # Agent development template
│
├── tools/                     # MCP tool servers
│   ├── retrival_tools.py     # News search tools (port 8001)
│   ├── tool_pay.py           # Payment tool (port 8007)
│   ├── geo_server.py         # Location/time tool (port 8002)
│   ├── walletx.py            # Wallet utilities
│   └── start_mcp.py          # MCP service manager
│
├── wallet/                    # Solana wallet system
│   └── wallet.py             # Agent wallet implementation
│
├── datalog/                   # Generated data logs
│   ├── news_*.txt            # News gathering results
│   └── transfer_log.txt      # Payment transaction logs
│
├── prompts/                    # Agent prompt templates
│   ├── retriv_prompts.py
│   ├── report_prompts.py
│   └── sub_retriv_prompt.py
│
├── main.py                    # Main entry point & test menu
├── test_server.py            # X402 payment protocol server
├── test_x402_flow.py         # Payment flow test script
├── generate_a_wallet.py      # Wallet keypair generator
└── README.md                  # This file
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Solana Devnet account (for payment testing)
- API keys for:
  - OpenAI (for LLM agents)
  - Alpha Vantage (for news retrieval)
  - Any future information source 

### Installation

1. **Clone the repository**:
```bash
cd D:\ICP\newsieai
```

2. **Install dependencies**:
```bash
pip install langchain langchain-openai langchain-mcp-adapters fastmcp python-dotenv requests solana solders httpx pytz
```

3. **Set up environment variables**:
Create a `.env` file in the project root:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Alpha Vantage API
ALPHAADVANTAGE_API_KEY=your_alpha_vantage_key_here

# MCP Service Ports
SEARCH_HTTP_PORT=8001
PAY_HTTP_PORT=8007
DATE_TIME_HTTP_PORT=8002

# Solana Wallet (for payment testing)
SERVER_SECRETKEY=your_base58_private_key
SERVER_PUBKEY=your_public_key
```

4. **Generate a wallet** (optional, for payment testing):
```bash
python generate_a_wallet.py
```
Copy the generated keys to your `.env` file.

## Usage

### Main Menu Interface

Run the main script to access the interactive menu:

```bash
python main.py
```

**Menu Options:**
1. **Test News Retrieval Agent**: Search for market news with custom context
2. **Test Accountant Agent**: Test automated payment processing (requires `test_server.py`)
3. **Test Personal Assistant Agent**: Orchestrate news delivery based on user profile and schedule
4. **Exit**

### 1. News Retrieval Agent

Searches for market news using Alpha Vantage API with intelligent context understanding.

**Features:**
- Context-aware search queries
- Support for stock tickers (e.g., "AAPL", "TSLA")
- Topic-based filtering (e.g., "technology", "crypto")
- Automatic summarization

**Example:**
```python
from agents.retriv import retriv_run_agent

result = await retriv_run_agent(
    "Search for latest news about Apple Inc. and technology developments"
)
```

### 2. Accountant Agent

Evaluates payment requests against user budget constraints and executes Solana transactions.

**Features:**
- Budget-aware decision making
- User profile integration (tier, preferences)
- Automatic payment execution via MCP
- Transaction logging

**Workflow:**
1. Receives HTTP 402 response with payment request
2. Evaluates against user profile constraints
3. Executes payment if approved
4. Returns transaction hash

**Example:**
```python
from agents.accountant import run_accountant_service

user_profile = {
    "user_id": "user_01",
    "tier": "VIP_PLATINUM",
    "custom_budget_limit": 0.1,  # SOL
    "preference": "interested in crypto market"
}

payment_data = {
    "amount": 0.05,
    "receiver_id": "target_solana_address"
}

result = await run_accountant_service(payment_data, user_profile)
```

### 3. Personal Assistant Agent

Orchestrates content delivery based on user profile, schedule, and preferences.

**Features:**
- Time-aware scheduling
- IP-based location and timezone detection
- Integration with News Retrieval Agent
- Automatic content saving to `datalog/`

**Initialization Parameters:**
- `user_profile`: User preferences and notification times
- `schedule_log`: Recent schedule entries
- `input_time`: When the assistant was invoked
- `input_content`: What content to explore
- `user_ip`: IP address for location detection (optional)

**Example:**
```python
from agents.personal_assistant import run_personal_assistant

user_profile = {
    "user_id": "alice",
    "timezone": "UTC",
    "preferred_notification_times": ["09:00", "21:30"],
    "content_preferences": ["technology", "crypto", "macro"]
}

schedule_log = [
    {
        "start_time": "2025-01-07 09:00",
        "end_time": "2025-01-07 11:00",
        "title": "Morning Meeting"
    }
]

result = await run_personal_assistant(
    user_profile=user_profile,
    schedule_log=schedule_log,
    input_time="10:15",
    input_content="today's key market and tech news",
    user_ip="203.0.113.10"
)
```

**Output:**
- Planning summary with notification time
- Gathered news content (saved to `datalog/news_YYYYMMDD_HHMMSS.txt`)

## MCP Tools

### Retrieval Tools (`retrival_tools.py`)

**Port:** 8001 (configurable via `SEARCH_HTTP_PORT`)

**Available Tools:**
- `get_market_news(query, tickers, topics)`: Search market news
- `get_web3_news(query, topics)`: Search Web3-specific news

**Start manually:**
```bash
python tools/retrival_tools.py
```

### Payment Tool (`tool_pay.py`)

**Port:** 8007 (configurable via `PAY_HTTP_PORT`)

**Available Tools:**
- `pay_solana(to_address, amount, reason)`: Execute Solana payment

**Start manually:**
```bash
python tools/tool_pay.py
```

### Geo/Time Server (`geo_server.py`)

**Port:** 8002 (configurable via `DATE_TIME_HTTP_PORT`)

**Available Tools:**
- `get_location_and_time(ip_address)`: Get location, timezone, and local time from IP

**Start manually:**
```bash
python tools/geo_server.py
```

### MCP Service Manager

Start all services at once:
```bash
python tools/start_mcp.py
```

## X402 Payment Protocol

The system implements HTTP 402 (Payment Required) for micropayments.

### Testing the Payment Flow

1. **Start the test server**:
```bash
python test_server.py
```

2. **Run the payment flow test**:
```bash
python test_x402_flow.py
```

**Flow:**
1. Client requests premium content → Server returns HTTP 402
2. Accountant Agent evaluates payment request
3. If approved, payment is executed on Solana
4. Client redeems content with transaction hash

## Data Logging

### News Logs
Gathered news content is automatically saved to:
```
datalog/news_YYYYMMDD_HHMMSS.txt
```

### Payment Logs
All transactions are logged to:
```
datalog/transfer_log.txt
```

Format: `[timestamp] Agent | To: address | Amount: X SOL | Hash: tx_hash | Status`

## Wallet Management

### Generate New Wallet
```bash
python generate_a_wallet.py
```

Outputs:
- Public Key (Base58)
- Secret Key (Base58) - **Keep this secure!**

### Wallet Features
- Automatic keypair generation and storage
- Balance checking
- Transaction execution
- Transaction logging

## Testing

### Unit Testing

**Test News Retrieval:**
```bash
python main.py
# Select option 1
```

**Test Payment Flow:**
```bash
# Terminal 1
python test_server.py

# Terminal 2
python main.py
# Select option 2
```

**Test Personal Assistant:**
```bash
python main.py
# Select option 3
```

### Integration Testing

**Full X402 Flow:**
```bash
python test_x402_flow.py
```

## Agent Development

Follow the scaffold pattern in `agents/scaffold` for creating new agents:

1. **Inherit standard structure:**
   - `__init__()`: Initialize context and LLM
   - `setup_mcp_client()`: Connect to MCP services
   - `create_agent_graph()`: Build LangGraph agent
   - `run()`: Execute agent logic
   - `cleanup()`: Clean up connections

2. **Use MCP tools** (never hardcode):
   - All tools must come from MCP servers
   - Use `MultiServerMCPClient` to connect

3. **Follow async pattern:**
   - All agent methods should be `async`
   - Use `asyncio.run()` for entry points

## Troubleshooting

### Port Already in Use
If a port is already in use:
1. Check what's using it: `netstat -ano | findstr :8001`
2. Change the port in `.env` file
3. Or stop the conflicting process

### MCP Server Not Starting
- Verify API keys are set in `.env`
- Check port availability
- Ensure all dependencies are installed
- Check server logs for errors

### Agent Connection Issues
- Ensure MCP server is running before starting agent
- Verify port numbers match in both server and client
- Check network connectivity

### Payment Failures
- Verify wallet has sufficient balance (check with `wallet.check_balance()`)
- Ensure you're using Solana Devnet
- Check transaction logs in `datalog/transfer_log.txt`

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `ALPHAADVANTAGE_API_KEY` | Alpha Vantage API key (required) | - |
| `SEARCH_HTTP_PORT` | Retrieval tools port | `8001` |
| `PAY_HTTP_PORT` | Payment tool port | `8007` |
| `DATE_TIME_HTTP_PORT` | Geo/time server port | `8002` |
| `SERVER_SECRETKEY` | Solana wallet private key (Base58) | - |
| `SERVER_PUBKEY` | Solana wallet public key | - |

## Key Technologies

- **LangChain**: Agent framework and LLM integration
- **FastMCP**: MCP server implementation
- **Solana SDK**: Blockchain payment processing
- **Alpha Vantage API**: Market news data
- **FastAPI**: HTTP 402 payment server
- **Python asyncio**: Asynchronous execution

## Contributing

When adding new agents or tools:
1. Follow the scaffold pattern in `agents/scaffold`
2. Use MCP tools (never hardcode functionality)
3. Maintain async/await patterns
4. Add appropriate error handling
5. Update this README

## License

Not yet applicable


**For questions or issues, please check the troubleshooting section or review the agent implementations in `agents/` directory.**

contact innoqiu99@gmail.com
