# 🚀 Whats Trending On Social Media

This MCP fetches trending data from platforms like **YouTube**, **TikTok**, and **Instagram Reels** using various scraping and API techniques. It's designed to run under FastMCP and exposes tools that can be consumed via a local CLI or server.

![Animation](ezgif-19a49fe4da0940.gif)


---

## 🛠️ Dependencies

Make sure the following Python packages are installed:

- `beautifulsoup4`
- `youtube-comment-downloader`
- `yt_dlp`
- `scrapetube`
- `requests`
- `fastmcp`
- `apify-client`
- `instaloader`

---

## 🚀 Available Tools

### 🔹 `get_comments_yt()`

Fetches YouTube comments for a given video ID.

---

### 🔹 `get_yt_trending_global()`

Fetches trending YouTube videos (default region: US) using free Invidious public instances. If those instances are unavailable, it falls back to YouTube search scraping.

---

### 🔹 `get_yt_trending_by_region()`

Fetches region-specific YouTube trending videos using an ISO-2 region code such as `IT` or `US`. You can override public Invidious instances with `INVIDIOUS_INSTANCES`, comma-separated.

---

### 🔹 `get_yt_video_info()`

Returns detailed metadata about a YouTube video.

---

### 🔹 `tiktok_trending_global()`

Fetches trending TikTok videos via the RapidAPI and summarizes them.

---

### 🔹 `get_this_weeks_reels_trends()`

Scrapes weekly Instagram Reels trends from Later.com.

---

### 🔹 `search_tiktok_by_keyword()`

Searches TikTok videos by keyword using the RapidAPI and returns statistics.

---

### 🔹 `search_tiktok_by_hashtag()`

Searches TikTok videos by hashtag using the RapidAPI and returns statistics.

---

### 🔹 `search_instagram_reels_by_hashtag()`

Searches Instagram Reels by hashtag through Apify's Instagram API Scraper when `APIFY_TOKEN` is configured. If Apify is unavailable or returns no usable reels, it falls back to `instaloader`.
For the free fallback, optional `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` environment variables can improve reliability, but they are not required.

---

### 🔹 `search_yt_shorts_by_keyword()`

Searches YouTube Shorts by keyword using YouTube search scraping and returns metadata.

---

### 🔹 `rank_videos_by_engagement()`

Ranks a given list of videos based on their engagement rate `(likes + comments + shares + saves) / views`.

---

## 📁 File Structure

This module can be executed via CLI or server mode using `FastMCP`:

```bash
fastmcp run src/server.py
```


## 🌐 External Resources
YouTube Trending Source: Invidious `/api/v1/trending` public instances, with scraping fallback.

Instagram Reels Trends Source: https://later.com/blog/instagram-reels-trends/

TikTok RapidAPI: https://rapidapi.com/ponds4552/api/tiktok-best-experience

## 📌 MCP Config File

```bash
{
  "mcpServers": {
    "Whats Trending On Social Media": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "fastmcp",
        "--with",
        "youtube-comment-downloader",
        "--with",
        "yt_dlp",
        "--with",
        "beautifulsoup4",
        "--with",
        "scrapetube",
        "--with",
        "apify-client",
        "--with",
        "instaloader",
        "--with",
        "requests",
        "mcp",
        "run",
        "src/server.py"
      ],
      "env":{
        "tiktok": "<tiktok token goes here>",
        "APIFY_TOKEN": "<apify token goes here>"
    }
    }
  }
}

```
🧪 Run Locally
To run the server locally:

```bash
fastmcp run src/server.py
```
## 📎 Notes
YouTube comment extraction uses unofficial scraping and may break with YouTube changes.

TikTok API requires a valid RapidAPI key.

Instagram scraping is done by parsing Later.com's blog – may vary if structure changes.

## 🧑‍💻 Author
Trends-MCP by [Rugved Patil](https://github.com/rugvedp).


