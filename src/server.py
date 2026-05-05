import os
import json
import datetime
import re
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
import yt_dlp
from youtube_comment_downloader import YoutubeCommentDownloader

mcp = FastMCP(name="Whats Trending On Social Media", dependencies=["beautifulsoup4", "youtube-comment-downloader", "yt_dlp", "requests"])

tiktok_env = os.getenv("tiktok")
if tiktok_env:
    os.environ["tiktok"] = tiktok_env

# Global headers for TikTok
TIKTOK_HEADERS = {
    "x-rapidapi-key": os.getenv("tiktok", ""),
    "x-rapidapi-host": "tiktok-best-experience.p.rapidapi.com"
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

@mcp.tool()
def get_comments_yt(video_id: str, max_comments: int = 100) -> List[str]:
    """Fetch YouTube comments by video ID.  
    Returns up to `max_comments` comment texts."""
    try:
        d = YoutubeCommentDownloader()
        comments = []
        for c in d.get_comments_from_url(f"https://www.youtube.com/watch?v={video_id}"):
            comments.append(c["text"])
            if len(comments) >= max_comments:
                break
        return comments
    except Exception as e:
        return [f"Error fetching comments: {str(e)}"]

def _yt_trending(region: Optional[str] = None, limit: int = 10) -> List[Dict[str, str]]:
    url = "https://www.youtube.com/feed/trending"
    if region: 
        url += f"?gl={region.upper()}"
    opts = {'extract_flat': True, 'force_generic_extractor': True, 'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return [{"title": v.get("title", "No Title"), "url": f"https://www.youtube.com/watch?v={v.get('id')}"} for v in info.get("entries", [])[:limit] if v.get("id")]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_yt_trending_global(limit: int = 10) -> List[Dict[str, str]]:
    """Get trending YouTube videos globally (US).  
    Returns list of titles and URLs."""
    return _yt_trending(limit=limit)

@mcp.tool()
def get_yt_trending_by_region(region_code: str = "IT", limit: int = 10) -> List[Dict[str, str]]:
    """Get trending YouTube videos by region code.  
    Returns list of titles and URLs."""
    return _yt_trending(region=region_code, limit=limit)

@mcp.tool()
def get_yt_video_info(url: str) -> Optional[Dict[str, str]]:
    """Get metadata of a YouTube video from its URL.  
    Includes title, views, likes, description, etc."""
    opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            i = ydl.extract_info(url, download=False)
            return {
                "title": i.get("title", ""),
                "channel": i.get("uploader", ""),
                "description": i.get("description", ""),
                "views": f"{i.get('view_count', 0):,}",
                "likes": f"{i.get('like_count', 0):,}" if i.get('like_count') else "N/A",
                "upload_date": i.get("upload_date", ""),
                "duration": f"{i.get('duration', 0)} seconds",
                "thumbnail": i.get("thumbnail", ""),
                "url": i.get("webpage_url", url),
            }
    except Exception: 
        return None

@mcp.tool()
def tiktok_trending_global() -> str:
    """Fetches and summarizes trending TikTok videos with stats and hashtags."""
    if not TIKTOK_HEADERS["x-rapidapi-key"]:
        return "❌ Manca la chiave API di TikTok."
        
    try:
        res = requests.get("https://tiktok-best-experience.p.rapidapi.com/trending", headers=TIKTOK_HEADERS)
        if res.status_code != 200:
            return f"❌ HTTP Error: {res.status_code}"
            
        data = res.json()
        if data.get("status") != "ok" or "data" not in data:
            return "❌ Invalid or failed response from TikTok API."

        videos = data["data"].get("list", [])
        if not videos:
            return "⚠️ No trending videos found."

        return _format_tiktok_videos(videos)

    except Exception as e:
        return f"❌ Error: {str(e)}"

@mcp.tool()
def get_this_weeks_reels_trends() -> List[Dict[str, str]]:
    """Scrape this week’s Instagram Reels trends.  
    Returns list with trend name, date, and stats."""
    try:
        r = requests.get("https://later.com/blog/instagram-reels-trends/", headers={"User-Agent": USER_AGENT})
        if r.status_code != 200: 
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        today = datetime.date.today()
        trends = []
        for h in soup.select("h3"):
            t = h.get_text(strip=True)
            if t.startswith("Trend:"):
                try:
                    parts = re.split(r'\s*[-—–]\s*', t[len("Trend:"):], maxsplit=1)
                    if len(parts) != 2:
                        continue
                    name, date_str = parts
                    trend_date = datetime.datetime.strptime(date_str.strip(), "%B %d, %Y").date()
                    if (today - trend_date).days > 30: 
                        continue
                    ps = h.find_next_siblings("p", limit=2)
                    trends.append({
                        "date": str(trend_date),
                        "trend": name.strip(),
                        "description": ps[0].get_text(strip=True) if ps else "",
                        "posts_info": ps[1].get_text(strip=True) if len(ps) > 1 else ""
                    })
                except Exception:
                    continue
        return trends
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def search_tiktok_by_keyword(query: str, limit: int = 10) -> str:
    """Cerca video TikTok per keyword (es. 'viaggi over 50'). Restituisce le statistiche dei video."""
    if not TIKTOK_HEADERS["x-rapidapi-key"]:
        return "❌ Manca la chiave API di TikTok."
        
    try:
        res = requests.get("https://tiktok-best-experience.p.rapidapi.com/search/video", headers=TIKTOK_HEADERS, params={"keywords": query, "count": limit})
        if res.status_code != 200:
            return f"❌ Errore API o endpoint non supportato (Status: {res.status_code}). Per query specifiche si consiglia l'integrazione Apify come da guida."
        data = res.json()
        videos = data.get("data", {}).get("list", [])
        if not videos:
            return "⚠️ Nessun video trovato."
        
        return _format_tiktok_videos(videos)
    except Exception as e:
        return f"❌ Errore: {str(e)}"

@mcp.tool()
def search_tiktok_by_hashtag(hashtag: str, limit: int = 10) -> str:
    """Cerca video TikTok per hashtag (es. 'turismoitalia')."""
    if not TIKTOK_HEADERS["x-rapidapi-key"]:
        return "❌ Manca la chiave API di TikTok."
        
    hashtag = hashtag.replace("#", "")
    try:
        res = requests.get("https://tiktok-best-experience.p.rapidapi.com/challenge/search", headers=TIKTOK_HEADERS, params={"keywords": hashtag, "count": limit})
        if res.status_code != 200:
            return f"❌ Errore API o endpoint non supportato (Status: {res.status_code}). Per hashtag si consiglia Apify."
        data = res.json()
        videos = data.get("data", {}).get("list", [])
        if not videos:
            return "⚠️ Nessun video trovato."
        
        return _format_tiktok_videos(videos)
    except Exception as e:
        return f"❌ Errore: {str(e)}"

def _format_tiktok_videos(videos: list) -> str:
    summary = [f"✅ Found {len(videos)} TikTok videos.\n"]
    for i, video in enumerate(videos):
        author_name = video.get("author", {}).get("nickname") if isinstance(video.get("author"), dict) else "N/A"
        desc = video.get("desc", "No desc")
        link = video.get("share_url", "No link")
        
        stats = video.get("statistics", {})
        plays = stats.get("play_count", 0)
        likes = stats.get("digg_count", 0)
        comments = stats.get("comment_count", 0)
        shares = stats.get("share_count", 0)
        saves = stats.get("collect_count", 0)
        engagement = ((likes + comments + shares + saves) / plays) * 100 if plays > 0 else 0.0

        summary.append(f"--- Video {i} ---\n"
                       f"Author: {author_name}\n"
                       f"Desc: {desc}\n"
                       f"Link: {link}\n"
                       f"📊 Views: {plays:,} | Likes: {likes:,} | Comments: {comments:,} | Engagement: {engagement:.2f}%\n"
                       f"{'=' * 40}")
    return "\n".join(summary)

@mcp.tool()
def search_instagram_reels_by_hashtag(hashtag: str, limit: int = 10) -> str:
    """Ricerca Instagram Reels per hashtag usando Apify (Actor: apify/instagram-scraper)."""
    apify_token = os.getenv("apify")
    if not apify_token:
        return "❌ Manca la chiave API di Apify (configura la variabile d'ambiente 'apify')."
        
    try:
        from apify_client import ApifyClient
        client = ApifyClient(apify_token)
        
        # Pulizia dell'hashtag (rimuoviamo il # se presente)
        clean_hashtag = hashtag.replace("#", "")
        
        # Prepariamo l'input per l'attore di Apify
        # Usiamo l'URL diretto per l'hashtag per maggiore affidabilità
        run_input = {
            "directUrls": [f"https://www.instagram.com/explore/tags/{clean_hashtag}/"],
            "resultsType": "details",
            "resultsLimit": limit,
            "searchType": "hashtag",
            "searchLimit": 1
        }
        
        # Lanciamo lo scraper ufficiale di Instagram su Apify
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        videos = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # Filtriamo solo i Reel/Video se possibile
            if item.get("type") == "Video" or item.get("videoUrl") or item.get("isVideo"):
                videos.append(item)
                
        if not videos:
            return "⚠️ Nessun reel trovato per questo hashtag o limite raggiunto."
            
        summary = [f"✅ Found {len(videos)} Instagram Reels.\n"]
        for i, video in enumerate(videos):
            url = video.get("url", "No link")
            # Tronchiamo la caption a 100 caratteri per evitare output giganti
            desc = video.get("caption", "No desc").replace("\n", " ")[:100]
            views = video.get("videoViewCount", 0) or 0
            likes = video.get("likesCount", 0) or 0
            comments = video.get("commentsCount", 0) or 0
            
            # Calcolo basico dell'engagement
            eng = ((likes + comments) / views) * 100 if views > 0 else 0.0
            
            summary.append(f"--- Reel {i} ---\n"
                           f"Link: {url}\n"
                           f"Caption: {desc}...\n"
                           f"📊 Views: {views:,} | Likes: {likes:,} | Comments: {comments:,} | Engagement: {eng:.2f}%\n"
                           f"{'=' * 40}")
                           
        return "\n".join(summary)
        
    except ImportError:
        return "❌ Errore: La libreria 'apify-client' non è installata. Esegui 'pip install apify-client'."
    except Exception as e:
        return f"❌ Errore durante l'esecuzione di Apify: {str(e)}"

@mcp.tool()
def search_yt_shorts_by_keyword(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Cerca YouTube Shorts per keyword usando yt-dlp."""
    opts = {'extract_flat': True, 'force_generic_extractor': True, 'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query} #shorts", download=False)
            return [{"title": v.get("title", "No Title"), "url": f"https://www.youtube.com/watch?v={v.get('id')}", "views": v.get("view_count", 0)} for v in info.get("entries", []) if v.get("id")]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def rank_videos_by_engagement(videos: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """
    Ordina una lista di video (dizionari con 'views', 'likes', 'comments', 'shares', 'saves') 
    calcolando l'engagement rate: (likes + comments + shares + saves) / views.
    """
    ranked = []
    for v in videos:
        views = float(v.get('views', 0) or 0)
        if views > 0:
            eng = (float(v.get('likes', 0) or 0) + float(v.get('comments', 0) or 0) + 
                   float(v.get('shares', 0) or 0) + float(v.get('saves', 0) or 0)) / views
            v['engagement_rate'] = round(eng, 4)
        else:
            v['engagement_rate'] = 0.0
        ranked.append(v)
    return sorted(ranked, key=lambda x: x['engagement_rate'], reverse=True)
