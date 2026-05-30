import json
import os
import re
from typing import Any, Dict, List, Optional

import requests

DEFAULT_ORIGIN = "Hyderabad"

CITY_COORDINATES = {
    "delhi": {"lat": 28.6139, "lon": 77.2090},
    "mumbai": {"lat": 19.0760, "lon": 72.8777},
    "goa": {"lat": 15.2993, "lon": 74.1240},
    "bangalore": {"lat": 12.9716, "lon": 77.5946},
    "chennai": {"lat": 13.0827, "lon": 80.2707},
    "hyderabad": {"lat": 17.3850, "lon": 78.4867},
    "kolkata": {"lat": 22.5726, "lon": 88.3639},
    "jaipur": {"lat": 26.9124, "lon": 75.7873}
}

WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail"
}

KNOWN_CITIES = list(CITY_COORDINATES.keys())


def find_data_file(filename: str) -> str:
    root = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        os.path.join(root, filename),
        os.path.join(root, "..", filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), "data", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    raise FileNotFoundError(f"Data file '{filename}' not found. Tried: {candidates}")


def load_json_data(filename: str) -> List[Dict[str, Any]]:
    path = find_data_file(filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value: str) -> str:
    return value.strip().lower()


def paginate_items(items: List[Any], limit: int = 3) -> List[Any]:
    return items[:limit]


def search_flights(origin: str, destination: str) -> Dict[str, Any]:
    origin_norm = normalize_text(origin)
    destination_norm = normalize_text(destination)
    flights = load_json_data("flights.json")

    direct_matches = [
        flight
        for flight in flights
        if normalize_text(flight.get("from", "")) == origin_norm
        and normalize_text(flight.get("to", "")) == destination_norm
    ]
    if direct_matches:
        direct_matches.sort(key=lambda flight: flight.get("price", float("inf")))
        return {"flight": direct_matches[0], "status": "success", "source": origin, "destination": destination}

    fallback_matches = [
        flight
        for flight in flights
        if normalize_text(flight.get("to", "")) == destination_norm
    ]
    if fallback_matches:
        fallback_matches.sort(key=lambda flight: flight.get("price", float("inf")))
        return {
            "flight": fallback_matches[0],
            "status": "fallback",
            "message": f"No direct flight from {origin}. Returning cheapest flight to {destination} from another city.",
        }

    return {
        "status": "not_found",
        "message": f"No flights found arriving in {destination} from {origin} or any other city.",
    }


def search_hotels(city: str) -> Dict[str, Any]:
    city_norm = normalize_text(city)
    hotels = load_json_data("hotels.json")
    matches = [hotel for hotel in hotels if normalize_text(hotel.get("city", "")) == city_norm]

    if not matches:
        return {"status": "not_found", "message": f"No hotels found in {city}."}

    matches.sort(key=lambda hotel: (-hotel.get("stars", 0), hotel.get("price_per_night", float("inf"))))
    return {"hotel": matches[0], "status": "success", "city": city}


def search_places(city: str) -> Dict[str, Any]:
    city_norm = normalize_text(city)
    places = load_json_data("places.json")
    matches = [place for place in places if normalize_text(place.get("city", "")) == city_norm]

    if not matches:
        return {"status": "not_found", "message": f"No places found for {city}."}

    matches.sort(key=lambda place: (-place.get("rating", 0.0), place.get("name", "")))
    return {"places": paginate_items(matches, limit=3), "status": "success", "city": city}


def get_city_coordinates(city: str) -> Dict[str, float]:
    city_norm = normalize_text(city)
    if city_norm in CITY_COORDINATES:
        return CITY_COORDINATES[city_norm]

    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    response = requests.get(geo_url, timeout=10)
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    if not results:
        raise ValueError(f"City '{city}' could not be geocoded.")
    return {"lat": results[0]["latitude"], "lon": results[0]["longitude"]}


def weather_code_description(code: int) -> str:
    return WEATHER_CODE_DESCRIPTIONS.get(code, "Mixed Weather")


