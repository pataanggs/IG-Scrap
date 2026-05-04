import asyncio
import json
import os
import requests
import nodriver as uc
import pandas as pd

async def run_scraper(hashtag: str, limit: int = 100, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)

    out_dir = os.path.join("output", f"#{hashtag}")
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Start undetected browser
    log("Starting nodriver...")
    chrome_path = "/home/pataangg/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome"
    
    if os.path.exists(chrome_path):
        browser = await uc.start(
            headless=False,
            browser_executable_path=chrome_path,
            user_data_dir="./ig_profile"
        )
    else:
        browser = await uc.start(
            headless=False,
            user_data_dir="./ig_profile"
        )
        
    log("Navigating to Instagram...")
    tab = await browser.get('https://www.instagram.com')
    await asyncio.sleep(4)
    
    # Check if user needs to log in
    html = await tab.evaluate("document.body.innerHTML")
    if "Verify your account" in html or "Log in" in html or "Log In" in html:
        log("=====================================================")
        log("ACTION REQUIRED:")
        log("Please log in to your dummy account in the browser window.")
        log("The script will wait 60 seconds for you to do so...")
        log("Make sure to click 'Save Info' so the session persists!")
        log("=====================================================")
        for i in range(60):
            await asyncio.sleep(1)
        log("Resuming...")

    log(f"Fetching JSON data for #{hashtag}...")
    
    extracted_data = []
    seen_shortcodes = set()
    
    api_url = f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={hashtag}"
    max_id = ""
    
    while len(extracted_data) < limit:
        log("Executing internal fetch...")
        
        graphql_endpoint = "https://www.instagram.com/graphql/query/?query_hash=9b498c08113f1e09617a1703c22b2f32&variables=" + json.dumps({
            "tag_name": hashtag,
            "first": 50,
            "after": max_id
        })
        
        script = f"""
        (async () => {{
            try {{
                const response = await fetch(`{graphql_endpoint}`, {{
                    method: 'GET',
                    headers: {{
                        'X-IG-App-ID': '936619743392459',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': '*/*'
                    }}
                }});
                window.__ig_data = await response.text();
            }} catch (e) {{
                window.__ig_data = JSON.stringify({{error: e.message}});
            }}
        }})();
        """
        await tab.evaluate(script)
        
        log("Waiting for fetch to complete...")
        body_text = None
        for _ in range(15):
            body_text = await tab.evaluate("window.__ig_data")
            if body_text:
                await tab.evaluate("window.__ig_data = null") # reset for next loop
                break
            await asyncio.sleep(1)
            
        if not body_text:
            log("Fetch timed out or returned empty.")
            break
            
        try:
            data = json.loads(body_text)
            
            with open('output/debug_response.json', 'w') as dbg:
                json.dump(data, dbg, indent=2)
            
            extracted_count_this_loop = 0
            edges = []
            
            if 'data' in data:
                if 'recent' in data['data']:
                     for section in data['data']['recent']['sections']:
                         for layout in section.get('layout_content', {}).get('medias', []):
                             edges.append(layout.get('media', {}))
                elif 'top' in data['data']:
                     for section in data['data']['top']['sections']:
                         for layout in section.get('layout_content', {}).get('medias', []):
                             edges.append(layout.get('media', {}))
                elif 'hashtag' in data['data'] and 'edge_hashtag_to_media' in data['data']['hashtag']:
                     for edge in data['data']['hashtag']['edge_hashtag_to_media']['edges']:
                         edges.append(edge.get('node', {}))
            
            log(f"Found {len(edges)} items in this request.")
            
            for media in edges:
                if len(extracted_data) >= limit:
                    break
                
                shortcode = media.get('code') or media.get('shortcode')
                if not shortcode or shortcode in seen_shortcodes:
                    continue
                seen_shortcodes.add(shortcode)
                
                caption = ""
                caption_obj = media.get('caption') or media.get('edge_media_to_caption')
                if isinstance(caption_obj, dict):
                    if 'edges' in caption_obj and caption_obj['edges']:
                        caption = caption_obj['edges'][0].get('node', {}).get('text', '')
                    else:
                        caption = caption_obj.get('text', '')
                    
                likes = media.get('like_count') or media.get('edge_liked_by', {}).get('count', 0)
                
                timestamp = media.get('taken_at') or media.get('taken_at_timestamp')
                date_str = ""
                if timestamp:
                    date_str = pd.to_datetime(timestamp, unit='s').strftime("%Y-%m-%d %H:%M:%S")
                    
                location = media.get('location', {}).get('name', '') if media.get('location') else ''
                
                img_url = ""
                if 'image_versions2' in media and 'candidates' in media['image_versions2']:
                    img_url = media['image_versions2']['candidates'][0]['url']
                elif 'display_url' in media:
                    img_url = media['display_url']
                    
                post_url = f"https://www.instagram.com/p/{shortcode}/"
                    
                extracted_data.append({
                    "shortcode": shortcode,
                    "url": post_url,
                    "caption": caption,
                    "date": date_str,
                    "location": location,
                    "likes": likes
                })
                extracted_count_this_loop += 1
                
                if img_url:
                    save_path = os.path.join(out_dir, f"{shortcode}.jpg")
                    try:
                        r = requests.get(img_url, stream=True)
                        if r.status_code == 200:
                            with open(save_path, 'wb') as f:
                                for chunk in r.iter_content(1024):
                                    f.write(chunk)
                    except Exception as e:
                        pass
                        
            log(f"Extracted {len(extracted_data)}/{limit} posts.")
            
            page_info = {}
            if 'data' in data and 'recent' in data['data']:
                page_info = data['data']['recent'].get('page_info', {})
            elif 'data' in data and 'hashtag' in data['data']:
                page_info = data['data']['hashtag'].get('edge_hashtag_to_media', {}).get('page_info', {})
                
            if page_info.get('has_next_page'):
                max_id = page_info.get('end_cursor') or page_info.get('max_id', "")
                await asyncio.sleep(2)
            else:
                if extracted_count_this_loop == 0:
                     log("No posts found. Is the hashtag empty or blocked?")
                log("No more pages available.")
                break
                
        except json.JSONDecodeError:
            log("Failed to decode JSON. Anti-bot might be showing a fallback page.")
            break
        except Exception as e:
            log(f"Error processing loop: {e}")
            break

    browser.stop()
    
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        csv_filename = f'output/{hashtag}.csv'
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        log(f"Extraction complete! Saved to {csv_filename}")

async def main():
    await run_scraper("wisatalampungselatan", 100)

if __name__ == "__main__":
    uc.loop().run_until_complete(main())
