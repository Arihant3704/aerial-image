import json
from typing import List, Dict, Any
from tools import get_weather_forecast, check_airspace_restrictions, calculate_route_distance

class Agent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

    def run(self, context: str) -> str:
        """
        In a production system, this sends the system prompt and context to an LLM.
        For local testing/demonstration, we use a structured execution loop that
        simulates LLM reasoning using clear rule-based logic to respond to inputs.
        """
        raise NotImplementedError("Each specific agent type must implement run().")

class WeatherAnalystAgent(Agent):
    def __init__(self):
        super().__init__(
            name="AeroWeather",
            role="Weather Advisory Agent",
            system_prompt=(
                "You are an aviation weather specialist. Your job is to analyze coordinate-based "
                "weather telemetry, determine if winds and visibility are within safe thresholds for drone flight, "
                "and issue formal GO/NO-GO clearance based on weather conditions."
            )
        )

    def analyze(self, lat: float, lng: float) -> Dict[str, Any]:
        weather_data = get_weather_forecast(lat, lng)
        condition = weather_data["condition"]
        wind = weather_data["wind_speed_knots"]
        visibility = weather_data["visibility_miles"]
        
        # Safety criteria
        is_safe = True
        reason = "Weather is within operational parameters."
        
        if wind > 25.0:
            is_safe = False
            reason = f"Wind speed ({wind} knots) exceeds the safe operational limit of 25 knots."
        elif visibility < 1.0:
            is_safe = False
            reason = f"Visibility ({visibility} miles) is below minimum visual line of sight requirement of 1.0 mile."
        elif condition in ["Heavy Rain", "Foggy"]:
            is_safe = False
            reason = f"Adverse weather condition detected: {condition}."

        return {
            "agent": self.name,
            "status": "GO" if is_safe else "NO-GO",
            "weather_report": weather_data,
            "analysis": reason
        }

class SafetyOfficerAgent(Agent):
    def __init__(self):
        super().__init__(
            name="AeroSafety",
            role="Airspace and Hazard Safety Officer",
            system_prompt=(
                "You are a drone safety auditor. Your objective is to check coordinates against "
                "no-fly zones, military corridors, and airport airspace restrictions. You must issue "
                "a NO-GO status if any coordinate overlaps with restricted airspace."
            )
        )

    def audit(self, waypoints: List[tuple]) -> Dict[str, Any]:
        violations = []
        max_altitude = 400
        
        for wp in waypoints:
            lat, lng = wp
            check = check_airspace_restrictions(lat, lng)
            if check["restricted"]:
                violations.append(f"Waypoint ({lat:.4f}, {lng:.4f}) is restricted: {check['reason']}")
                max_altitude = 0
            else:
                max_altitude = min(max_altitude, check["max_allowed_altitude_ft"])

        is_safe = len(violations) == 0
        return {
            "agent": self.name,
            "status": "GO" if is_safe else "NO-GO",
            "max_altitude_allowed_ft": max_altitude,
            "violations": violations,
            "analysis": "Airspace cleared." if is_safe else f"Airspace violation(s) detected: {'; '.join(violations)}"
        }

class FlightPlannerAgent(Agent):
    def __init__(self):
        super().__init__(
            name="AeroPlanner",
            role="Flight Route Optimizer",
            system_prompt=(
                "You are an autonomous drone pilot. Your job is to take a request, plan coordinates, "
                "collaborate with the Weather and Safety agents, and assemble the final mission itinerary."
            )
        )

    def plan_mission(self, request_desc: str, waypoints: List[tuple]) -> Dict[str, Any]:
        print(f"[Flight Planner] Planning mission: '{request_desc}'")
        
        # Step 1: Check route metrics
        distance = calculate_route_distance(waypoints)
        estimated_battery_draw_percent = distance * 2.5 # ~2.5% battery per mile
        
        # Step 2: Trigger Weather Agent
        weather_agent = WeatherAnalystAgent()
        weather_decisions = []
        weather_ok = True
        
        for wp in waypoints:
            w_analysis = weather_agent.analyze(wp[0], wp[1])
            weather_decisions.append(w_analysis)
            if w_analysis["status"] == "NO-GO":
                weather_ok = False

        # Step 3: Trigger Safety Agent
        safety_agent = SafetyOfficerAgent()
        safety_analysis = safety_agent.audit(waypoints)
        safety_ok = safety_analysis["status"] == "GO"
        
        # Step 4: Final Assessment
        overall_status = "APPROVED" if (weather_ok and safety_ok and estimated_battery_draw_percent < 80.0) else "REJECTED"
        rejections = []
        if not weather_ok:
            rejections.append("Weather safety constraints violated.")
        if not safety_ok:
            rejections.append("Airspace restrictions violated.")
        if estimated_battery_draw_percent >= 80.0:
            rejections.append(f"Estimated battery usage ({estimated_battery_draw_percent:.1f}%) exceeds safety margins.")

        reason = "Mission approved for takeoff." if overall_status == "APPROVED" else f"Takeoff denied: {', '.join(rejections)}"

        return {
            "mission_name": request_desc,
            "status": overall_status,
            "route_details": {
                "number_of_waypoints": len(waypoints),
                "total_distance_nm": round(distance, 2),
                "estimated_battery_draw_percent": round(estimated_battery_draw_percent, 1)
            },
            "weather_clearance": "GO" if weather_ok else "NO-GO",
            "safety_clearance": "GO" if safety_ok else "NO-GO",
            "safety_details": safety_analysis,
            "weather_details": weather_decisions,
            "overall_assessment": reason
        }

if __name__ == "__main__":
    # Test cases
    planner = FlightPlannerAgent()
    
    # 1. Safe Mission
    print("\n--- Test Case 1: Safe Agricultural Mission ---")
    safe_waypoints = [(15.3644, 75.1244), (15.3685, 75.1299)]
    plan_1 = planner.plan_mission("Agricultural Mapping Phase 1", safe_waypoints)
    print(json.dumps(plan_1, indent=2))
    
    # 2. Unsafe Airspace Mission
    print("\n--- Test Case 2: Mission crossing Airbase / Restricted area ---")
    unsafe_waypoints = [(15.3644, 75.1244), (15.0001, 75.0002)] # Will trigger restriction
    plan_2 = planner.plan_mission("Industrial scouting near airfield", unsafe_waypoints)
    print(json.dumps(plan_2, indent=2))
