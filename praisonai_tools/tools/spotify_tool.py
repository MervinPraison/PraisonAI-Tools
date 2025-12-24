"""Spotify Tool for PraisonAI Agents.

Search and manage Spotify music.

Usage:
    from praisonai_tools import SpotifyTool
    
    spotify = SpotifyTool()
    tracks = spotify.search("Beatles")

Environment Variables:
    SPOTIFY_CLIENT_ID: Spotify API client ID
    SPOTIFY_CLIENT_SECRET: Spotify API client secret
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SpotifyTool(BaseTool):
    """Tool for Spotify music search."""
    
    name = "spotify"
    description = "Search tracks, artists, and playlists on Spotify."
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials
            except ImportError:
                raise ImportError("spotipy not installed. Install with: pip install spotipy")
            
            if not self.client_id or not self.client_secret:
                raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET required")
            
            self._client = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
            )
        return self._client
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        track_id: Optional[str] = None,
        artist_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, limit=limit)
        elif action == "search_artists":
            return self.search_artists(query=query, limit=limit)
        elif action == "get_track":
            return self.get_track(track_id=track_id)
        elif action == "get_artist":
            return self.get_artist(artist_id=artist_id)
        elif action == "get_artist_top_tracks":
            return self.get_artist_top_tracks(artist_id=artist_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search tracks."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            results = self.client.search(q=query, type="track", limit=limit)
            tracks = []
            for track in results.get("tracks", {}).get("items", []):
                tracks.append({
                    "id": track["id"],
                    "name": track["name"],
                    "artist": track["artists"][0]["name"] if track["artists"] else None,
                    "album": track["album"]["name"],
                    "duration_ms": track["duration_ms"],
                    "url": track["external_urls"].get("spotify"),
                })
            return tracks
        except Exception as e:
            logger.error(f"Spotify search error: {e}")
            return [{"error": str(e)}]
    
    def search_artists(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search artists."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            results = self.client.search(q=query, type="artist", limit=limit)
            artists = []
            for artist in results.get("artists", {}).get("items", []):
                artists.append({
                    "id": artist["id"],
                    "name": artist["name"],
                    "genres": artist.get("genres", []),
                    "followers": artist.get("followers", {}).get("total"),
                    "url": artist["external_urls"].get("spotify"),
                })
            return artists
        except Exception as e:
            logger.error(f"Spotify search_artists error: {e}")
            return [{"error": str(e)}]
    
    def get_track(self, track_id: str) -> Dict[str, Any]:
        """Get track details."""
        if not track_id:
            return {"error": "track_id is required"}
        
        try:
            track = self.client.track(track_id)
            return {
                "id": track["id"],
                "name": track["name"],
                "artist": track["artists"][0]["name"] if track["artists"] else None,
                "album": track["album"]["name"],
                "duration_ms": track["duration_ms"],
                "popularity": track["popularity"],
                "url": track["external_urls"].get("spotify"),
            }
        except Exception as e:
            logger.error(f"Spotify get_track error: {e}")
            return {"error": str(e)}
    
    def get_artist(self, artist_id: str) -> Dict[str, Any]:
        """Get artist details."""
        if not artist_id:
            return {"error": "artist_id is required"}
        
        try:
            artist = self.client.artist(artist_id)
            return {
                "id": artist["id"],
                "name": artist["name"],
                "genres": artist.get("genres", []),
                "followers": artist.get("followers", {}).get("total"),
                "popularity": artist["popularity"],
                "url": artist["external_urls"].get("spotify"),
            }
        except Exception as e:
            logger.error(f"Spotify get_artist error: {e}")
            return {"error": str(e)}
    
    def get_artist_top_tracks(self, artist_id: str, country: str = "US") -> List[Dict[str, Any]]:
        """Get artist's top tracks."""
        if not artist_id:
            return [{"error": "artist_id is required"}]
        
        try:
            results = self.client.artist_top_tracks(artist_id, country=country)
            tracks = []
            for track in results.get("tracks", []):
                tracks.append({
                    "id": track["id"],
                    "name": track["name"],
                    "album": track["album"]["name"],
                    "popularity": track["popularity"],
                })
            return tracks
        except Exception as e:
            logger.error(f"Spotify get_artist_top_tracks error: {e}")
            return [{"error": str(e)}]


def spotify_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search Spotify tracks."""
    return SpotifyTool().search(query=query, limit=limit)
