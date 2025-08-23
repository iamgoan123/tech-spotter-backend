# File 1: main.py
# This is the main file for our backend server.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx # A library for making web requests

# This defines the structure of the data we expect to receive
class URLPayload(BaseModel):
    url: str

# Initialize our FastAPI application
app = FastAPI()

# --- CORS Middleware ---
# This is a crucial security step. It allows your Vercel frontend
# to make requests to this backend, even though they are on different domains.
origins = [
    "*" # Allows all origins for simplicity. In production, you'd restrict this.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This is our main analysis endpoint.
@app.post("/analyze")
async def analyze_url(payload: URLPayload):
    """
    Receives a URL, fetches its content, and performs a basic analysis.
    """
    target_url = payload.url
    
    # --- This is where the real analysis logic will go ---
    # For now, we will just check if the site is reachable.
    
    try:
        async with httpx.AsyncClient() as client:
            # We use a common user-agent to look like a real browser
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await client.get(target_url, headers=headers, follow_redirects=True, timeout=10.0)
            
            # Check if the request was successful
            if response.status_code == 200:
                # In the future, we will analyze response.text (the HTML) here.
                # For now, we return a simple success message.
                return {
                    "message": f"Successfully reached {target_url}",
                    "status_code": response.status_code,
                    "detected_technologies": {
                        "analytics": [{"name": "Google Analytics", "detected": "Coming Soon!"}],
                        "frameworks": [{"name": "React", "detected": "Coming Soon!"}]
                    }
                }
            else:
                return {"error": f"Could not fetch the URL. Status code: {response.status_code}"}

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

# A simple root endpoint to confirm the server is running
@app.get("/")
def read_root():
    return {"message": "Tech Spotter API is running!"}
