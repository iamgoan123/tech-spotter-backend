# File: main.py
# This is the upgraded version with advanced detection logic.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import re

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
    This function takes HTML content and looks for technology clues,
    extracting specific IDs where possible.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # We'll store our findings here. The values will be lists of strings.
    detected = {
        "google_tags": [],
        "frameworks": [],
        "web_technologies": [],
        "compliance": [] 
    }

    # --- NEW & IMPROVED DETECTION LOGIC ---

    # 1. Find all Google-related IDs (GA4, GTM, Ads, etc.)
    # This pattern looks for G-, AW-, DC-, and GTM- prefixes.
    google_ids = re.findall(r'(G-[A-Z0-9]{10}|UA-[0-9]{4,9}-[0-9]{1,4}|GTM-[A-Z0-9]{7}|AW-[0-9]{9}|DC-[0-9]{7})', html_content)
    # Add unique IDs to our results
    if google_ids:
        detected["google_tags"].extend(list(set(google_ids))) # set() removes duplicates

    # 2. Check for dataLayer
    if "dataLayer = [" in html_content or "window.dataLayer = window.dataLayer || []" in html_content:
        detected["google_tags"].append("dataLayer Detected")

    # 3. Next.js Framework
    if soup.find('script', id='__NEXT_DATA__'):
        detected["frameworks"].append("Next.js")

    # 4. React Framework (as a fallback)
    # We check if Next.js wasn't found, as Next.js is built on React.
    if "Next.js" not in detected["frameworks"] and (soup.find(id='root') or soup.find('script', src=re.compile(r'react-dom'))):
         detected["frameworks"].append("React")

    # 5. Webpack (simple check)
    if "webpack" in html_content:
        detected["web_technologies"].append("Webpack")
        
    # 6. OneTrust (Compliance)
    if "cdn.cookielaw.org" in html_content:
        detected["compliance"].append("OneTrust CMP")

    return detected


@app.post("/analyze")
async def analyze_url(payload: URLPayload):
    target_url = payload.url
    
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    try:
        async with httpx.AsyncClient() as client:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await client.get(target_url, headers=headers, follow_redirects=True, timeout=15.0)
            
            if response.status_code == 200:
                html = response.text
                detected_technologies = analyze_html(html)
                
                # Add a new category for server-side tech
                detected_technologies["server_info"] = []

                if 'strict-transport-security' in response.headers:
                    detected_technologies["server_info"].append("HSTS Enabled")
                
                # Check for CDN headers
                server_header = response.headers.get('server', '').lower()
                if 'akamai' in server_header:
                    detected_technologies["server_info"].append("Akamai CDN")

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
