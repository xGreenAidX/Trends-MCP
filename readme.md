# 🚀 Whats Trending On Social Media

This MCP fetches trending data from platforms like **YouTube**, **TikTok**, and **Instagram Reels** using various scraping and API techniques. It's designed to run under FastMCP and exposes tools that can be consumed via a local CLI or server.

![Animation](ezgif-19a49fe4da0940.gif)


---

## 🛠️ Dependencies

Make sure the following Python packages are installed:

- `beautifulsoup4`
- `youtube-comment-downloader`
- `yt_dlp`
- `requests`
- `fastmcp`
- `apify-client`

---

## 🚀 Available Tools

### 🔹 `get_comments_yt()`

Fetches YouTube comments for a given video ID.

---

### 🔹 `get_yt_trending_global()`

Fetches globally trending YouTube videos (default region: US).

---

### 🔹 `get_yt_trending_by_region()`

Fetches region-specific YouTube trending videos.

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

Placeholder tool for Instagram Reels search. Currently prompts the user to use Apify as no native open API is implemented.

---

### 🔹 `search_yt_shorts_by_keyword()`

Searches YouTube Shorts by keyword using `yt_dlp` and returns metadata.

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
YouTube Trending Feed: https://www.youtube.com/feed/trending

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
        "requests",
        "mcp",
        "run",
        "src/server.py"
      ],
      "env":{
        "tiktok": "<tiktok token goes here>",
        "apify": "<apify token goes here>"
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