def get_weather_forecast(city: str) -> Dict[str, Any]:
    try:
        coords = get_city_coordinates(city)
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}"
            "&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        codes = daily.get("weathercode", [])

        forecast = []
        for index, date in enumerate(dates):
            forecast.append(
                {
                    "date": date,
                    "max_temp": f"{highs[index]}°C" if index < len(highs) else "N/A",
                    "min_temp": f"{lows[index]}°C" if index < len(lows) else "N/A",
                    "condition": weather_code_description(codes[index] if index < len(codes) else 0),
                }
            )

        return {
            "city": city,
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "forecast": forecast,
            "status": "success",
        }
    except requests.RequestException as exc:
        return {"status": "error", "message": f"Weather API request failed: {exc}"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def plan_trip(destination: str, days: int, origin: Optional[str] = None) -> Dict[str, Any]:
    if origin is None:
        origin = DEFAULT_ORIGIN
    destination = destination.strip()
    days = max(1, int(days))

    flight_result = search_flights(origin, destination)
    hotel_result = search_hotels(destination)
    places_result = search_places(destination)
    weather_result = get_weather_forecast(destination)

    flight_price = flight_result.get("flight", {}).get("price", 0)
    hotel_price = hotel_result.get("hotel", {}).get("price_per_night", 0)

    total_cost = flight_price + hotel_price * days

    return {
        "destination": destination,
        "origin": origin,
        "days": days,
        "flight": flight_result,
        "hotel": hotel_result,
        "places": places_result,
        "weather": weather_result,
        "total_cost": total_cost,
    }


def _format_table(headers: List[str], rows: List[List[str]]) -> str:
    if not rows:
        return ""
    column_widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            column_widths[index] = max(column_widths[index], len(cell))

    separator = "+" + "+".join(["-" * (width + 2) for width in column_widths]) + "+"
    header_row = "|" + "|".join([f" {headers[i].ljust(column_widths[i])} " for i in range(len(headers))]) + "|"
    lines = [separator, header_row, separator]
    for row in rows:
        lines.append("|" + "|".join([f" {row[i].ljust(column_widths[i])} " for i in range(len(row))]) + "|")
    lines.append(separator)
    return "\n".join(lines)


def format_trip_summary(plan: Dict[str, Any]) -> str:
    destination = plan.get("destination", "N/A")
    origin = plan.get("origin", "N/A")
    days = str(plan.get("days", "N/A"))
    total_cost = str(plan.get("total_cost", "N/A"))

    flight = plan.get("flight", {})
    hotel = plan.get("hotel", {})
    places = plan.get("places", {})
    weather = plan.get("weather", {})

    lines = [
        "TRIP SUMMARY",
        _format_table(
            ["Field", "Value"],
            [["Origin", origin], ["Destination", destination], ["Days", days], ["Total Cost", total_cost]],
        ),
        "",
        "FLIGHT DETAILS",
    ]

    flight_row = []
    flight_info = flight.get("flight") if isinstance(flight, dict) else None
    if flight_info:
        flight_row = [
            str(flight_info.get("airline", "N/A")),
            str(flight_info.get("from", "N/A")),
            str(flight_info.get("to", "N/A")),
            str(flight_info.get("departure_time", "N/A")),
            str(flight_info.get("arrival_time", "N/A")),
            str(flight_info.get("price", "N/A")),
        ]
    else:
        flight_row = ["N/A"] * 6

    lines.append(
        _format_table(
            ["Airline", "From", "To", "Departure", "Arrival", "Price"],
            [flight_row],
        )
    )

    lines.extend(["", "HOTEL DETAILS"])
    hotel_info = hotel.get("hotel") if isinstance(hotel, dict) else None
    hotel_row = [
        str(hotel_info.get("name", "N/A")) if hotel_info else "N/A",
        str(hotel_info.get("city", "N/A")) if hotel_info else "N/A",
        str(hotel_info.get("stars", "N/A")) if hotel_info else "N/A",
        str(hotel_info.get("price_per_night", "N/A")) if hotel_info else "N/A",
        ", ".join(hotel_info.get("amenities", [])) if hotel_info else "N/A",
    ]
    lines.append(
        _format_table(
            ["Hotel", "City", "Stars", "Price/Night", "Amenities"],
            [hotel_row],
        )
    )

    lines.extend(["", "TOP PLACES"])
    place_rows = []
    if isinstance(places, dict) and isinstance(places.get("places"), list):
        for place in places["places"]:
            place_rows.append(
                [
                    str(place.get("name", "N/A")),
                    str(place.get("type", "N/A")),
                    str(place.get("rating", "N/A")),
                ]
            )
    if not place_rows:
        place_rows = [["No places found", "", ""]]
    lines.append(_format_table(["Name", "Type", "Rating"], place_rows))

    lines.extend(["", "WEATHER FORECAST"])
    weather_rows = []
    if isinstance(weather, dict) and isinstance(weather.get("forecast"), list):
        for day in weather["forecast"][:5]:
            weather_rows.append(
                [
                    str(day.get("date", "N/A")),
                    str(day.get("max_temp", "N/A")),
                    str(day.get("min_temp", "N/A")),
                    str(day.get("condition", "N/A")),
                ]
            )
    if not weather_rows:
        weather_rows = [["No forecast available", "", "", ""]]
    lines.append(_format_table(["Date", "High", "Low", "Condition"], weather_rows))

    return "\n".join(lines)
