# explore_tavily.py  (project root — delete after Day 1)
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

response = httpx.post(
    "https://api.tavily.com/search",
    json={
        "query": "What is the current population of Tokyo?",
        "max_results": 3,
    },
    headers={"Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}"},
    timeout=10.0,
)

print(json.dumps(response.json(), indent=2))