import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import httpx
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
import pytz
# Reuse existing news agent
from .retriv import retriv_run_agent
from database import get_latest_news_for_user,get_starred_news_for_user
load_dotenv()


@dataclass
class UserProfile:
    user_id: str
    timezone: str = "UTC"
    preferred_notification_times: List[str] = field(default_factory=list)  # ["09:00", "20:30"]
    content_preferences: List[str] = field(default_factory=list)  # ["tech", "crypto", ...]
    x_usernames: List[str] = field(default_factory=list)  # ["@elonmusk", "@openai"]
    raw_profile: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleItem:
    start_time: str  # ISO 8601 or "YYYY-MM-DD HH:MM"
    end_time: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class PersonalAssistantAgent:
    """
    [Personal Assistant]: Time & content orchestration agent.

    Responsibilities:
    - Ingest user profile + recent schedule log + input_time + input_content.
    - (Mock) Track user's current time zone and location based on submitted IP.
    - Decide WHEN to trigger a new information gathering task.
    - Call other agents (e.g., NewsRetrievalAgent via retriv_run_agent) to gather info.
    - Expose a separate function that returns gathered info for downstream delivery.
    """

    def __init__(
        self,
        user_profile: Dict[str, Any],
        schedule_log: List[Dict[str, Any]],
        input_time: Optional[str] = None,
        input_content: Optional[str] = None,
        user_ip: Optional[str] = None,
    ):
        """
        :param user_profile: Arbitrary profile dict, will be normalized into UserProfile.
        :param schedule_log: List of schedule entries for recent days.
        :param input_time: Time string for when user invoked new_gathering (local time).
        :param input_content: What the user wants to explore (free-form text).
        :param user_ip: (Optional) IP address for time zone / location derivation (mock for now).
        """
        self.raw_user_profile = user_profile or {}
        self.schedule_log_raw = schedule_log or []
        self.input_time = input_time
        self.input_content = input_content
        self.user_ip = user_ip

        # Normalize profile and schedule
        self.profile = self._parse_user_profile(self.raw_user_profile)
        self.schedule_log = self._parse_schedule_log(self.schedule_log_raw)

        # LLM / MCP core components (for future extension, e.g., more complex reasoning)
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
        )
        # self.mcp_client: Optional[MultiServerMCPClient] = None
        self.mcp_client = None
        self.agent_runnable = None

        # Internal state for gathered info
        self._gathering_result: Optional[str] = None
        self._planned_notification_time: Optional[datetime] = None

    # ---------------------------------------------------------------------
    # Data parsing helpers
    # ---------------------------------------------------------------------
    def _parse_user_profile(self, profile: Dict[str, Any]) -> UserProfile:
        """Normalize arbitrary profile dict into UserProfile dataclass."""
        preferred_times = profile.get("preferred_notification_times", [])
        if isinstance(preferred_times, str):
            preferred_times = [preferred_times]

        content_prefs = profile.get("content_preferences", [])
        if isinstance(content_prefs, str):
            content_prefs = [content_prefs]

        x_usernames = profile.get("x_usernames", [])
        if isinstance(x_usernames, str):
            x_usernames = [x_usernames]

        return UserProfile(
            user_id=str(profile.get("user_id", "anonymous")),
            timezone=profile.get("timezone", "UTC"),
            preferred_notification_times=preferred_times,
            content_preferences=content_prefs,
            x_usernames=x_usernames,
            raw_profile=profile,
        )

    def _parse_schedule_log(self, schedule_log: List[Dict[str, Any]]) -> List[ScheduleItem]:
        """Normalize raw schedule entries into ScheduleItem list."""
        normalized: List[ScheduleItem] = []
        for item in schedule_log:
            normalized.append(
                ScheduleItem(
                    start_time=item.get("start_time") or item.get("start") or "",
                    end_time=item.get("end_time") or item.get("end"),
                    title=item.get("title"),
                    location=item.get("location"),
                    meta={k: v for k, v in item.items() if k not in {"start_time", "start", "end_time", "end", "title", "location"}},
                )
            )
        return normalized

    # ---------------------------------------------------------------------
    # MCP setup & mock time/place checker
    # ---------------------------------------------------------------------
    async def setup_mcp_client(self):
        """
        Connect to any MCP services needed for this assistant.

        For now this is a placeholder. When you later add a "calendar" or "geo" MCP,
        you can plug it in here.
        """
        # Example config placeholder

        mcp_config = {
            "date_time_tools": {
                "url": f"http://localhost:{os.getenv('DATE_TIME_HTTP_PORT', '8002')}/mcp",
                "transport": "streamable-http"
            }
        }

        if mcp_config:
            self.mcp_client = MultiServerMCPClient(mcp_config)
        else:
            self.mcp_client = None

    async def check_time_and_place(self) -> Dict[str, Any]:
        """
        Real function: call the MCP tool 'get_location_and_time'.
        """
        try:
            # 1. 使用 ip-api.com 获取位置和时区 (免费版，非商业用途)
            url = f"http://ip-api.com/json/{self.user_ip}"
                    
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()

            if data.get("status") != "success":
                print(f"Failed to retrieve data for IP: {self.user_ip}")
                return json.dumps({"error": f"Could not retrieve data for IP {self.user_ip}"})

            timezone_str = data.get("timezone", "UTC")
            city = data.get("city", "Unknown")
            country = data.get("country", "Unknown")
            
            # 2. 根据时区计算当前时间
            try:
                tz = pytz.timezone(timezone_str)
                local_time = datetime.now(tz).isoformat()
            except Exception as e:
                print(f"Timezone conversion error: {e}")
                local_time = datetime.now().isoformat()

                result = {
                    "ip": self.user_ip,
                    "location": f"{city}, {country}",
                    "timezone": timezone_str,
                    "current_local_time": local_time
                }
                
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            print(f"Error in get_location_and_time: {str(e)}")
            return f"Error processing request: {str(e)}"

        # if not self.mcp_client:
        #     await self.setup_mcp_client()

        # # default ip address is google's public dns server
        # target_ip = self.user_ip if self.user_ip else "8.8.8.8"

        # try:
        #     # 调用 geo_server.py 中的 get_location_and_time 工具
        #     result = await self.mcp_client.call_tool(
        #         "geo_service", 
        #         "get_location_and_time", 
        #         {"ip_address": target_ip}
        #     )
            
        #     #return the result
        #     return {
        #         "ip": target_ip,
        #         "guessed_timezone": result.get("timezone", "UTC"),
        #         "guessed_location": result.get("location", "Unknown"),
        #         "server_time_utc": datetime.utcnow().isoformat(),
        #         "local_time": result.get("current_local_time") # 新增字段
        #     }

        # except Exception as e:
        #     print(f"MCP Call Failed: {e}")
        #     # Fallback to profile default if MCP fails
        #     return {
        #         "ip": self.user_ip,
        #         "guessed_timezone": self.profile.timezone,
        #         "guessed_location": "Fallback Location",
        #         "server_time_utc": datetime.utcnow().isoformat(),
        #     }

    # ---------------------------------------------------------------------
    # Core orchestration logic
    # ---------------------------------------------------------------------
    def _decide_notification_time(self) -> Tuple[datetime, str]:
        """
        Decide when to trigger the new_gathering, based on:
        - user profile preferred_notification_times
        - schedule_log (basic gap-finding heuristic)
        - input_time as "now" fallback
        """
        # Base "now" – if user provided an explicit time, prefer that
        if self.input_time:
            try:
                # Accept "YYYY-MM-DD HH:MM" or "HH:MM"
                if len(self.input_time.strip()) <= 5:
                    today = datetime.now()
                    hour, minute = map(int, self.input_time.split(":"))
                    base_time = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    base_time = datetime.fromisoformat(self.input_time)
            except Exception:
                base_time = datetime.now()
        else:
            base_time = datetime.now()

        # If user has preferred_notification_times, try the next one that is >= now
        candidates: List[datetime] = []
        for t in self.profile.preferred_notification_times:
            try:
                h, m = map(int, t.split(":"))
                candidate = base_time.replace(hour=h, minute=m, second=0, microsecond=0)
                if candidate < base_time:
                    # push to next day
                    candidate = candidate + timedelta(days=1)
                candidates.append(candidate)
            except Exception:
                continue

        if candidates:
            planned = min(candidates)
        else:
            # Fallback: 5 minutes after base_time
            planned = base_time + timedelta(minutes=5)

        reason = "Planned based on preferred_notification_times" if candidates else "Fallback: 5 minutes after base_time"
        self._planned_notification_time = planned
        return planned, reason

    async def _call_news_agent(self, prompt: str) -> str:
        """
        Call the existing NewsRetrievalAgent via retriv_run_agent.
        This is how PersonalAssistant 'calls other agents'.
        """
        # Build user_context from profile for filtering preferences
        user_context = {
            "user_id": self.profile.user_id,
            "timezone": self.profile.timezone,
            "preferred_notification_times": self.profile.preferred_notification_times,
            "content_preferences": self.profile.content_preferences,
            "x_usernames": self.profile.x_usernames,
            "description": self.raw_user_profile.get("description", [])
        }
        
        # Use prompt as query_body
        query_body = prompt
        
        result = await retriv_run_agent(
            user_context=user_context,
            query_body=query_body,
            user_profile=None
        )
        return result
    async def crafting_context_string(self) -> Dict[str, Any]:
        """
        Craft a context string for the news agent.
        """
        preference_str = ", ".join(self.profile.content_preferences) or "general interests"
        base_content = self.input_content or "high quality daily briefing"
        user_id = self.profile.user_id
        user_history = get_latest_news_for_user(user_id) #history of yesterday's news
        user_starred_news = get_starred_news_for_user(user_id) # starred news

        #here a LLM should read user history and current time and place, and craft a context string for the news agent.
        context_string = f"The user ({self.profile.user_id}) has preferences: {preference_str}. They requested: {base_content}."

        return f"The user ({self.profile.user_id}) has preferences: {preference_str}. They requested: {base_content}."


    async def plan_and_gather(self) -> Dict[str, Any]:
        """
        Main high-level function:
        - Check time/place (mock for now).
        - Decide best notification time.
        - Construct a news-gathering prompt based on user preferences & input_content.
        - Immediately call the news agent (for now; you can later defer call until planned time).
        - Store gathered info internally and return a planning summary.
        """
        time_place_info = await self.check_time_and_place()
        planned_time, reason = self._decide_notification_time()

        # Build a context string for the news agent
        preference_str = ", ".join(self.profile.content_preferences) or "general interests"
        base_content = self.input_content or "high quality daily briefing"

        news_context = (
            f"The user ({self.profile.user_id}) has preferences: {preference_str}. "
            f"They requested: {base_content}. "
            # f"Plan a news package suitable for delivery at approx {planned_time.isoformat()} "
            # f"in timezone {self.profile.timezone}."
        )

        gathered = await self._call_news_agent(news_context)
        self._gathering_result = gathered

        return {
            "time_place": time_place_info,
            "planned_notification_time": planned_time.isoformat(),
            "planning_reason": reason,
            "news_context_sent": news_context,
            "gathered_preview": str(gathered)[:300],
        }

    # ---------------------------------------------------------------------
    # LLM-based reasoning hook (optional)
    # ---------------------------------------------------------------------
    async def create_agent_graph(self):
        """
        Optional: full LangGraph agent that can reason over profile + schedule.
        For now, this just wires a generic system prompt; you can grow this later.
        """
        if not self.mcp_client:
            await self.setup_mcp_client()

        tools = []
        if self.mcp_client:
            tools = await self.mcp_client.get_tools()

        context_payload = {
            "user_profile": self.profile.raw_profile,
            "schedule_log": [s.__dict__ for s in self.schedule_log],
            "input_time": self.input_time,
            "input_content": self.input_content,
        }
        formatted = json.dumps(context_payload, indent=2, ensure_ascii=False)

        system_prompt = f"""You are the Personal Assistant agent.

You receive:
- USER PROFILE
- RECENT SCHEDULE LOG
- INPUT_TIME (when the user invoked a new gathering)
- INPUT_CONTENT (what they want to explore)

Your responsibilities:
1. Analyze the user's typical busy / free periods from the schedule.
2. Respect the user's preferred_notification_times when choosing when to send content.
3. Align suggested topics with the user's content_preferences and INPUT_CONTENT.
4. Output a concise plan for WHEN to send WHAT kind of content, and WHY.

Context JSON:
{formatted}
"""

        self.agent_runnable = create_agent(self.llm, tools, system_prompt=system_prompt)

    async def run_reasoning(self) -> str:
        """
        Optional: run the reasoning-only LangGraph agent.
        """
        if not self.agent_runnable:
            await self.create_agent_graph()

        msg = "Analyze the context JSON and propose an optimized notification schedule and content plan."
        inputs = {"messages": [HumanMessage(content=msg)]}
        result = await self.agent_runnable.ainvoke(inputs)
        return result["messages"][-1].content

    async def cleanup(self):
        """Clean up MCP connections if any."""
        if self.mcp_client:
            try:
                await self.mcp_client.disconnect()
            except Exception:
                pass

    # ---------------------------------------------------------------------
    # External accessors
    # ---------------------------------------------------------------------
    def get_gathered_info(self) -> Optional[str]:
        """
        Return the previously gathered information package.
        """
        return self._gathering_result

    def get_planned_notification_time(self) -> Optional[datetime]:
        """Return the planned notification time (if already computed)."""
        return self._planned_notification_time


