# File: main.py
# This version scans linked JavaScript files for the most accurate detection.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import re
import asyncio
from urllib.parse import urljoin, urlparse

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

# --- FINGERPRINT LIBRARY V4 ---
# Expanded with more technologies and CMS detectors.
TECHNOLOGY_FINGERPRINTS = {
    "Analytics": [
        {"name": "Microsoft Clarity", "pattern": r'clarity.ms', "type": "presence"},
        {"name": "Hotjar", "pattern": r'static.hotjar.com', "type": "presence"},
    ],
    "Google Tags": [
        {"name": "Google Tag Manager (Loader)", "pattern": r'googletagmanager.com/gtm.js', "type": "presence"},
        {"name": "Google Analytics GA4", "pattern": r'G-[A-Z0-9]{10}', "type": "extract_all"},
        {"name": "Universal Analytics", "pattern": r'UA-[0-9]{4,9}-[0-9]{1,4}', "type": "extract_all"},
        {"name": "Google Tag Manager ID", "pattern": r'GTM-[A-Z0-9]{7}', "type": "extract_all"},
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
    "Page Builders & CMS": [
        {"name": "Webflow", "pattern": 'data-wf-page', "type": "html_attribute"},
        {"name": "Shopify", "pattern": r'\.myshopify\.com', "type": "presence"},
        {"name": "WordPress", "pattern": r'/wp-content/', "type": "presence"},
    ],
    "A/B Testing": [
        {"name": "VWO", "pattern": r'dev.visualwebsiteoptimizer.com', "type": "presence"},
        {"name": "Optimizely", "pattern": r'cdn.optimizely.com', "type": "presence"},
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

def analyze_combined_content(full_content, headers):
    detected = {}
    soup = BeautifulSoup(full_content, 'html.parser')

    for category, technologies in TECHNOLOGY_FINGERPRINTS.items():
        found_in_category = []
        for tech in technologies:
            name, pattern, tech_type = tech["name"], tech["pattern"], tech["type"]
            found, details = False, []

            if tech_type == "presence":
                if re.search(pattern, full_content, re.IGNORECASE): found = True
            elif tech_type == "extract_all":
                matches = re.findall(pattern, full_content)
                if matches:
                    found, details = True, list(set(matches))
            elif tech_type == "script_id":
                if soup.find('script', id=pattern): found = True
            elif tech_type == "div_id":
                if soup.find(id=pattern) and "Next.js" not in [f.get("name") for f in found_in_category]: found = True
            elif tech_type == "html_attribute":
                if soup.find(attrs={pattern: True}): found = True
            elif tech_type == "header":
                if pattern in headers: found = True
            elif tech_type == "server_header":
                if pattern in headers.get('server', ''): found = True
            
            if found:
                tech_result = {"name": name}
                if details: tech_result["ids"] = details
                found_in_category.append(tech_result)
        
        if found_in_category:
            detected[category] = found_in_category
            
    return detected

async def fetch_script_content(client, url):
    try:
        script_res = await client.get(url, timeout=10.0)
        script_res.raise_for_status()
        return script_res.text
    except Exception:
        return "" # Return empty string if a script fails to load

@app.post("/analyze")
async def analyze_url(payload: URLPayload):
    target_url = payload.url
    
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    try:
        async with httpx.AsyncClient(verify=False, http2=True) as client:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await client.get(target_url, headers=headers, follow_redirects=True, timeout=20.0)
            response.raise_for_status()
            
            html = response.text
            response_headers = {k.lower(): v.lower() for k, v in response.headers.items()}
            
            # --- NEW SCRIPT ANALYSIS LOGIC ---
            soup = BeautifulSoup(html, 'html.parser')
            scripts = soup.find_all('script', src=True)
            script_urls = [urljoin(str(response.url), script['src']) for script in scripts]
            
            # Fetch all scripts concurrently
            script_tasks = [fetch_script_content(client, url) for url in script_urls]
            script_contents = await asyncio.gather(*script_tasks)
            
            # Combine HTML and all script contents for a full analysis
            full_content_to_analyze = html + "\n".join(script_contents)
            
            detected_technologies = analyze_combined_content(full_content_to_analyze, response_headers)
            
            return { "message": "Deep analysis complete!", "detected_technologies": detected_technologies }

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

@app.get("/")
def read_root():
    return {"message": "Tech Spotter API is running!"}
