import random
from typing import Dict, Any

def get_weather_forecast(lat: float, lng: float) -> Dict[str, Any]:
    """
    Simulates fetching real-time weather details for coordinate-based drone flight paths.
    """
    # Deterministic simulation based on coordinate seed
    seed_val = int((lat + lng) * 100) % 5
    conditions = ["Clear", "Partly Cloudy", "High Winds", "Heavy Rain", "Foggy"]
    wind_speeds = [5.2, 12.5, 28.4, 15.1, 4.0] # in knots
    visibilities = [10.0, 8.5, 3.2, 2.0, 0.5] # in miles
    
    return {
        "status": "success",
        "coordinate": {"lat": lat, "lng": lng},
        "condition": conditions[seed_val],
        "wind_speed_knots": wind_speeds[seed_val],
        "visibility_miles": visibilities[seed_val],
        "temperature_c": 22 + (seed_val * 2)
    }

def check_airspace_restrictions(lat: float, lng: float) -> Dict[str, Any]:
    """
    Checks if coordinates intersect with restricted zones or airports.
    """
    seed_val = int((lat + lng) * 1000) % 10
    
    # 0, 1, 2 represent restricted airspace
    if seed_val < 3:
        zones = ["Military Airbase Zone Alpha", "Airport Class B Airspace", "National Park Restricted Zone"]
        return {
            "restricted": True,
            "reason": f"Prohibited zone: {zones[seed_val]}",
            "max_allowed_altitude_ft": 0
        }
    
    return {
        "restricted": False,
        "reason": "Class G Uncontrolled Airspace - Drone operations permitted up to 400ft AGL",
        "max_allowed_altitude_ft": 400
    }

def calculate_route_distance(waypoints: list) -> float:
    """
    Calculates coordinate distance (simplified Euclidean distance).
    """
    if len(waypoints) < 2:
        return 0.0
        
    total_dist = 0.0
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i+1]
        dist = ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5
        # Convert degree approximation to nautical miles roughly
        total_dist += dist * 60.0
        
    return total_dist
