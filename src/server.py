import os
import json
import datetime
import re
import requests
from typing import Any, List, Dict, Optional
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
import yt_dlp
from youtube_comment_downloader import YoutubeCommentDownloader
import scrapetube

mcp = FastMCP(name="Whats Trending On Social Media", dependencies=["beautifulsoup4", "youtube-comment-downloader", "yt_dlp", "scrapetube", "requests", "apify-client", "instaloader"])

tiktok_env = os.getenv("tiktok")
if tiktok_env:
    os.environ["tiktok"] = tiktok_env

# Global headers for TikTok
TIKTOK_HEADERS = {
    "x-rapidapi-key": os.getenv("tiktok", ""),
    "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
DEFAULT_INVIDIOUS_INSTANCES = [
    "https://inv.thepixora.com",
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://yt.chocolatemoo53.com",
]

def _clamp_limit(limit: int, default: int = 10, maximum: int = 50) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, maximum))

def _yt_trending_queries(region: str) -> List[str]:
    region = (region or "US").strip().upper()[:2]
    query_map = {
        "IT": [
            "tendenze youtube italia oggi",
            "video virali italia oggi",
            "musica tendenza italia oggi",
            "shorts virali italia oggi",
        ],
        "US": [
            "trending youtube videos today",
            "viral videos today",
            "trending music videos today",
            "viral shorts today",
        ],
    }
    return query_map.get(region, [
        f"trending youtube videos {region} today",
        f"viral videos {region} today",
        f"trending shorts {region} today",
    ])

def _invidious_instances() -> List[str]:
    raw = os.getenv("INVIDIOUS_INSTANCES", "")
    instances = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    return instances or DEFAULT_INVIDIOUS_INSTANCES

def _format_invidious_trending_item(item: Dict[str, Any], region: str, source: str) -> Dict[str, str]:
    video_id = item.get("videoId", "")
    return {
        "title": item.get("title", "Nessun Titolo"),
        "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
        "channel": item.get("author", ""),
        "views": str(item.get("viewCount", "N/D")),
        "published": item.get("publishedText", ""),
        "duration": str(item.get("lengthSeconds", "")),
        "thumbnail": (item.get("videoThumbnails") or [{}])[-1].get("url", ""),
        "source": source,
        "region": region,
    }

def _yt_trending_from_invidious(region: str, limit: int) -> tuple[List[Dict[str, str]], List[str]]:
    errors = []
    for instance in _invidious_instances():
        url = f"{instance}/api/v1/trending"
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                params={"region": region, "type": "default"},
                timeout=12,
            )
            if response.status_code != 200:
                errors.append(f"{instance}: HTTP {response.status_code}")
                continue
            data = response.json()
            if not isinstance(data, list):
                errors.append(f"{instance}: risposta non lista")
                continue
            videos = [
                _format_invidious_trending_item(item, region, f"invidious:{instance}")
                for item in data
                if item.get("videoId")
            ]
            if videos:
                return videos[:limit], errors
            errors.append(f"{instance}: nessun video")
        except Exception as e:
            errors.append(f"{instance}: {str(e)}")
    return [], errors

def _yt_trending(region: str = "US", limit: int = 10) -> List[Dict[str, str]]:
    region = (region or "US").strip().upper()[:2]
    limit = _clamp_limit(limit)
    invidious_results, invidious_errors = _yt_trending_from_invidious(region, limit)
    if invidious_results:
        return invidious_results

    results = []
    seen_urls = set()
    errors = invidious_errors

    for query in _yt_trending_queries(region):
        batch = search_yt_videos(query, sort_by="upload_date", limit=limit)
        if batch and "error" in batch[0]:
            errors.append(batch[0]["error"])
            continue
        for video in batch:
            url = video.get("url", "")
            if not url or url in seen_urls:
                continue
            video["source"] = f"scrapetube_search:{query}"
            video["region"] = region
            results.append(video)
            seen_urls.add(url)
            if len(results) >= limit:
                return results

    if results:
        return results
    detail = f" Dettaglio: {'; '.join(errors)}" if errors else ""
    return [{"error": f"Nessun video YouTube trending trovato tramite scraping.{detail}"}]

