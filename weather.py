from typing import Any, Optional, Dict
import httpx
import logging
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather")

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Make a request to the NWS API with proper error handling."""
    default_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    if headers:
        default_headers.update(headers)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=default_headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

def format_alert(props: Dict[str, Any]) -> str:
    """Format an alert feature into a readable string."""
    return (
        f"Event: {props.get('event', 'Unknown')}\n"
        f"Area: {props.get('areaDesc', 'Unknown')}\n"
        f"Severity: {props.get('severity', 'Unknown')}\n"
        f"Description: {props.get('description', 'No description available')}\n"
        f"Instructions: {props.get('instruction', 'No specific instructions provided')}\n"
    )

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    if not (isinstance(state, str) and len(state) == 2 and state.isalpha()):
        return "Invalid state code. Please provide a two-letter US state code."
    url = f"{NWS_API_BASE}/alerts/active/area/{state.upper()}"
    data = await make_nws_request(url)
    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    if not data["features"]:
        return "No active alerts for this state."
    alerts = [format_alert(feature["properties"]) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return "Invalid latitude or longitude."
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)
    if not points_data or "properties" not in points_data or "forecast" not in points_data["properties"]:
        return "Unable to fetch forecast data for this location."
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)
    if not forecast_data or "properties" not in forecast_data or "periods" not in forecast_data["properties"]:
        return "Unable to fetch detailed forecast."
    periods = forecast_data["properties"]["periods"]
    forecasts = [
        (
            f"{period['name']}:\n"
            f"Temperature: {period['temperature']}°{period['temperatureUnit']}\n"
            f"Wind: {period['windSpeed']} {period['windDirection']}\n"
            f"Forecast: {period['detailedForecast']}\n"
        )
        for period in periods[:5]
    ]
    return "\n---\n".join(forecasts)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')