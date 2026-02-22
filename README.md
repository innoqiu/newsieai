# NewsieAI

NewsieAI is an AI-powered workflow system for personalized news discovery, profile-aware retrieval, and payment-gated content access.  
It combines a React workflow UI with a FastAPI backend, multi-agent orchestration, MCP tools, and Solana-based payment verification.

## Project Overview

This project is built around a **dual-agent architecture**:

1. **Dynamic Profile Builder Agent**  
   An interactive, context-aware interface that helps collect and update external user input (preferences, profile signals, and feedback) to keep user context fresh.

2. **Retrieval Agent**  
   A smart retrieval pipeline that searches for new content (especially X/Twitter and topic-based signals), structures outputs, and supports profile-aware filtering in smart mode.

## Key Highlights

- **Dual-agent system for personalization + retrieval**  
  User intent and preferences are captured continuously, then used by retrieval logic to improve relevance.

- **SmartPayment-compatible flow (x402 + Web3 Solana address payment)**  
  Supports HTTP 402-style paid content access with Solana-chain payment execution and verification, including handling of payment amount and receiver address via agent + tool workflow.

- **Multiple MCP tools integrated into the workflow**  
  The system uses MCP services for retrieval, payment execution/re-access, profile management, and geo/time context, enabling modular extension and cleaner agent-tool boundaries.

- **Thread-based automation and scheduling**  
  Workflows can be saved as threads and executed in interval/daily schedules with timezone support.

- **Structured output and persistence**  
  Retrieved items are normalized into structured records and stored for later inbox/history use.

- **End-to-end product surface**  
  Includes auth, profile APIs, thread/workflow management, frontend workflow studio, and backend execution pipeline.

## Current Scope and TODO

1. **Current support is limited to general search intent and X-platform information retrieval.**  
   Next step: strengthen search logic for better extensibility across additional sources and richer retrieval strategies.

2. **Security and prompt engineering need further hardening.**  
   Next step: improve LLM guardrails and prompt tuning, with special focus on payment-related task safety and decision quality.