@mcp.tool()
def get_comments_yt(video_id: str, max_comments: int = 100) -> List[str]:
    """Estrae i commenti di YouTube tramite video ID senza usare API key."""
    try:
        d = YoutubeCommentDownloader()
        comments = []
        for c in d.get_comments_from_url(f"https://www.youtube.com/watch?v={video_id}"):
            comments.append(c["text"])
            if len(comments) >= max_comments:
                break
        return comments
    except Exception as e:
        return [f"Errore durante l'estrazione dei commenti: {str(e)}"]

@mcp.tool()
def search_yt_videos(query: str, sort_by: str = "view_count", limit: int = 10) -> List[Dict[str, str]]:
    """Cerca video YouTube per keyword usando scraping.
    sort_by può essere: 'relevance', 'upload_date', 'view_count', 'rating'."""
    try:
        videos = scrapetube.get_search(query, sort_by=sort_by, limit=_clamp_limit(limit))
        results = []
        for v in videos:
            title = v.get("title", {}).get("runs", [{}])[0].get("text", "Nessun Titolo")
            video_id = v.get("videoId", "")
            if not video_id:
                continue
            views = v.get("viewCountText", {}).get("simpleText", "0 visualizzazioni")
            published = v.get("publishedTimeText", {}).get("simpleText", "")
            results.append({
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "views": views,
                "published": published
            })
        return results
    except Exception as e:
        return [{"error": f"Errore: {str(e)}"}]

@mcp.tool()
def get_yt_trending_global(limit: int = 10) -> List[Dict[str, str]]:
    """Ottiene video YouTube in tendenza tramite endpoint gratuiti Invidious.
    Se le istanze pubbliche non rispondono, usa una ricerca scraping best effort."""
    return _yt_trending(region="US", limit=limit)

@mcp.tool()
def get_yt_trending_by_region(region_code: str = "IT", limit: int = 10) -> List[Dict[str, str]]:
    """Ottiene video YouTube in tendenza per paese ISO-2, ad esempio IT o US."""
    return _yt_trending(region=region_code, limit=limit)

@mcp.tool()
def get_yt_video_info(url: str) -> Optional[Dict[str, str]]:
    """Ottiene i metadati di un video YouTube dal suo URL tramite yt-dlp.  
    Include titolo, visualizzazioni, mi piace, descrizione, ecc."""
    opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            i = ydl.extract_info(url, download=False)
            return {
                "title": i.get("title", ""),
                "channel": i.get("uploader", ""),
                "description": i.get("description", ""),
                "views": f"{i.get('view_count', 0):,}",
                "likes": f"{i.get('like_count', 0):,}" if i.get('like_count') else "N/D",
                "upload_date": i.get("upload_date", ""),
                "duration": f"{i.get('duration', 0)} secondi",
                "thumbnail": i.get("thumbnail", ""),
                "url": i.get("webpage_url", url),
            }
    except Exception: 
        return None

@mcp.tool()
def tiktok_trending_global() -> str:
    """Recupera e riassume i video in tendenza su TikTok con statistiche e hashtag."""
    if not TIKTOK_HEADERS["x-rapidapi-key"]:
        return "Manca la chiave API di TikTok."
        
    try:
        res = requests.get("https://tiktok-scraper7.p.rapidapi.com/feed/list", headers=TIKTOK_HEADERS, params={"region": "US", "count": 10})
        if res.status_code != 200:
            return f"Errore HTTP: {res.status_code}"
            
        data = res.json()
        if data.get("code") != 0:
            return "Risposta non valida o fallita dall'API di TikTok."

        videos = data.get("data", [])
        if not videos:
            return "Nessun video in tendenza trovato."

        return _format_tiktok_videos(videos)

    except Exception as e:
        return f"Errore: {str(e)}"

@mcp.tool()
def get_this_weeks_reels_trends() -> List[Dict[str, str]]:
    """Estrae i trend di Instagram Reels di questa settimana.  
    Restituisce una lista con nome del trend, data e statistiche."""
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
        return [{"error": f"Errore: {str(e)}"}]

