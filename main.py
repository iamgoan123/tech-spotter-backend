# File: main.py
# This version extracts specific IDs and has a richer data structure.

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

# --- FINGERPRINT LIBRARY V2 ---
# Now includes specific patterns for extracting IDs.
TECHNOLOGY_FINGERPRINTS = {
    "Analytics": [
        {"name": "Microsoft Clarity", "pattern": r'clarity.ms', "type": "presence"},
    ],
    "Google Tags": [
        {"name": "Google Analytics GA4", "pattern": r'G-[A-Z0-9]{10}', "type": "extract_all"},
        {"name": "Universal Analytics", "pattern": r'UA-[0-9]{4,9}-[0-9]{1,4}', "type": "extract_all"},
        {"name": "Google Tag Manager", "pattern": r'GTM-[A-Z0-9]{7}', "type": "extract_all"},
        {"name": "Google Ads", "pattern": r'AW-[0-9]{9}', "type": "extract_all"},
        {"name": "DoubleClick Floodlight", "pattern": r'DC-[0-9]{7}', "type": "extract_all"},
    ],
    "Advertising": [
        {"name": "Facebook Pixel", "pattern": r'connect.facebook.net', "type": "presence"},
        {"name": "LinkedIn Insight Tag", "pattern": r'snap.licdn.com/li.lms-analytics', "type": "presence"},
    ],
    "Frameworks": [
        {"name": "Next.js", "pattern": '__NEXT_DATA__', "type": "script_id"},
        {"name": "React", "pattern": 'root', "type": "div_id"},
    ],
    "JavaScript Libraries": [
        {"name": "jQuery", "pattern": r'jquery.js|jquery.min.js', "type": "presence"},
        {"name": "GSAP", "pattern": r'gsap.min.js', "type": "presence"},
    ],
    "Page Builders": [
        {"name": "Webflow", "pattern": 'data-wf-page', "type": "html_attribute"},
    ],
    "Miscellaneous": [
        {"name": "Webpack", "pattern": 'webpack', "type": "presence"},
        {"name": "dataLayer", "pattern": r'dataLayer\s*=\s*\[', "type": "presence"},
    ],
    "Security": [
        {"name": "HSTS", "pattern": 'strict-transport-security', "type": "header"},
    ],
    "CDN": [
        {"name": "Cloudflare", "pattern": 'cloudflare', "type": "server_header"},
    ]
}

def analyze_content(html_content, headers):
    detected = {}
    soup = BeautifulSoup(html_content, 'html.parser')

    for category, technologies in TECHNOLOGY_FINGERPRINTS.items():
        found_in_category = []
        for tech in technologies:
            name = tech["name"]
            pattern = tech["pattern"]
            tech_type = tech["type"]
            
            found = False
            details = []

            if tech_type == "presence":
                if re.search(pattern, html_content, re.IGNORECASE):
                    found = True
            elif tech_type == "extract_all":
                matches = re.findall(pattern, html_content)
                if matches:
                    found = True
                    details = list(set(matches)) # Use set to get unique IDs
            elif tech_type == "script_id":
                if soup.find('script', id=pattern):
                    found = True
            elif tech_type == "div_id":
                if soup.find(id=pattern) and "Next.js" not in [f["name"] for f in found_in_category]:
                    found = True
            elif tech_type == "html_attribute":
                if soup.find(attrs={pattern: True}):
                    found = True
            elif tech_type == "header":
                if pattern in headers:
                    found = True
            elif tech_type == "server_header":
                if pattern in headers.get('server', ''):
                    found = True
            
            if found:
                tech_result = {"name": name}
                if details:
                    tech_result["ids"] = details
                found_in_category.append(tech_result)
        
        if found_in_category:
            detected[category] = found_in_category
            
    return detected

@app.post("/analyze")
async def analyze_url(payload: URLPayload):
    target_url = payload.url
    
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    try:
        async with httpx.AsyncClient(verify=False) as client:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await client.get(target_url, headers=headers, follow_redirects=True, timeout=20.0)
            
            if response.status_code == 200:
                html = response.text
                response_headers = {k.lower(): v.lower() for k, v in response.headers.items()}
                detected_technologies = analyze_content(html, response_headers)
                return { "message": "Advanced analysis complete!", "detected_technologies": detected_technologies }
            else:
                return {"error": f"Could not fetch the URL. Status code: {response.status_code}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

@app.get("/")
def read_root():
    return {"message": "Tech Spotter API is running!"}
