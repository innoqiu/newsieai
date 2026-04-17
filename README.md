##MY NEW PROJECT FOXMO (HELPING WITH FOMO BY IMPROVING, INTEGRATING, AND MANAGING INFORMATION SOURCES) IS ONGOING, FOLLOW THE CHANNEL FOR MAJOR UPDATE.

# NewsieAI

NewsieAI is an AI-powered workflow system for personalized news discovery, profile-aware retrieval, and payment-gated content access.  
It combines a React workflow UI with a FastAPI backend, multi-agent orchestration, MCP tools, and Solana-based payment verification.

## Project Overview

This project is built around a **dual-agent architecture**:

1. **Dynamic Profile Builder Agent**  
   An interactive, context-aware interface that helps collect and update external user input (preferences, profile signals, and feedback) to keep user context fresh.

2. **Retrieval Agent**  
   A smart retrieval pipeline that searches for new content (especially X/Twitter and topic-based signals), structures outputs, and supports profile-aware filtering in smart mode.

3. **Accoutant Agent (Not Secure Now)**  
   A SmartPayment-compatible agent that evaluate the value of the content and automatically pays via Solona network.

## Key Highlights

- **Dual-agent system for personalization + retrieval**  
  User intent and preferences are captured continuously, then used by retrieval logic to improve relevance.

- **SmartPayment-compatible flow (x402 + Web3 Solana address payment)**  
  Supports HTTP 402-style paid content access with Solana-chain payment execution and verification, including handling of payment amount and receiver address via agent + tool workflow.

- **Multiple MCP tools integrated into the workflow**  
  The system uses MCP services for retrieval, payment execution/re-access, profile management, and geo/time context, enabling modular extension and cleaner agent-tool boundaries.

- **Thread-based automation and scheduling**  
  Workflows can be saved as threads and executed in interval/daily schedules with timezone support.
  <img width="2449" height="1330" alt="image" src="https://github.com/user-attachments/assets/19041b55-5839-45e2-abb7-c2f1c9d6cfdd" />


- **Structured output and persistence**  
  Retrieved items are normalized into structured records and stored for later inbox/history use.

- **End-to-end product surface**  
  Includes auth, profile APIs, thread/workflow management, frontend workflow studio, and backend execution pipeline.

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


## Current Scope and TODO

1. **Current support is limited to general search intent and X-platform information retrieval.**  
   Next step: strengthen search logic for better extensibility across additional sources and richer retrieval strategies.

2. **Security and prompt engineering need further hardening.**  
   Next step: improve LLM guardrails and prompt tuning, with special focus on payment-related task safety and decision quality.
