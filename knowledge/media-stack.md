# Media & Download Stack Knowledge Base

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Prowlarr (Indexer Manager)                  │
│                         :9696                                    │
└───────┬─────────┬─────────┬─────────┬─────────┬─────────────────┘
        │         │         │         │         │
        ▼         ▼         ▼         ▼         ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Sonarr  │ │ Radarr  │ │ Lidarr  │ │ Readarr │ │Whisparr │
│  :8989  │ │  :7878  │ │  :8686  │ │  :8787  │ │  :6969  │
│   TV    │ │ Movies  │ │  Music  │ │  Books  │ │  Adult  │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │           │
     └───────────┴───────────┴───────────┴───────────┘
                             │
                             ▼
              ┌───────────────────────────┐
              │         Gluetun           │
              │      (VPN Gateway)        │
              └─────────────┬─────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
       ┌─────────────┐           ┌─────────────┐
       │ qBittorrent │           │   SABnzbd   │
       │    :8082    │           │    :8085    │
       │   Torrents  │           │   Usenet    │
       └─────────────┘           └─────────────┘
```

## *Arr Stack

### Prowlarr (Indexer Manager)
- **Port:** 9696
- **Purpose:** Centralized indexer management for all *arr apps
- **Features:**
  - Manages torrent and usenet indexers
  - Syncs to all other *arr apps automatically
  - Search across all indexers at once

```yaml
# docker-compose.yml
prowlarr:
  image: lscr.io/linuxserver/prowlarr:latest
  container_name: prowlarr
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/prowlarr:/config
  ports:
    - 9696:9696
  restart: unless-stopped
```

### Sonarr (TV Shows)
- **Port:** 8989
- **Purpose:** TV show management and automation

```yaml
sonarr:
  image: lscr.io/linuxserver/sonarr:latest
  container_name: sonarr
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/sonarr:/config
    - /mnt/user/media/tv:/tv
    - /mnt/user/downloads:/downloads
  ports:
    - 8989:8989
  restart: unless-stopped
```

### Radarr (Movies)
- **Port:** 7878
- **Purpose:** Movie management and automation

```yaml
radarr:
  image: lscr.io/linuxserver/radarr:latest
  container_name: radarr
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/radarr:/config
    - /mnt/user/media/movies:/movies
    - /mnt/user/downloads:/downloads
  ports:
    - 7878:7878
  restart: unless-stopped
```

### Lidarr (Music)
- **Port:** 8686
- **Purpose:** Music library management

```yaml
lidarr:
  image: lscr.io/linuxserver/lidarr:latest
  container_name: lidarr
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/lidarr:/config
    - /mnt/user/media/music:/music
    - /mnt/user/downloads:/downloads
  ports:
    - 8686:8686
  restart: unless-stopped
```

### Readarr (Books/Audiobooks)
- **Port:** 8787
- **Purpose:** Book and audiobook management

```yaml
readarr:
  image: lscr.io/linuxserver/readarr:develop
  container_name: readarr
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/readarr:/config
    - /mnt/user/media/books:/books
    - /mnt/user/downloads:/downloads
  ports:
    - 8787:8787
  restart: unless-stopped
```

### Bazarr (Subtitles)
- **Port:** 6767
- **Purpose:** Automated subtitle downloads

```yaml
bazarr:
  image: lscr.io/linuxserver/bazarr:latest
  container_name: bazarr
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/bazarr:/config
    - /mnt/user/media/movies:/movies
    - /mnt/user/media/tv:/tv
  ports:
    - 6767:6767
  restart: unless-stopped
```

### Whisparr (Adult Content)
- **Port:** 6969
- **Purpose:** Adult content automation (Sonarr fork)
- **Note:** Fork specifically for adult content with appropriate metadata scrapers

```yaml
whisparr:
  image: ghcr.io/hotio/whisparr:latest
  container_name: whisparr
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/whisparr:/config
    - /mnt/user/media/adult:/adult
    - /mnt/user/downloads:/downloads
  ports:
    - 6969:6969
  restart: unless-stopped
```

### Stash (Adult Content Manager)
- **Port:** 9999
- **Status:** Already running
- **Purpose:** Organize, tag, browse adult content library

## VPN & Download Clients

### Gluetun (VPN Gateway)
All download traffic routes through Gluetun for privacy.

```yaml
gluetun:
  image: qmcgaw/gluetun:latest
  container_name: gluetun
  cap_add:
    - NET_ADMIN
  devices:
    - /dev/net/tun:/dev/net/tun
  environment:
    - VPN_SERVICE_PROVIDER=mullvad  # or your provider
    - VPN_TYPE=wireguard
    - WIREGUARD_PRIVATE_KEY=${WIREGUARD_KEY}
    - WIREGUARD_ADDRESSES=${WIREGUARD_ADDRESS}
    - SERVER_COUNTRIES=USA
  ports:
    # qBittorrent
    - 8082:8082
    - 6881:6881
    - 6881:6881/udp
    # SABnzbd
    - 8085:8085
  restart: unless-stopped
```

### qBittorrent (Torrents)
```yaml
qbittorrent:
  image: lscr.io/linuxserver/qbittorrent:latest
  container_name: qbittorrent
  network_mode: "service:gluetun"  # Route through VPN
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
    - WEBUI_PORT=8082
  volumes:
    - /mnt/user/appdata/download-stack/qbittorrent:/config
    - /mnt/user/downloads:/downloads
  depends_on:
    - gluetun
  restart: unless-stopped