@mcp.tool()
def search_tiktok_by_keyword(query: str, limit: int = 10) -> str:
    """Cerca video TikTok per keyword (es. 'viaggi over 50'). Restituisce le statistiche dei video."""
    if not TIKTOK_HEADERS["x-rapidapi-key"]:
        return "Manca la chiave API di TikTok."
        
    try:
        res = requests.get("https://tiktok-scraper7.p.rapidapi.com/feed/search", headers=TIKTOK_HEADERS, params={"keywords": query, "count": limit})
        if res.status_code != 200:
            return f"Errore API o endpoint non supportato (Status: {res.status_code}). Per query specifiche si consiglia l'integrazione Apify come da guida."
        data = res.json()
        videos = data.get("data", {}).get("videos", [])
        if not videos:
            return "Nessun video trovato."
        
        return _format_tiktok_videos(videos)
    except Exception as e:
        return f"Errore: {str(e)}"

@mcp.tool()
def search_tiktok_by_hashtag(hashtag: str, limit: int = 10) -> str:
    """Cerca video TikTok per hashtag (es. 'turismoitalia')."""
    hashtag = hashtag if hashtag.startswith("#") else f"#{hashtag}"
    return search_tiktok_by_keyword(hashtag, limit)

def _format_tiktok_videos(videos: list) -> str:
    summary = [f"Trovati {len(videos)} video TikTok.\n"]
    for i, video in enumerate(videos):
        author_name = video.get("author", {}).get("nickname", "N/D")
        author_id = video.get("author", {}).get("unique_id", "")
        desc = video.get("title", "Nessuna descrizione")
        video_id = video.get("video_id", "")
        
        link = f"https://www.tiktok.com/@{author_id}/video/{video_id}" if video_id and author_id else "Nessun link"
        
        plays = video.get("play_count", 0)
        likes = video.get("digg_count", 0)
        comments = video.get("comment_count", 0)
        shares = video.get("share_count", 0)
        saves = video.get("collect_count", 0) or video.get("download_count", 0)
        engagement = ((likes + comments + shares + saves) / plays) * 100 if plays > 0 else 0.0

        summary.append(f"--- Video {i} ---\n"
                       f"Autore: {author_name}\n"
                       f"Descrizione: {desc}\n"
                       f"Link: {link}\n"
                       f"Visualizzazioni: {plays:,} | Mi piace: {likes:,} | Commenti: {comments:,} | Engagement: {engagement:.2f}%\n"
                       f"{'=' * 40}")
    return "\n".join(summary)

def _first_value(item: Dict[str, Any], keys: List[str], default: Any = "") -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default

def _is_instagram_video(item: Dict[str, Any]) -> bool:
    content_type = str(_first_value(item, ["type", "productType", "mediaType"], "")).lower()
    url = str(item.get("url", "")).lower()
    return (
        "video" in content_type
        or "reel" in content_type
        or "/reel/" in url
        or bool(_first_value(item, ["videoUrl", "videoPlayCount", "videoViewCount", "videoDuration", "isVideo"], None))
    )

def _format_instagram_reels(items: List[Dict[str, Any]], hashtag: str, source: str = "instagram") -> str:
    summary = [f"Trovati {len(items)} Reel/video di Instagram per #{hashtag} ({source}).\n"]
    for i, video in enumerate(items, start=1):
        url = _first_value(video, ["url", "inputUrl"], "Nessun link")
        desc = str(_first_value(video, ["caption", "text", "alt", "description"], "Nessuna descrizione")).replace("\n", " ")[:180]
        author = _first_value(video, ["ownerUsername", "username", "ownerFullName"], "N/D")
        views = int(_first_value(video, ["videoViewCount", "videoPlayCount", "playCount", "playsCount"], 0) or 0)
        likes = int(_first_value(video, ["likesCount", "likeCount", "likes"], 0) or 0)
        comments = int(_first_value(video, ["commentsCount", "commentCount", "comments"], 0) or 0)
        timestamp = _first_value(video, ["timestamp", "takenAt", "createdAt"], "")
        audio = _first_value(video, ["musicInfo", "audioTitle", "songName"], "")
        eng = ((likes + comments) / views) * 100 if views > 0 else 0.0

        summary.append(f"--- Reel {i} ---\n"
                       f"Autore: {author}\n"
                       f"Link: {url}\n"
                       f"Didascalia: {desc}{'...' if len(desc) == 180 else ''}\n"
                       f"Audio: {audio if audio else 'N/D'}\n"
                       f"Data: {timestamp if timestamp else 'N/D'}\n"
                       f"Visualizzazioni: {views:,} | Mi piace: {likes:,} | Commenti: {comments:,} | Engagement: {eng:.2f}%\n"
                       f"{'=' * 40}")
    return "\n".join(summary)

