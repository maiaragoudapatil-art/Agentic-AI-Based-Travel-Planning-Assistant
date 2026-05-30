# Agentic AI-Based Travel Planning Assistant Using LangChain

This project is a complete, modular **Agentic AI-Based Travel Planning Assistant** that autonomously plans trip itineraries. It is implemented using **LangChain** and **Streamlit** in Python.

The assistant combines a conversational ReAct agent with custom tools to query mock databases and fetch real-time weather from the **Open-Meteo API** to formulate optimized, budget-aware day-by-day travel schedules.

---

## 🌟 Core Features

- **Multi-LLM Integration**: Works with both **Google Gemini** (via `ChatGoogleGenerativeAI`) and **OpenAI** (via `ChatOpenAI`).
- **Optimal Flight Search**: Reads `flights.json`, filters by origin/destination/budget, and sorts to find the **cheapest** flight.
- **Top-Tier Hotel Recommendations**: Reads `hotels.json` and filters by destination, sorting by **rating descending** (highest rated) and then **price ascending** (best value).
- **Points of Interest Discovery**: Reads `places.json` to find tourist hotspots, ranking them by rating to design the perfect tour.
- **Real-time Weather Integration**: Calls the free, API-key-less **Open-Meteo API** to dynamically geocode coordinates and fetch current daily weather conditions.
- **Interactive Agent Logs**: Streams the agent's step-by-step tool invocations and intermediate thoughts directly on screen in the Streamlit UI.
- **Premium Design Layout**: Fully loaded with rich visual aesthetics, custom styles, metrics cards, and interactive sliders.

---

## 📁 Project Structure

```text
Agentic AI-Based Travel Planning Assistant/
│
├── data/                     # Optional folder (automatically resolves files in workspace root too)
│   ├── flights.json          # Mock flights (from, to, departure_time, arrival_time, price)
│   ├── hotels.json           # Mock hotels (name, city, stars, price_per_night, amenities)
│   └── places.json           # Mock places/attractions (name, city, type, rating)
│
├── tools/                    # Custom LangChain Tools Package
│   ├── __init__.py           # Exports all tools in an registry list
│   ├── flight_tool.py        # Flight search tool matching "from", "to", and "price"
│   ├── hotel_tool.py         # Hotel search tool filtering by city, stars, and price
│   ├── places_tool.py        # Places discovery tool returning attractions by city sorted by rating
│   └── weather_tool.py       # Weather tool fetching real-time data from Open-Meteo API
│
├── agent.py                  # LangChain agent orchestrator (loads LLM and ReAct agent)
├── app.py                    # Sleek Streamlit Web Application interface
├── main.py                   # CLI-based alternative entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template for LLM provider and API keys
└── README.md                 # Project documentation and setup guide
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Install Dependencies
Run the following command in your terminal/command prompt to install all required packages:
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
1. Copy the `.env.example` file and rename it to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and configure your preferred provider (`google` or `openai`) and supply your API keys:
   - For Google Gemini: Set `LLM_PROVIDER=google` and paste your `GOOGLE_API_KEY` (available via Google AI Studio).
   - For OpenAI: Set `LLM_PROVIDER=openai` and paste your `OPENAI_API_KEY`.

---

## 💻 Running the Assistant

### Option A: Premium Web Interface (Recommended)
Launch the Streamlit web dashboard:
```bash
streamlit run app.py
```
This opens a beautiful visual dashboard in your default browser (usually at `http://localhost:8501`), where you can:
- Swap LLM providers and model versions on the fly in the sidebar.
- Set API keys securely via the interface.
- View the **interactive step-by-step thoughts of the AI agent** in real-time.
- View a gorgeous day-by-day itinerary summary.

### Option B: Terminal Command Line Interface
Run the CLI planner directly from your shell:
```bash
python main.py
```
Simply answer the prompts for departure, destination, days, and budget, and watch the agent output its complete plan.

---

## 🛠️ Verification & Testing
To confirm everything is working properly:
- Search flights from **Hyderabad** to **Delhi** (contained in `flights.json`).
- Search hotels in **Delhi** (contained in `hotels.json`).
- Make sure weather information is retrieved correctly via HTTP from Open-Meteo for Delhi.
- Observe the day-wise itinerary matching Delhi's famous attractions (from `places.json`).
