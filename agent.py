import importlib.util
import json
import os
import re
from typing import Any, Dict, List, Optional

_tools_path = os.path.join(os.path.dirname(__file__), "tools.py")
_spec = importlib.util.spec_from_file_location("root_tools", _tools_path)
_tools = importlib.util.module_from_spec(_spec)
if _spec and _spec.loader:
    _spec.loader.exec_module(_tools)

get_weather_forecast = _tools.get_weather_forecast
plan_trip = _tools.plan_trip
search_flights = _tools.search_flights
search_hotels = _tools.search_hotels
search_places = _tools.search_places
format_trip_summary = _tools.format_trip_summary

try:
    from langchain.agents.factory import create_agent
    from langchain_core.language_models.chat_models import BaseChatModel, ChatGeneration, ChatResult
    from langchain_core.messages import AIMessage, BaseMessage
    from langchain_core.tools.simple import Tool
    from langchain_core.callbacks import CallbackManagerForLLMRun
    LANGCHAIN_AVAILABLE = True
except Exception:
    LANGCHAIN_AVAILABLE = False

KNOWN_CITIES = [
    "Delhi",
    "Mumbai",
    "Goa",
    "Bangalore",
    "Chennai",
    "Hyderabad",
    "Kolkata",
    "Jaipur",
]


def _normalize_query(query: str) -> str:
    return query.strip().lower()


def _extract_city(query: str) -> Optional[str]:
    lower = _normalize_query(query)
    for city in KNOWN_CITIES:
        if city.lower() in lower:
            return city
    return None


def _extract_number(query: str, default: int = 3) -> int:
    match = re.search(r"(\d+)\s*(?:day|days)", query, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)", query)
    if match:
        return int(match.group(1))
    return default


def _extract_route(query: str) -> Dict[str, str]:
    lower = _normalize_query(query)
    origin = None
    destination = None

    from_match = re.search(r"from\s+([a-zA-Z]+)", lower)
    to_match = re.search(r"to\s+([a-zA-Z]+)", lower)
    if from_match:
        origin = from_match.group(1).title()
    if to_match:
        destination = to_match.group(1).title()

    city_matches = [city for city in KNOWN_CITIES if city.lower() in lower]
    if not origin or not destination:
        remaining_cities = [c for c in city_matches if c.title() != origin and c.title() != destination]
        if not origin and not destination:
            if len(remaining_cities) >= 2:
                origin = remaining_cities[0]
                destination = remaining_cities[-1]
            elif len(remaining_cities) == 1:
                destination = remaining_cities[0]
        elif not origin and remaining_cities:
            origin = remaining_cities[0]
        elif not destination and remaining_cities:
            destination = remaining_cities[-1]

    return {"origin": origin, "destination": destination}


def _human_readable(result: Any) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, ensure_ascii=False)


def _format_agent_response(content: str) -> str:
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content

    if (
        isinstance(parsed, dict)
        and all(key in parsed for key in ["destination", "origin", "flight", "hotel", "places", "weather"])
    ):
        return format_trip_summary(parsed)

    return json.dumps(parsed, indent=2, ensure_ascii=False)