```

### SABnzbd (Usenet)
```yaml
sabnzbd:
  image: lscr.io/linuxserver/sabnzbd:latest
  container_name: sabnzbd
  network_mode: "service:gluetun"  # Route through VPN
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Chicago
  volumes:
    - /mnt/user/appdata/download-stack/sabnzbd:/config
    - /mnt/user/downloads:/downloads
  depends_on:
    - gluetun
  restart: unless-stopped
```

## Web Crawlers & Scrapers

### Firecrawl (URL → Markdown)
- **Port:** 3002
- **Purpose:** Convert web pages to clean markdown for RAG
- **Best for:** Single URL processing, clean extraction

```yaml
firecrawl:
  image: mendableai/firecrawl:latest
  container_name: firecrawl
  ports:
    - 3002:3002
  environment:
    - FIRECRAWL_API_KEY=${FIRECRAWL_KEY}
  restart: unless-stopped
```

### Crawl4AI (LLM-Optimized)
- **Purpose:** Async crawling optimized for LLM consumption
- **Features:**
  - Handles JavaScript-heavy sites
  - Extracts structured data
  - Async for speed
  - LLM-friendly output

```bash
# Install
pip install crawl4ai

# Usage
from crawl4ai import WebCrawler

crawler = WebCrawler()
result = crawler.run(url="https://example.com")
print(result.markdown)
```

### gallery-dl (Image Sites)
- **Purpose:** Download images from 100+ sites
- **Supports:** DeviantArt, Pixiv, Twitter, Reddit, adult sites, etc.

```bash
# Install
pip install gallery-dl

# Usage
gallery-dl "https://twitter.com/user/status/123"
gallery-dl "https://www.pixiv.net/en/artworks/12345"

# Config (~/.config/gallery-dl/config.json)
{
  "extractor": {
    "base-directory": "/mnt/user/downloads/gallery-dl",
    "twitter": {
      "cookies": "~/.config/gallery-dl/twitter-cookies.txt"
    }
  }
}
```

### yt-dlp (Video Downloader)
- **Purpose:** Download videos from YouTube, adult sites, etc.
- **Supports:** 1000+ sites

```bash
# Install
pip install yt-dlp

# Usage
yt-dlp "https://youtube.com/watch?v=xxx"
yt-dlp -f bestvideo+bestaudio "https://..."

# Config (~/.config/yt-dlp/config)
-o "/mnt/user/downloads/yt-dlp/%(title)s.%(ext)s"
--embed-thumbnail
--embed-metadata
```

### trafilatura (Article Extraction)
- **Purpose:** Fast article/text extraction
- **Best for:** News sites, blogs

```python
from trafilatura import fetch_url, extract

url = "https://example.com/article"
downloaded = fetch_url(url)
text = extract(downloaded)
```

### Scrapy (Industrial Scraping)
- **Purpose:** Large-scale web scraping
- **Best for:** Complex crawling jobs

```python
import scrapy

class MySpider(scrapy.Spider):
    name = 'myspider'
    start_urls = ['https://example.com']
    
    def parse(self, response):
        yield {
            'title': response.css('title::text').get(),
            'content': response.css('article::text').getall()
        }
```

## Content Acquisition Pipeline

### RAG Ingestion Flow
```
Source → Crawler → Markdown → Chunker → Embeddings → Qdrant
           │
           ├── Firecrawl (clean articles)
           ├── Crawl4AI (complex sites)
           ├── trafilatura (fast extraction)
           └── gallery-dl (images → descriptions)
```

### RSS → Knowledge Pipeline (n8n)
```
Miniflux (RSS) → n8n trigger → Firecrawl → Chunk → Embed → Qdrant
                      │
                      └── LLM summary → Daily digest email
```

## Media Server Stack

### Plex
- **Port:** 32400
- **Status:** Already running
- **Libraries:** Movies, TV, Music

### Immich (Photo Management)
- **Port:** 2283
- **Purpose:** Google Photos replacement

```yaml
immich:
  image: ghcr.io/immich-app/immich-server:release
  container_name: immich
  volumes:
    - /mnt/user/photos:/usr/src/app/upload
  environment:
    - DB_HOSTNAME=immich_postgres
    - REDIS_HOSTNAME=immich_redis
  ports:
    - 2283:3001
  depends_on:
    - immich_redis
    - immich_postgres
  restart: unless-stopped
```

## Directory Structure

```
/mnt/user/
├── media/
│   ├── movies/           # Radarr managed
│   ├── tv/               # Sonarr managed
│   ├── music/            # Lidarr managed
│   ├── books/            # Readarr managed
│   ├── adult/            # Whisparr managed
│   └── stash/            # Stash library
├── downloads/
│   ├── complete/         # Finished downloads
│   ├── incomplete/       # In-progress
│   ├── gallery-dl/       # Image downloads
│   └── yt-dlp/           # Video downloads
└── photos/               # Immich library
```

## Setup Checklist

### *Arr Apps
1. [ ] Deploy Prowlarr first
2. [ ] Add indexers to Prowlarr
3. [ ] Deploy other *arr apps
4. [ ] Sync Prowlarr to each app
5. [ ] Configure download clients (qBit/SABnzbd)
6. [ ] Set up root folders for each media type
7. [ ] Import existing libraries

### VPN
1. [ ] Get VPN credentials (Mullvad recommended)
2. [ ] Configure Gluetun with WireGuard
3. [ ] Test VPN: `docker exec gluetun curl ifconfig.me`
4. [ ] Route download clients through Gluetun

### Crawlers
1. [ ] Install gallery-dl and yt-dlp
2. [ ] Configure authentication for sites that need it
3. [ ] Set up download directories
4. [ ] Test each crawler
