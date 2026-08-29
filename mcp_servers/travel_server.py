import os
import time
from typing import Any, Dict, List
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("Tripster Travel Tools Server")

TOKEN_URL = os.getenv(
    "OPENSKY_TOKEN_URL",
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
)

class OpenSkyTokenManager:
    def __init__(self):
        self.access_token = None
        self.expires_at = 0.0

    def get_headers(self) -> Dict[str, str]:
        if not self.access_token or time.time() >= self.expires_at:
            self._refresh()
        return {"Authorization": f"Bearer {self.access_token}"}

    def _refresh(self) -> None:
        client_id = os.getenv("OPENSKY_CLIENT_ID")
        client_secret = os.getenv("OPENSKY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET are required")

        try:
            response = httpx.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPError as error:
            raise RuntimeError(f"OpenSky token request failed: {error}") from error

        self.access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 1800))
        self.expires_at = time.time() + max(expires_in - 30, 1)

    def clear(self) -> None:
        self.access_token = None
        self.expires_at = 0.0


opensky_tokens = OpenSkyTokenManager()

@mcp.tool()
def search_flights_tool(origin: str, destination: str, budget: float) -> List[Dict[str, Any]]:
    import random
    
    airline_data = [
        {"name": "Delta Air Lines", "code": "DL"},
        {"name": "United Airlines", "code": "UA"},
        {"name": "American Airlines", "code": "AA"},
        {"name": "Lufthansa", "code": "LH"},
        {"name": "Emirates", "code": "EK"},
        {"name": "Air India", "code": "AI"},
        {"name": "Singapore Airlines", "code": "SQ"},
        {"name": "All Nippon Airways", "code": "NH"}
    ]
    
    results = []
    selected_airlines = random.sample(airline_data, min(3, len(airline_data)))
    
    for item in selected_airlines:
        airline = item["name"]
        flight_num = f"{item['code']}{random.randint(100, 999)}"
        is_direct = random.choice([True, False])
        
        # Base price loosely based on budget (20% - 40% of total budget)
        base_price = budget * random.uniform(0.20, 0.40)
        if not is_direct:
            base_price *= 0.82
            
        duration_hours = random.uniform(3.5, 14.0) if not is_direct else random.uniform(2.0, 9.0)
        hours = int(duration_hours)
        minutes = int((duration_hours - hours) * 60)
        
        dep_hour = random.randint(6, 21)
        arr_hour = (dep_hour + hours) % 24
        departure_time = f"{dep_hour:02d}:{random.choice(['00', '15', '30', '45'])}"
        arrival_time = f"{arr_hour:02d}:{random.choice(['05', '20', '40', '50'])}"
        
        results.append({
            "airline": airline,
            "flight_number": flight_num,
            "origin": origin,
            "destination": destination,
            "price": round(base_price, 2),
            "duration": f"{hours}h {minutes}m",
            "departure": departure_time,
            "arrival": arrival_time,
            "is_direct": is_direct,
            "flight_status": "scheduled",
            "source": "MockFlight API",
            "requested_origin": origin,
            "requested_destination": destination,
        })
        
    results.sort(key=lambda x: x["price"])
    return results