if LANGCHAIN_AVAILABLE:
    class TravelPlannerModel(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "travel-planner"

        def bind_tools(self, tools: Any, tool_choice: Any = None, **kwargs: Any) -> "TravelPlannerModel":
            return self

        def _generate(self, messages: List[BaseMessage], stop=None, run_manager: CallbackManagerForLLMRun | None = None, **kwargs: Any):
            prompt = ""
            if messages:
                raw = messages[-1].content
                if isinstance(raw, list):
                    raw = " ".join(str(item) for item in raw)
                prompt = str(raw)

            response = self._route_prompt(prompt)
            return ChatResult(generations=[ChatGeneration(text=response, message=AIMessage(content=response))])

        def _route_prompt(self, prompt: str) -> str:
            lower = _normalize_query(prompt)
            route = _extract_route(prompt)
            origin = route.get("origin")
            destination = route.get("destination") or _extract_city(prompt)
            days = _extract_number(prompt, default=3)

            if "weather" in lower:
                city = destination or _extract_city(prompt)
                if not city:
                    return "Please tell me the city for weather information."
                return _human_readable(get_weather_forecast(city))

            if "hotel" in lower:
                city = destination or _extract_city(prompt)
                if not city:
                    return "Please tell me the city to search for hotels."
                return _human_readable(search_hotels(city))

            if "place" in lower or "attraction" in lower or "sight" in lower:
                city = destination or _extract_city(prompt)
                if not city:
                    return "Please tell me the city to search for places."
                return _human_readable(search_places(city))

            if "flight" in lower or "fly" in lower:
                if not destination:
                    return "Please tell me your flight destination."
                if not origin:
                    origin = "Hyderabad"
                return _human_readable(search_flights(origin, destination))

            if "plan" in lower or "trip" in lower:
                if not destination:
                    return "Please tell me the trip destination."
                return _human_readable(plan_trip(destination, days, origin or "Hyderabad"))

            if destination and days:
                return _human_readable(plan_trip(destination, days, origin or "Hyderabad"))

            return "I can help you search flights, hotels, places, weather, or plan a trip."

    class TravelAgent:
        def __init__(self) -> None:
            self.model = TravelPlannerModel()
            tool_list = [
                Tool.from_function(search_flights, name="search_flights", description="Search scheduled flights by origin and destination."),
                Tool.from_function(search_hotels, name="search_hotels", description="Search hotels in a city and return the best-rated option."),
                Tool.from_function(search_places, name="search_places", description="Search top tourist places in a city."),
                Tool.from_function(get_weather_forecast, name="get_weather_forecast", description="Get daily weather forecast for a city."),
                Tool.from_function(plan_trip, name="plan_trip", description="Create a complete trip plan including flight, hotel, places, and weather."),
            ]
            self.agent = create_agent(
                self.model,
                tools=tool_list,
                system_prompt=(
                    "You are a travel planning assistant. Use the available travel tools and return JSON or human-readable summaries."
                ),
            )

        def run(self, prompt: str) -> str:
            result = self.agent.invoke({"messages": [{"type": "human", "content": prompt}]})
            if isinstance(result, dict):
                messages = result.get("messages", [])
                if messages:
                    # Return the final AI response if available, otherwise fall back to the last message
                    for message in reversed(messages):
                        content = None
                        if isinstance(message, dict) and message.get("type") == "ai":
                            content = message.get("content", str(message))
                        elif not isinstance(message, dict) and getattr(message, "type", None) == "ai":
                            content = getattr(message, "content", str(message))
                        if content is not None:
                            return _format_agent_response(content)
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        return _format_agent_response(last_message.get("content", str(last_message)))
                    return _format_agent_response(getattr(last_message, "content", str(last_message)))
            return _human_readable(result)

else:
    class TravelAgent:
        def __init__(self) -> None:
            self.agent = None

        def run(self, prompt: str) -> str:
            lower = _normalize_query(prompt)
            if "plan" in lower or "trip" in lower:
                route = _extract_route(prompt)
                destination = route.get("destination") or _extract_city(prompt)
                origin = route.get("origin")
                days = _extract_number(prompt, default=3)
                if not destination:
                    return "Please tell me the trip destination."
                return format_trip_summary(plan_trip(destination, days, origin))
            if "hotel" in lower:
                city = _extract_route(prompt).get("destination") or _extract_city(prompt)
                if not city:
                    return "Please tell me the city to search for hotels."
                return _human_readable(search_hotels(city))
            if "flight" in lower:
                route = _extract_route(prompt)
                origin = route.get("origin") or "Hyderabad"
                destination = route.get("destination")
                if not destination:
                    return "Please tell me your flight destination."
                return _human_readable(search_flights(origin, destination))
            if "weather" in lower:
                city = _extract_route(prompt).get("destination") or _extract_city(prompt)
                if not city:
                    return "Please tell me the city for weather information."
                return _human_readable(get_weather_forecast(city))
            if "place" in lower or "attraction" in lower or "sight" in lower:
                city = _extract_route(prompt).get("destination") or _extract_city(prompt)
                if not city:
                    return "Please tell me the city to search for places."
                return _human_readable(search_places(city))
            return "LangChain is not available. Please install langchain and langchain-core, or ask a direct travel planning question."