def _search_instagram_reels_with_apify(clean_hashtag: str, limit: int) -> str:
    apify_token = os.getenv("APIFY_TOKEN") or os.getenv("apify")
    if not apify_token:
        return ""

    try:
        from apify_client import ApifyClient
        client = ApifyClient(apify_token)

        # L'actor ufficiale più recente supporta resultsType="reels".
        actor_id = os.getenv("APIFY_INSTAGRAM_ACTOR", "apify/instagram-api-scraper")
        run_input = {
            "directUrls": [f"https://www.instagram.com/explore/tags/{clean_hashtag}/"],
            "resultsType": "reels",
            "resultsLimit": limit,
            "searchType": "hashtag",
            "searchLimit": 1
        }
        
        run = client.actor(actor_id).call(run_input=run_input)
        
        items = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
        videos = [item for item in items if _is_instagram_video(item)]
                
        if videos:
            return _format_instagram_reels(videos[:limit], clean_hashtag, source="Apify")
            
        if items:
            found_types = sorted({str(_first_value(item, ["type", "productType", "mediaType"], "sconosciuto")) for item in items})
            return f"Apify ha restituito {len(items)} contenuti per #{clean_hashtag}, ma nessun Reel/video riconoscibile. Tipi trovati: {', '.join(found_types)}."
        return f"Nessun reel trovato per #{clean_hashtag}. Prova un hashtag più ampio o verifica i log della run Apify {run.get('id', '')}."
        
    except ImportError:
        return "Errore: La libreria 'apify-client' non è installata. Esegui 'pip install apify-client'."
    except Exception as e:
        return f"Errore durante l'esecuzione di Apify: {str(e)}"

def _search_instagram_reels_with_instaloader(clean_hashtag: str, limit: int) -> str:
    try:
        import instaloader
    except ImportError:
        return "Fallback Instaloader non disponibile: installa 'instaloader'."

    try:
        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )

        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        if username and password:
            loader.login(username, password)

        hashtag = instaloader.Hashtag.from_name(loader.context, clean_hashtag)
        reels = []
        for post in hashtag.get_posts():
            if not post.is_video:
                continue
            shortcode = post.shortcode
            reels.append({
                "url": f"https://www.instagram.com/reel/{shortcode}/" if shortcode else post.url,
                "caption": post.caption or "",
                "ownerUsername": post.owner_username,
                "videoViewCount": post.video_view_count or 0,
                "likesCount": post.likes or 0,
                "commentsCount": post.comments or 0,
                "timestamp": post.date_utc.isoformat() if post.date_utc else "",
                "type": post.typename,
            })
            if len(reels) >= limit:
                break

        if reels:
            return _format_instagram_reels(reels, clean_hashtag, source="Instaloader fallback")
        return f"Nessun video/Reel trovato per #{clean_hashtag} con Instaloader."
    except Exception as e:
        return f"Errore fallback Instaloader: {str(e)}"

@mcp.tool()
def search_instagram_reels_by_hashtag(hashtag: str, limit: int = 10) -> str:
    """Ricerca Instagram Reels per hashtag.
    Usa Apify se APIFY_TOKEN è configurato; altrimenti prova il fallback gratuito Instaloader."""
    clean_hashtag = hashtag.replace("#", "").strip()
    limit = _clamp_limit(limit, maximum=100)
    if not clean_hashtag:
        return "Inserisci un hashtag valido."

    apify_result = _search_instagram_reels_with_apify(clean_hashtag, limit)
    if apify_result.startswith("Trovati "):
        return apify_result

    fallback_result = _search_instagram_reels_with_instaloader(clean_hashtag, limit)
    if apify_result:
        return f"{fallback_result}\n\nNota Apify: {apify_result}"
    return fallback_result

@mcp.tool()
def search_yt_shorts_by_keyword(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """Cerca YouTube Shorts per keyword usando scraping."""
    return search_yt_videos(query=f"{query} #shorts", sort_by="relevance", limit=limit)

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
