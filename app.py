import requests
import json
import re
import time
from flask import Flask, jsonify, request
from urllib.parse import quote

app = Flask(__name__)

class SnapchatProfileAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    def get_profile_picture_url(self, html, username):
        """Extract profile picture URL that opens in browser"""
        profile_pics = []
        
        # Method 1: Look for og:image meta tag
        og_image_match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_image_match:
            url = og_image_match.group(1)
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                profile_pics.append({"url": url, "type": "og:image", "quality": "high"})
        
        # Method 2: Look for twitter:image meta tag
        twitter_image_match = re.search(r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if twitter_image_match:
            url = twitter_image_match.group(1)
            if url not in [p["url"] for p in profile_pics]:
                profile_pics.append({"url": url, "type": "twitter:image", "quality": "high"})
        
        # Method 3: Look for profile image in img tags
        img_patterns = [
            r'<img[^>]*src=["\'](https://cf-st\.sc-cdn\.net/[^"\']+profile[^"\']+)["\'][^>]*>',
            r'<img[^>]*alt=["\'][^"\']*profile[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
            r'<img[^>]*class=["\'][^"\']*avatar[^"\']*["\'][^>]*src=["\']([^"\']+)["\']',
            r'<img[^>]*class=["\'][^"\']*profile[^"\']*["\'][^>]*src=["\']([^"\']+)["\']'
        ]
        
        for pattern in img_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for url in matches:
                if url and 'http' in url and url not in [p["url"] for p in profile_pics]:
                    profile_pics.append({"url": url, "type": "img_tag", "quality": "medium"})
        
        # Method 4: Look for background images in CSS
        bg_pattern = r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)'
        bg_matches = re.findall(bg_pattern, html, re.IGNORECASE)
        for url in bg_matches:
            if 'http' in url and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                if url not in [p["url"] for p in profile_pics]:
                    profile_pics.append({"url": url, "type": "background", "quality": "medium"})
        
        # Method 5: Generate from Snapcode (fallback)
        snapcode_url = f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=PNG"
        profile_pics.append({"url": snapcode_url, "type": "snapcode", "quality": "low"})
        
        # Method 6: Try story.snapchat.com for profile image
        try:
            story_url = f"https://story.snapchat.com/@{username}"
            story_resp = self.session.get(story_url, timeout=5)
            if story_resp.status_code == 200:
                story_html = story_resp.text
                story_img_match = re.search(r'<img[^>]*class=["\'][^"\']*user-avatar[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', story_html, re.IGNORECASE)
                if story_img_match:
                    url = story_img_match.group(1)
                    if url not in [p["url"] for p in profile_pics]:
                        profile_pics.append({"url": url, "type": "story_avatar", "quality": "high"})
        except:
            pass
        
        # Method 7: Look for profile image in JSON-LD
        jsonld_match = re.search(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        if jsonld_match:
            try:
                json_data = json.loads(jsonld_match.group(1))
                if isinstance(json_data, dict) and 'image' in json_data:
                    url = json_data.get('image')
                    if isinstance(url, str) and 'http' in url:
                        if url not in [p["url"] for p in profile_pics]:
                            profile_pics.append({"url": url, "type": "jsonld", "quality": "high"})
            except:
                pass
        
        # Return best quality image
        if profile_pics:
            # Sort by quality: high > medium > low
            quality_order = {"high": 3, "medium": 2, "low": 1}
            profile_pics.sort(key=lambda x: quality_order.get(x["quality"], 0), reverse=True)
            return profile_pics[0]["url"]
        
        return None
    
    def extract_snap_info(self, username):
        """Extract all profile information"""
        start_time = time.time()
        
        url = f"https://www.snapchat.com/add/{username}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return {
                    "success": True,
                    "data": {
                        "username": username,
                        "exists": False,
                        "profile_url": url
                    },
                    "developer": "@GoatThunder",
                    "api_by": "@GoatThunder",
                    "response_time_ms": round((time.time() - start_time) * 1000, 2)
                }
            
            html = response.text
            
            # Initialize data
            data = {
                "username": username,
                "exists": True,
                "profile_url": url,
                "profile_picture_url": None,
                "display_name": None,
                "description": None,
                "bitmoji_url": None,
                "snapcode_url": f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=PNG",
                "has_stories": False,
                "story_count": 0,
                "snap_score": None,
                "friend_count": None,
                "subscriber_count": None,
                "location": None,
                "website": None,
                "join_date": None,
                "is_verified": False
            }
            
            # 1. Get Profile Picture (PRIORITY)
            data["profile_picture_url"] = self.get_profile_picture_url(html, username)
            
            # 2. Extract display name
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                if f"({username})" in title:
                    data["display_name"] = title.split(f"({username})")[0].strip()
                else:
                    data["display_name"] = title
            
            # 3. Extract description
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
            if desc_match:
                data["description"] = desc_match.group(1)
            
            # 4. Extract subscriber count from description
            if data["description"]:
                # Hindi pattern
                hindi_match = re.search(r'(\d+(?:\.\d+)?k?)\s*सब्स्क्राइबर्स', data["description"])
                if hindi_match:
                    data["subscriber_count"] = hindi_match.group(1)
                else:
                    # English pattern
                    eng_match = re.search(r'(\d+(?:\.\d+)?k?)\s*subscribers', data["description"], re.IGNORECASE)
                    if eng_match:
                        data["subscriber_count"] = eng_match.group(1)
                
                # Extract location
                loc_match = re.search(r'📍\s*(.+?)(?:\s*\||\s*$)', data["description"])
                if not loc_match:
                    loc_match = re.search(r'from\s+(.+?)(?:\s*\||\s*$)', data["description"], re.IGNORECASE)
                if loc_match:
                    data["location"] = loc_match.group(1).strip()
                
                # Extract website
                web_match = re.search(r'(?:Instagram|Youtube|Website):\s*(@?\w+[^\s|]*)', data["description"])
                if web_match:
                    data["website"] = web_match.group(1).strip()
            
            # 5. Extract Bitmoji URL
            bitmoji_patterns = [
                r'https://images\.bitmoji\.com/render/panel/[^\s"\']+',
                r'https://cf-st\.sc-cdn\.net/aps/bolt_web/[^\s"\']*bitmoji[^\s"\']*',
                r'"bitmojiUrl"\s*:\s*"([^"]+)"',
                r'bitmoji_url["\']?\s*:\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in bitmoji_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    data["bitmoji_url"] = match.group(0) if pattern.startswith('http') else match.group(1)
                    break
            
            # 6. Extract Snap Score
            score_patterns = [
                r'"snapScore"\s*:\s*"(\d+)"',
                r'snapScore["\']?\s*:\s*["\']?(\d+)["\']?',
                r'"score"\s*:\s*"(\d+)"'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    data["snap_score"] = match.group(1)
                    break
            
            # 7. Extract Friend Count
            friend_patterns = [
                r'"friendCount"\s*:\s*"(\d+)"',
                r'friendCount["\']?\s*:\s*["\']?(\d+)["\']?',
                r'"friends"\s*:\s*"(\d+)"'
            ]
            
            for pattern in friend_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    data["friend_count"] = match.group(1)
                    break
            
            # 8. Check for verification
            if "verified" in html.lower() or '"isVerified":true' in html:
                data["is_verified"] = True
            
            # 9. Check stories
            try:
                story_url = f"https://story.snapchat.com/@{username}"
                story_resp = self.session.get(story_url, timeout=5)
                if story_resp.status_code == 200:
                    data["has_stories"] = True
                    story_html = story_resp.text
                    
                    # Count stories
                    story_count = len(re.findall(r'data-story-id|story-item|story-container|media-story', story_html, re.IGNORECASE))
                    data["story_count"] = min(story_count, 50)
                    
                    # Try to get better profile picture from stories page
                    if not data["profile_picture_url"] or "snapcode" in data["profile_picture_url"]:
                        story_img = re.search(r'<img[^>]*class=["\'][^"\']*avatar[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', story_html, re.IGNORECASE)
                        if story_img:
                            data["profile_picture_url"] = story_img.group(1)
            except:
                pass
            
            # 10. Calculate profile completeness score
            score = 0
            if data["display_name"]: score += 20
            if data["profile_picture_url"] and "snapcode" not in data["profile_picture_url"]: score += 25
            if data["description"]: score += 15
            if data["bitmoji_url"]: score += 20
            if data["snap_score"]: score += 10
            if data["has_stories"]: score += 10
            data["profile_completeness_score"] = min(score, 100)
            
            # 11. Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            # 12. Add image preview info if profile picture exists
            if data.get("profile_picture_url"):
                data["profile_picture_info"] = {
                    "direct_url": data["profile_picture_url"],
                    "opens_in_browser": True,
                    "preview_url": data["profile_picture_url"],
                    "formats": ["PNG", "JPEG", "WEBP"]
                }
            
            return {
                "success": True,
                "data": data,
                "developer": "@GoatThunder",
                "api_by": "@GoatThunder",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "developer": "@GoatThunder",
                "api_by": "@GoatThunder"
            }

# Initialize API
snap_api = SnapchatProfileAPI()

@app.route('/')
def home():
    return jsonify({
        "api": "Snapchat Profile API",
        "version": "2.0",
        "developer": "@GoatThunder",
        "api_by": "@GoatThunder",
        "features": [
            "Profile Picture URL (Browser compatible)",
            "Display Name",
            "Description/Bio",
            "Subscriber Count",
            "Location",
            "Bitmoji URL",
            "Snap Score",
            "Friend Count",
            "Story Info",
            "Profile Completeness Score"
        ],
        "endpoints": {
            "/profile/<username>": "Get complete profile info",
            "/check/<username>": "Quick existence check",
            "/multi?users=user1,user2": "Check multiple users"
        },
        "example": "/profile/priyapanchal272"
    })

@app.route('/profile/<username>')
def get_profile(username):
    """Main endpoint for complete profile data"""
    return jsonify(snap_api.extract_snap_info(username))

@app.route('/check/<username>')
def quick_check(username):
    """Quick check if user exists"""
    start = time.time()
    url = f"https://www.snapchat.com/add/{username}"
    
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        exists = response.status_code == 200
        
        return jsonify({
            "success": True,
            "data": {
                "username": username,
                "exists": exists,
                "profile_url": url,
                "snapcode_url": f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=PNG" if exists else None
            },
            "developer": "@GoatThunder",
            "api_by": "@GoatThunder",
            "response_time_ms": round((time.time() - start) * 1000, 2)
        })
    except:
        return jsonify({
            "success": False,
            "data": {
                "username": username,
                "exists": False,
                "error": "Connection failed"
            },
            "developer": "@GoatThunder",
            "api_by": "@GoatThunder"
        })

@app.route('/multi')
def multi_users():
    """Check multiple usernames"""
    users_param = request.args.get('users', '')
    if not users_param:
        return jsonify({
            "success": False,
            "error": "Provide users parameter",
            "example": "/multi?users=user1,user2,user3"
        })
    
    users = [u.strip() for u in users_param.split(',')[:10]]  # Max 10
    results = []
    
    for user in users:
        info = snap_api.extract_snap_info(user)
        if info["success"]:
            results.append({
                "username": user,
                "exists": info["data"]["exists"],
                "display_name": info["data"].get("display_name"),
                "profile_picture": info["data"].get("profile_picture_url"),
                "subscribers": info["data"].get("subscriber_count")
            })
        else:
            results.append({
                "username": user,
                "exists": False,
                "error": info.get("error")
            })
    
    return jsonify({
        "success": True,
        "results": results,
        "count": len(results),
        "developer": "@GoatThunder",
        "api_by": "@GoatThunder"
    })

@app.route('/image/<username>')
def get_profile_image(username):
    """Get only profile image URL"""
    info = snap_api.extract_snap_info(username)
    
    if info["success"] and info["data"]["exists"]:
        return jsonify({
            "success": True,
            "username": username,
            "profile_picture_url": info["data"].get("profile_picture_url"),
            "bitmoji_url": info["data"].get("bitmoji_url"),
            "snapcode_url": info["data"].get("snapcode_url"),
            "all_images": {
                "profile_picture": info["data"].get("profile_picture_url"),
                "bitmoji": info["data"].get("bitmoji_url"),
                "snapcode": info["data"].get("snapcode_url")
            },
            "developer": "@GoatThunder",
            "api_by": "@GoatThunder"
        })
    
    return jsonify({
        "success": False,
        "username": username,
        "error": "No profile image found",
        "developer": "@GoatThunder",
        "api_by": "@GoatThunder"
    })

@app.route('/image/<username>')
def get_profile_image(username):
    """Get only profile image URL"""
    info = snap_api.extract_snap_info(username)

    if info["success"] and info["data"]["exists"]:
        return jsonify({
            "success": True,
            "username": username,
            "profile_picture_url": info["data"].get("profile_picture_url"),
            "bitmoji_url": info["data"].get("bitmoji_url"),
            "snapcode_url": info["data"].get("snapcode_url"),
            "all_images": {
                "profile_picture": info["data"].get("profile_picture_url"),
                "bitmoji": info["data"].get("bitmoji_url"),
                "snapcode": info["data"].get("snapcode_url")
            },
            "developer": "@GoatThunder",
            "api_by": "@GoatThunder"
        })

    return jsonify({
        "success": False,
        "username": username,
        "error": "No profile image found",
        "developer": "@GoatThunder",
        "api_by": "@GoatThunder"
    })

# 🔚 FILE ENDS HERE — NOTHING BELOW THIS
