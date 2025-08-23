# File: main.py
# The ultimate upgrade with a comprehensive detection library.

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

# --- COMPREHENSIVE FINGERPRINT LIBRARY ---
# We define patterns for various technologies.
TECHNOLOGY_FINGERPRINTS = {
    "Analytics": {
        "Google Analytics GA4": (r'G-[A-Z0-9]{10}', 'html'),
        "Universal Analytics": (r'UA-[0-9]{4,9}-[0-9]{1,4}', 'html'),
        "Microsoft Clarity": (r'clarity.ms', 'html'),
    },
    "Tag Managers": {
        "Google Tag Manager": (r'GTM-[A-Z0-9]{7}', 'html'),
    },
    "Advertising": {
        "Facebook Pixel": (r'connect.facebook.net', 'html'),
        "LinkedIn Insight Tag": (r'snap.licdn.com/li.lms-analytics', 'html'),
        "Quora Pixel": (r'qevents.js', 'html'),
        "Twitter Ads": (r'static.ads-twitter.com', 'html'),
        "DoubleClick Floodlight": (r'fls.doubleclick.net', 'html'),
    },
    "Frameworks": {
        "Next.js": ('__NEXT_DATA__', 'script_id'),
        "React": ('root', 'div_id'),
    },
    "JavaScript Libraries": {
        "jQuery": (r'jquery.js|jquery.min.js', 'html'),
        "GSAP": (r'gsap.min.js', 'html'),
        "core-js": (r'core-js', 'html'),
        "Three.js": (r'three.min.js', 'html'),
    },
    "Page Builders": {
        "Webflow": ('data-wf-page', 'html_attribute'),
    },
    "Miscellaneous": {
        "Webpack": ('webpack', 'html'),
        "dataLayer": (r'dataLayer\s*=\s*\[', 'html'),
    },
    "Security": {
        "HSTS": ('strict-transport-security', 'header'),
    },
    "CDN": {
        "Cloudflare": ('cloudflare', 'server_header'),
        "jsDelivr": ('cdn.jsdelivr.net', 'html'),
    }
}

def analyze_content(html_content, headers):
    detected = {}

    for category, technologies in TECHNOLOGY_FINGERPRINTS.items():
        found_in_category = []
        for tech, (pattern, scope) in technologies.items():
            if scope == 'html':
                if re.search(pattern, html_content, re.IGNORECASE):
                    found_in_category.append(tech)
            elif scope == 'script_id':
                soup = BeautifulSoup(html_content, 'html.parser')
                if soup.find('script', id=pattern):
                    found_in_category.append(tech)
            elif scope == 'div_id':
                soup = BeautifulSoup(html_content, 'html.parser')
                if soup.find(id=pattern):
                    # Avoid double-counting if Next.js (which uses React) is found
                    if "Next.js" not in found_in_category:
                        found_in_category.append(tech)
            elif scope == 'html_attribute':
                soup = BeautifulSoup(html_content, 'html.parser')
                if soup.find(attrs={pattern: True}):
                    found_in_category.append(tech)
            elif scope == 'header':
                if pattern in headers:
                    found_in_category.append(tech)
            elif scope == 'server_header':
                if pattern in headers.get('server', ''):
                    found_in_category.append(tech)
        
        if found_in_category:
            detected[category] = found_in_category
            
    return detected


@app.post("/analyze")
async def analyze_url(payload: URLPayload):
    target_url = payload.url
    
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    try:
        async with httpx.AsyncClient(verify=False) as client: # Added verify=False for flexibility
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await client.get(target_url, headers=headers, follow_redirects=True, timeout=20.0)
            
            if response.status_code == 200:
                html = response.text
                response_headers = {k.lower(): v.lower() for k, v in response.headers.items()}
                
                detected_technologies = analyze_content(html, response_headers)

                return {
                    "message": "Advanced analysis complete!",
                    "detected_technologies": detected_technologies
                }
            else:
                return {"error": f"Could not fetch the URL. Status code: {response.status_code}"}

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


@app.get("/")
def read_root():
    return {"message": "Tech Spotter API is running!"}
