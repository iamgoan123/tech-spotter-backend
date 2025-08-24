# File: main.py
# A super-stable version for debugging the connection.
# This version IGNORES the website and ALWAYS returns a fake result.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class URLPayload(BaseModel):
    url: str

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_url(payload: URLPayload):
    """
    This function immediately returns a hardcoded successful result
    to test the server and connection health.
    """
    fake_results = {
        "Google Tags": [
            {
                "name": "Test: Google Tag Manager",
                "ids": ["GTM-TEST123"]
            },
            {
                "name": "Test: Google Analytics GA4",
                "ids": ["G-TEST456"]
            }
        ],
        "Frameworks": [
            {
                "name": "Test: React",
            }
        ]
    }
    
    return { 
        "message": "Backend connection is stable!", 
        "detected_technologies": fake_results 
    }

@app.get("/")
def read_root():
    return {"message": "Tech Spotter API (Stable Test Version) is running!"}
