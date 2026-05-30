import argparse
import importlib.util
import json
import os

from agent import TravelAgent

_tools_path = os.path.join(os.path.dirname(__file__), "tools.py")
_spec = importlib.util.spec_from_file_location("root_tools", _tools_path)
_tools = importlib.util.module_from_spec(_spec)
if _spec and _spec.loader:
    _spec.loader.exec_module(_tools)

format_trip_summary = _tools.format_trip_summary
plan_trip = _tools.plan_trip

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Travel Planning Assistant.")
    parser.add_argument("--origin", default=None, help="Origin city for the trip.")
    parser.add_argument("--destination", default=None, help="Destination city for the trip.")
    parser.add_argument("--days", type=int, default=None, help="Number of days for the trip.")
    parser.add_argument("--prompt", default=None, help="Optional natural language prompt for the travel agent.")
    args = parser.parse_args()

    origin = args.origin
    if not origin:
        origin = input("Where are you starting your trip from (default Hyderabad)? ").strip()
        if not origin:
            origin = "Hyderabad"

    destination = args.destination
    if not destination:
        print("Available destinations:")
        for city in KNOWN_CITIES:
            print(f"- {city}")
        destination = input("Where is your next trip? ").strip()
        while not destination:
            destination = input("Please enter a destination city: ").strip()

    days = args.days if args.days is not None else 3
    if args.days is None:
        try:
            entered_days = input("Enter number of days (default 3): ").strip()
            if entered_days:
                days = max(1, int(entered_days))
        except ValueError:
            days = 3

    prompt = args.prompt or f"Plan a {days}-day trip from {origin} to {destination}."

    print("=== Direct Trip Plan ===")
    plan = plan_trip(destination, days, origin=origin)
    print(format_trip_summary(plan))

    print("\n=== LangChain Agent Response ===")
    agent = TravelAgent()
    agent_output = agent.run(prompt)
    print(agent_output)


if __name__ == "__main__":
    main()
