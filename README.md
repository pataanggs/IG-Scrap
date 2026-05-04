# Instagram Hashtag Scraper 🚀

A modern, fast, and anti-bot-resistant Instagram scraper built with Python and [Nodriver](https://github.com/ultrafunkamsterdam/nodriver). Nodriver operates using a real Chromium browser engine under the hood, heavily minimizing the risk of getting blocked by Instagram's API rate limits or Web Application Firewalls (WAF).

Features a simple Desktop GUI (built with PyQt6) so you don't have to interact with terminals every time!

## 🌟 Prerequisites

1. **Python 3.12+**
2. **`uv` Package Manager** installed.  
   If you haven't installed `uv`, install it via curl:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   *(Make sure to restart your terminal afterward!)*

## 🛠️ Installation

 Clone the repository and navigate to the project directory:
```bash
git clone <your-repo-url>
cd IG-Scrap
```
*Note: Because we use `uv`, you don't even need to manually create virtual environments or install dependencies. `uv` handles everything instantly when you run the script!*

## 🚀 How to Use (GUI)

The easiest way to use this scraper is through the graphical interface.

1. Run the GUI application:
   ```bash
   uv run src/gui.py
   ```
2. Enter the **Hashtag** you want to scrape (e.g., `wisatalampungselatan`). *Do not include the `#` symbol!*
3. Enter your **Post Limit** (e.g., `100`).
4. Click **"Start Scraping"**.

### 🔐 First-Time Login (Important!)
Since Instagram blocks anonymous scraping, the app will open a visible Google Chrome window:
- If you aren't logged in, the script will pause for **60 seconds**. 
- Please **manually log in** to your dummy Instagram account in that browser window.
- **CRITICAL:** When Instagram asks to "Save login info", click **Save Info**. 
- After 60 seconds, the script will automatically resume and start scraping in the background. For subsequent runs, you will *not* need to log in again, as your session is saved locally in the `ig_profile/` folder!

## 📂 Output

All your scraped data is saved inside the `output/` directory (which is ignored by Git to keep your repo clean):
- `output/<hashtag>.csv`: A complete spreadsheet containing `shortcode`, `url`, `caption`, `date`, `location`, and `likes`. (Emoji friendly! Named after the hashtag you searched)
- `output/#<hashtag_name>/`: A folder containing all the downloaded high-resolution `.jpg` images from the posts.

## ⚠️ Notes & Best Practices
- **Use a Dummy Account:** Never use your primary personal/business account for scraping. Although Nodriver is quite stealthy, Instagram takes aggressive action if they detect automated activity.
- **Locations:** Instagram's backend feed GraphQL API largely omits the `location` data nowadays. The field is provided in the CSV, but don't be surprised if it remains blank.
