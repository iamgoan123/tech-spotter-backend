# File: main.py
# This is the final version with real analysis logic.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup # We've added BeautifulSoup for parsing HTML
import re # We've added the regular expression module

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

def analyze_html(html_content: str):
    """
    This function takes HTML content and looks for technology clues.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    detected = {
        "analytics": [],
        "frameworks": [],
        "security": [],
        "compliance": [] 
    }

    # --- Detection Logic ---

    # 1. Google Analytics (GA4 and UA)
    if re.search(r'G-[A-Z0-9]{10}', html_content):
        detected["analytics"].append({"name": "Google Analytics 4", "detected": "Yes"})
    if re.search(r'UA-[0-9]{4,9}-[0-9]{1,4}', html_content):
        detected["analytics"].append({"name": "Universal Analytics", "detected": "Yes"})

    # 2. Google Tag Manager
    if "googletagmanager.com/gtm.js" in html_content:
        detected["analytics"].append({"name": "Google Tag Manager", "detected": "Yes"})

    # 3. React
    # A simple check for the common 'root' div or react scripts
    if soup.find(id='root') or soup.find('script', src=re.compile(r'react-dom')):
         detected["frameworks"].append({"name": "React", "detected": "Yes"})

    # 4. OneTrust (Compliance)
    if "cdn.cookielaw.org" in html_content:
        detected["compliance"].append({"name": "OneTrust CMP", "detected": "Yes"})

    return detected


@app.post("/analyze")
async def analyze_url(payload: URLPayload):
    target_url = payload.url
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await client.get(target_url, headers=headers, follow_redirects=True, timeout=15.0)
            
            if response.status_code == 200:
                # Now we pass the HTML to our new analysis function
                html = response.text
                detected_technologies = analyze_html(html)
                
                # Check for HSTS Header (Security)
                if 'strict-transport-security' in response.headers:
                    detected_technologies["security"].append({"name": "HSTS Enabled", "detected": "Yes"})

                return {
                    "message": "Analysis complete!",
                    "detected_technologies": detected_technologies
                }
            else:
                return {"error": f"Could not fetch the URL. Status code: {response.status_code}"}

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


@app.get("/")
def read_root():
    return {"message": "Tech Spotter API is running!"}
