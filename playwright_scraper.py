import json
import time
import os
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

def download_image(url, save_path):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def main():
    hashtag = "wisatalampungselatan"
    limit = 20
    os.makedirs(f"#{hashtag}", exist_ok=True)
    
    try:
        with open('cookies.json', 'r') as f:
            raw_cookies = json.load(f)
            # Filter cookies for Playwright format
            cookies = []
            for c in raw_cookies:
                # Instagram gets caught in a redirect loop if we pass empty session/user cookies
                if c["value"] == '""' or not c["value"]:
                    continue
                cookie = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c["domain"],
                    "path": c["path"]
                }
                cookies.append(cookie)
    except FileNotFoundError:
        print("Please provide cookies.json")
        return

    extracted_data = []

    with sync_playwright() as p:
        print("Launching headless browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        
        page = context.new_page()
        
        # Intercept network requests containing JSON data
        def handle_response(response):
            if "graphql/query" in response.url or "api/v1/tags/" in response.url:
                try:
                    data = response.json()
                    edges = []
                    
                    # Log finding for debugging
                    print("Received JSON length: ", len(str(data)))
                    
                    # Dump the first large JSON locally to inspect keys
                    if len(str(data)) > 100000 and not os.path.exists("dump.json"):
                        with open("dump.json", "w") as df:
                            json.dump(data, df, indent=2)
                        print("Saved large JSON to dump.json for debugging.")
                    
                    # Path 1: new graphql structure (`hashtag` root)
                    if 'data' in data and data['data'] and 'hashtag' in data['data']:
                        hashtag_node = data['data']['hashtag']
                        if hashtag_node and 'edge_hashtag_to_media' in hashtag_node:
                            edges = hashtag_node['edge_hashtag_to_media']['edges']
                            
                    # Path 2: xdt_api__v1__tags__web_info (layout content)
                    elif 'data' in data and data['data'] and 'xdt_api__v1__tags__web_info' in data['data']:
                        info = data['data']['xdt_api__v1__tags__web_info']
                        if info and 'recent' in info and info['recent']:
                            sections = info['recent']['sections']
                            for section in sections:
                                for layout_content in section.get('layout_content', {}).get('medias', []):
                                    edges.append({"node": layout_content.get('media', {})})
                                
# Path 4: new GraphQL serp grid format
                    elif 'data' in data and data['data'] and 'xdt_fbsearch__top_serp_graphql' in data['data']:
                        search_edges = data['data']['xdt_fbsearch__top_serp_graphql'].get('edges', [])
                        for edge in search_edges:
                            node = edge.get('node', {})
                            if node.get('__typename') == 'XDTTopSerpMediaGridUnit':
                                for item in node.get('items', []):
                                    edges.append({"node": item})
                            elif node.get('__typename') == 'XDTMediaDict':
                                edges.append({"node": node})
                                
                    # If we found items to process
                    for edge in edges:
                        if len(extracted_data) >= limit: return
                        
                        node = edge.get('node', {})
                        shortcode = node.get('code') or node.get('shortcode')
                        if not shortcode: continue
                        
                        # Prevent duplicate saving
                        if shortcode in [d.get('shortcode') for d in extracted_data]:
                            continue
                            
                        # Extract Caption
                        caption = ""
                        caption_data = node.get('edge_media_to_caption') or node.get('caption')
                        if isinstance(caption_data, dict):
                            edges_caption = caption_data.get('edges', [])
                            if edges_caption:
                                caption = edges_caption[0].get('node', {}).get('text', '')
                            else:
                                caption = caption_data.get('text', '')
                                
                        # Date
                        timestamp = node.get('taken_at') or node.get('taken_at_timestamp')
                        date_str = ""
                        if timestamp:
                            date_str = pd.to_datetime(timestamp, unit='s').strftime("%Y-%m-%d %H:%M:%S")
                            
                        # Like count
                        likes = node.get('like_count') or node.get('edge_liked_by', {}).get('count', 0)
                        
                        # Location (often omitted by Instagram in hashtag layout, but we fetch if exists)
                        location = node.get('location', {}).get('name', '') if node.get('location') else ''
                        
                        # High Res Image
                        img_url = ""
                        candidates = node.get('image_versions2', {}).get('candidates', [])
                        if candidates:
                            img_url = candidates[0].get('url', '')
                        else:
                            img_url = node.get('display_url', '')
                            
                        extracted_data.append({
                            "shortcode": shortcode,
                            "caption": caption,
                            "date": date_str,
                            "location": location,
                            "likes": likes
                        })
                        
                        if img_url:
                            img_path = os.path.join(f"#{hashtag}", f"{shortcode}.jpg")
                            # Disable download for testing speed or enable to save
                            download_image(img_url, img_path)
                            
                        print(f"Extracted {len(extracted_data)}/{limit} posts...")
                except Exception as e:
                    # Ignore parsing errors for other non-hashtag graphql endpoints
                    pass

        page.on("response", handle_response)
        
        print(f"Navigating to hashtag #{hashtag}...")
        page.goto(f"https://www.instagram.com/explore/tags/{hashtag}/", wait_until="networkidle")
        
        # Take a screenshot so we know if it's logging in or showing an error
        page.screenshot(path="debug_page.png")
        
        print("Scrolling page to load more data...")
        for i in range(15):
            if len(extracted_data) >= limit: break
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2) # Give it 2 seconds to fetch the data
            
        browser.close()
        
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        df.to_csv('data.csv', index=False, encoding='utf-8')
        print(f"Data mapping for {len(extracted_data)} posts exported to data.csv")
    else:
        print("No post JSON payloads found. Instagram might be presenting a login popup.")

if __name__ == "__main__":
    main()
