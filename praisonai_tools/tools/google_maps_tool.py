"""Google Maps Tool for PraisonAI Agents.

Geocoding, places, and directions using Google Maps API.

Usage:
    from praisonai_tools import GoogleMapsTool
    
    maps = GoogleMapsTool()
    location = maps.geocode("1600 Amphitheatre Parkway, Mountain View, CA")

Environment Variables:
    GOOGLE_MAPS_API_KEY: Google Maps API key
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GoogleMapsTool(BaseTool):
    """Tool for Google Maps operations."""
    
    name = "google_maps"
    description = "Geocode addresses, search places, and get directions."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import googlemaps
            except ImportError:
                raise ImportError("googlemaps not installed. Install with: pip install googlemaps")
            
            if not self.api_key:
                raise ValueError("GOOGLE_MAPS_API_KEY required")
            
            self._client = googlemaps.Client(key=self.api_key)
        return self._client
    
    def run(
        self,
        action: str = "geocode",
        address: Optional[str] = None,
        place_id: Optional[str] = None,
        query: Optional[str] = None,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "geocode":
            return self.geocode(address=address)
        elif action == "reverse_geocode":
            return self.reverse_geocode(lat=kwargs.get("lat"), lng=kwargs.get("lng"))
        elif action == "search_places":
            return self.search_places(query=query, **kwargs)
        elif action == "place_details":
            return self.place_details(place_id=place_id)
        elif action == "directions":
            return self.directions(origin=origin, destination=destination, **kwargs)
        elif action == "distance":
            return self.distance(origin=origin, destination=destination)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def geocode(self, address: str) -> Dict[str, Any]:
        """Geocode an address."""
        if not address:
            return {"error": "address is required"}
        
        try:
            results = self.client.geocode(address)
            if not results:
                return {"error": "No results found"}
            
            result = results[0]
            return {
                "formatted_address": result.get("formatted_address"),
                "lat": result["geometry"]["location"]["lat"],
                "lng": result["geometry"]["location"]["lng"],
                "place_id": result.get("place_id"),
            }
        except Exception as e:
            logger.error(f"Google Maps geocode error: {e}")
            return {"error": str(e)}
    
    def reverse_geocode(self, lat: float, lng: float) -> Dict[str, Any]:
        """Reverse geocode coordinates."""
        if lat is None or lng is None:
            return {"error": "lat and lng are required"}
        
        try:
            results = self.client.reverse_geocode((lat, lng))
            if not results:
                return {"error": "No results found"}
            
            result = results[0]
            return {
                "formatted_address": result.get("formatted_address"),
                "place_id": result.get("place_id"),
            }
        except Exception as e:
            logger.error(f"Google Maps reverse_geocode error: {e}")
            return {"error": str(e)}
    
    def search_places(self, query: str, location: Optional[str] = None, radius: int = 5000) -> List[Dict[str, Any]]:
        """Search for places."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            params = {"query": query}
            if location:
                geo = self.geocode(location)
                if "error" not in geo:
                    params["location"] = (geo["lat"], geo["lng"])
                    params["radius"] = radius
            
            results = self.client.places(**params)
            
            places = []
            for place in results.get("results", [])[:10]:
                places.append({
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "place_id": place.get("place_id"),
                    "rating": place.get("rating"),
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                })
            return places
        except Exception as e:
            logger.error(f"Google Maps search_places error: {e}")
            return [{"error": str(e)}]
    
    def place_details(self, place_id: str) -> Dict[str, Any]:
        """Get place details."""
        if not place_id:
            return {"error": "place_id is required"}
        
        try:
            result = self.client.place(place_id)
            place = result.get("result", {})
            
            return {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "phone": place.get("formatted_phone_number"),
                "website": place.get("website"),
                "rating": place.get("rating"),
                "reviews": place.get("user_ratings_total"),
                "hours": place.get("opening_hours", {}).get("weekday_text"),
            }
        except Exception as e:
            logger.error(f"Google Maps place_details error: {e}")
            return {"error": str(e)}
    
    def directions(self, origin: str, destination: str, mode: str = "driving") -> Dict[str, Any]:
        """Get directions."""
        if not origin or not destination:
            return {"error": "origin and destination are required"}
        
        try:
            results = self.client.directions(origin, destination, mode=mode)
            if not results:
                return {"error": "No route found"}
            
            route = results[0]
            leg = route["legs"][0]
            
            return {
                "distance": leg["distance"]["text"],
                "duration": leg["duration"]["text"],
                "start_address": leg["start_address"],
                "end_address": leg["end_address"],
                "steps": [s["html_instructions"] for s in leg["steps"][:10]],
            }
        except Exception as e:
            logger.error(f"Google Maps directions error: {e}")
            return {"error": str(e)}
    
    def distance(self, origin: str, destination: str) -> Dict[str, Any]:
        """Get distance between two points."""
        if not origin or not destination:
            return {"error": "origin and destination are required"}
        
        try:
            result = self.client.distance_matrix(origin, destination)
            element = result["rows"][0]["elements"][0]
            
            if element["status"] != "OK":
                return {"error": element["status"]}
            
            return {
                "distance": element["distance"]["text"],
                "duration": element["duration"]["text"],
            }
        except Exception as e:
            logger.error(f"Google Maps distance error: {e}")
            return {"error": str(e)}


def geocode_address(address: str) -> Dict[str, Any]:
    """Geocode address."""
    return GoogleMapsTool().geocode(address=address)