async def run_personal_assistant(
    user_profile: Dict[str, Any],
    schedule_log: List[Dict[str, Any]],
    input_time: Optional[str],
    input_content: Optional[str],
    user_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience entry point for invoking the Personal Assistant.

    Returns a dict with:
    - planning summary
    - full gathered_info (for your UI / delivery layer)
    """
            #     user_profile = {
        #     "user_id": profile.email.split("@")[0],
        #     "name": profile.name,
        #     "email": profile.email,
        #     "timezone": "UTC",
        #     "preferred_notification_times": notification_times,
        #     "content_preferences": interests_list,
        # }

        #     result = await run_personal_assistant(
        #     user_profile=user_profile,
        #     schedule_log=[],
        #     input_time=None,
        #     input_content="daily briefing based on user preferences",
        #     user_ip=client_ip,
        # )

    #         def __init__(
    #     self,
    #     user_profile: Dict[str, Any],
    #     schedule_log: List[Dict[str, Any]],
    #     input_time: Optional[str] = None,
    #     input_content: Optional[str] = None,
    #     user_ip: Optional[str] = None,
    # ):
    agent = PersonalAssistantAgent(
        user_profile=user_profile, #it has user_id, timezone, preferred_notification_times, content_preferences
        schedule_log=schedule_log,
        input_time=input_time,
        input_content=input_content,
        user_ip=user_ip,
    )
    print(f"user_ip: {user_ip}")
    try:
        planning_summary = await agent.plan_and_gather()
        gathered_info = agent.get_gathered_info()
        planning_summary["gathered_info_full"] = gathered_info
        return planning_summary
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    # Minimal local test stub
    mock_profile = {
        "user_id": "test_user_01",
        "timezone": "UTC",
        "preferred_notification_times": ["09:00", "21:30"],
        "content_preferences": ["technology", "crypto"],
    }
    mock_schedule = [
        {
            "start_time": "2025-01-07 09:00",
            "end_time": "2025-01-07 11:00",
            "title": "Morning meeting",
            "location": "Office",
        }
    ]

    async def _demo():
        res = await run_personal_assistant(
            user_profile=mock_profile,
            schedule_log=mock_schedule,
            input_time="10:15",
            input_content="today's key market and tech news",
            user_ip="203.0.113.10",
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))

    asyncio.run(_demo())


