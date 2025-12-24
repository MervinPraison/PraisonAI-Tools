"""Weather Tool for PraisonAI Agents.

Get current weather, forecasts, and air quality data.

Usage:
    from praisonai_tools import WeatherTool
    
    weather = WeatherTool()  # Uses OPENWEATHER_API_KEY env var
    
    # Get current weather
    result = weather.get_current("London")
    
    # Get forecast
    forecast = weather.get_forecast("New York", days=5)

Environment Variables:
    OPENWEATHER_API_KEY: OpenWeatherMap API key (free tier available)
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WeatherTool(BaseTool):
    """Tool for getting weather information."""
    
    name = "weather"
    description = "Get current weather, forecasts, and air quality for any location."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        units: str = "metric",
    ):
        """Initialize WeatherTool.
        
        Args:
            api_key: OpenWeatherMap API key (or use OPENWEATHER_API_KEY env var)
            units: Temperature units - "metric" (Celsius), "imperial" (Fahrenheit), "standard" (Kelvin)
        """
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        self.units = units
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.geo_url = "https://api.openweathermap.org/geo/1.0"
        super().__init__()
    
    def _request(self, url: str, params: Dict) -> Dict:
        """Make API request."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}
        
        try:
            params["appid"] = self.api_key
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {"error": str(e)}
    
    def _geocode(self, location: str) -> Optional[Dict]:
        """Convert location name to coordinates."""
        if not self.api_key:
            return None
        url = f"{self.geo_url}/direct"
        result = self._request(url, {"q": location, "limit": 1})
        if isinstance(result, list) and result:
            return {"lat": result[0]["lat"], "lon": result[0]["lon"], "name": result[0].get("name", location)}
        return None
    
    def run(
        self,
        action: str = "current",
        location: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute weather action.
        
        Args:
            action: "current", "forecast", "air_quality"
            location: City name (e.g., "London", "New York, US")
            lat: Latitude (alternative to location)
            lon: Longitude (alternative to location)
            days: Forecast days (for forecast action)
        """
        if not self.api_key:
            return {"error": "OPENWEATHER_API_KEY not configured"}
        
        action = action.lower()
        if action == "current":
            return self.get_current(location=location, lat=lat, lon=lon)
        elif action == "forecast":
            return self.get_forecast(location=location, lat=lat, lon=lon, days=days)
        elif action in ("air", "air_quality", "pollution"):
            return self.get_air_quality(location=location, lat=lat, lon=lon)
        else:
            return {"error": f"Unknown action: {action}. Use 'current', 'forecast', or 'air_quality'."}
    
    def get_current(
        self,
        location: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get current weather for a location.
        
        Args:
            location: City name
            lat: Latitude
            lon: Longitude
            
        Returns:
            Current weather data
        """
        if not self.api_key:
            return {"error": "OPENWEATHER_API_KEY not configured"}
        
        # Get coordinates
        if lat is None or lon is None:
            if not location:
                return {"error": "Location or coordinates required"}
            geo = self._geocode(location)
            if not geo:
                return {"error": f"Could not find location: {location}"}
            lat, lon = geo["lat"], geo["lon"]
            location = geo["name"]
        
        url = f"{self.base_url}/weather"
        params = {"lat": lat, "lon": lon, "units": self.units}
        result = self._request(url, params)
        
        if "error" in result:
            return result
        
        # Format response
        temp_unit = "°C" if self.units == "metric" else "°F" if self.units == "imperial" else "K"
        speed_unit = "m/s" if self.units == "metric" else "mph" if self.units == "imperial" else "m/s"
        
        return {
            "location": result.get("name", location),
            "country": result.get("sys", {}).get("country", ""),
            "temperature": f"{result['main']['temp']}{temp_unit}",
            "feels_like": f"{result['main']['feels_like']}{temp_unit}",
            "humidity": f"{result['main']['humidity']}%",
            "pressure": f"{result['main']['pressure']} hPa",
            "wind_speed": f"{result['wind']['speed']} {speed_unit}",
            "description": result["weather"][0]["description"] if result.get("weather") else "",
            "icon": result["weather"][0]["icon"] if result.get("weather") else "",
            "visibility": f"{result.get('visibility', 0) / 1000} km",
            "clouds": f"{result.get('clouds', {}).get('all', 0)}%",
        }
    
    def get_forecast(
        self,
        location: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5,
    ) -> Dict[str, Any]:
        """Get weather forecast.
        
        Args:
            location: City name
            lat: Latitude
            lon: Longitude
            days: Number of days (max 5 for free tier)
            
        Returns:
            Forecast data
        """
        if not self.api_key:
            return {"error": "OPENWEATHER_API_KEY not configured"}
        
        if lat is None or lon is None:
            if not location:
                return {"error": "Location or coordinates required"}
            geo = self._geocode(location)
            if not geo:
                return {"error": f"Could not find location: {location}"}
            lat, lon = geo["lat"], geo["lon"]
            location = geo["name"]
        
        url = f"{self.base_url}/forecast"
        params = {"lat": lat, "lon": lon, "units": self.units, "cnt": min(days * 8, 40)}
        result = self._request(url, params)
        
        if "error" in result:
            return result
        
        temp_unit = "°C" if self.units == "metric" else "°F" if self.units == "imperial" else "K"
        
        forecasts = []
        for item in result.get("list", []):
            forecasts.append({
                "datetime": item["dt_txt"],
                "temperature": f"{item['main']['temp']}{temp_unit}",
                "feels_like": f"{item['main']['feels_like']}{temp_unit}",
                "humidity": f"{item['main']['humidity']}%",
                "description": item["weather"][0]["description"] if item.get("weather") else "",
                "wind_speed": item["wind"]["speed"],
                "rain_chance": item.get("pop", 0) * 100,
            })
        
        return {
            "location": result.get("city", {}).get("name", location),
            "country": result.get("city", {}).get("country", ""),
            "forecasts": forecasts,
        }
    
    def get_air_quality(
        self,
        location: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get air quality/pollution data.
        
        Args:
            location: City name
            lat: Latitude
            lon: Longitude
            
        Returns:
            Air quality data
        """
        if not self.api_key:
            return {"error": "OPENWEATHER_API_KEY not configured"}
        
        if lat is None or lon is None:
            if not location:
                return {"error": "Location or coordinates required"}
            geo = self._geocode(location)
            if not geo:
                return {"error": f"Could not find location: {location}"}
            lat, lon = geo["lat"], geo["lon"]
            location = geo["name"]
        
        url = f"{self.base_url}/air_pollution"
        params = {"lat": lat, "lon": lon}
        result = self._request(url, params)
        
        if "error" in result:
            return result
        
        if not result.get("list"):
            return {"error": "No air quality data available"}
        
        data = result["list"][0]
        aqi = data["main"]["aqi"]
        aqi_labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
        
        return {
            "location": location,
            "aqi": aqi,
            "aqi_label": aqi_labels.get(aqi, "Unknown"),
            "components": {
                "co": f"{data['components'].get('co', 0)} μg/m³",
                "no2": f"{data['components'].get('no2', 0)} μg/m³",
                "o3": f"{data['components'].get('o3', 0)} μg/m³",
                "pm2_5": f"{data['components'].get('pm2_5', 0)} μg/m³",
                "pm10": f"{data['components'].get('pm10', 0)} μg/m³",
            },
        }


def get_weather(location: str, units: str = "metric") -> Dict[str, Any]:
    """Get current weather for a location."""
    return WeatherTool(units=units).get_current(location=location)


def get_forecast(location: str, days: int = 5, units: str = "metric") -> Dict[str, Any]:
    """Get weather forecast for a location."""
    return WeatherTool(units=units).get_forecast(location=location, days=days)


def get_air_quality(location: str) -> Dict[str, Any]:
    """Get air quality for a location."""
    return WeatherTool().get_air_quality(location=location)
