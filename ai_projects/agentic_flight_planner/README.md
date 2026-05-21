# Agentic Flight Planner & Multi-Agent Coordinator

An autonomous coordinate-based drone flight planning system structured using collaborative AI agents. 

This project simulates a team of drone avionics and mission-planning agents coordinating to validate flight requests against real-world restrictions, showcasing:
- **System Prompts and Personas**: Defining operational boundaries for multiple agents.
- **Collaborative Consensus**: Combining reports from multiple experts (`AeroWeather`, `AeroSafety`) to approve or deny takeoff.
- **Tool Calling**: Binding real-world check APIs (Weather, Airspace restrictions, Battery constraints) into the agents' execution loops.

## System Architecture
```
                   [ User Request ]
                          │
                          ▼
                  ┌──────────────┐
                  │ AeroPlanner  │ (Primary Coordinator)
                  └──────┬───────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
┌──────────────┐                  ┌──────────────┐
│ AeroWeather  │                  │  AeroSafety  │
└──────┬───────┘                  └──────┬───────┘
       │                                 │
  (Checks API)                      (Checks API)
       │                                 │
       └────────────────┬────────────────┘
                        │
                        ▼
               [ Consensus Engine ]
                        │
                        ▼
               [ Final Flight Plan ]
```

## Running the Project
Execute `python agents.py` to run the coordinate checking simulation, which outputs the decision logs and JSON schemas of the agents.
