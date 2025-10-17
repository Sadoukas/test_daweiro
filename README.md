# TikTok Scraper - Dockerized

A TikTok scraper developed in Python using Playwright to extract video data from a TikTok account and export it to CSV format. The application is fully containerized with Docker.

## Objective

Develop a scraper that retrieves video information from a TikTok account and stores it in a CSV file. The application must be containerized with Docker.

**Target account:** @hugodecrypte

## Extracted Data

For each video from a TikTok account:
- **Video URL**
- **Description**
- **Thumbnail**
- **View count**
- **Like count**
- **Comment count**

## Installation and Usage

### Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

### Quick Installation

```bash
# Clone the repository
git clone https://github.com/Sadoukas/test_daweiro.git
cd test_daweiro

# Run the scraper with Docker Compose
docker-compose up --build
```

### Usage with Launch Script

```bash
# Build Docker image
./run.sh build

# Run scraper (default account: hugodecrypte)
./run.sh run

# Run with custom parameters
./run.sh run --username hugodecrypte --max-videos 100

# Run in visible mode (for debugging)
./run.sh run --visible

# Interactive mode for development
./run.sh run-interactive

# View logs
./run.sh logs

# Clean up Docker resources
./run.sh clean
```

### Manual Docker Usage

```bash
# Build image
docker build -t tiktok-scraper .

# Run container
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e TIKTOK_USERNAME=hugodecrypte \
  -e MAX_VIDEOS=50 \
  tiktok-scraper
```

## Configuration

### Environment Variables

Copy `config.env.example` to `.env` and modify the values:

```bash
cp config.env.example .env
```

**Main variables:**
- `TIKTOK_USERNAME`: TikTok username to scrape
- `MAX_VIDEOS`: Maximum number of videos to scrape
- `HEADLESS_MODE`: Headless mode (true/false)
- `SCROLL_DELAY`: Delay between scrolls (seconds)
- `MAX_RETRIES`: Maximum number of retry attempts on error

### Docker Compose Configuration

Modify `docker-compose.yml` to adjust:
- Resource limits (CPU/RAM)
- Environment variables
- Mounted volumes

## Project Structure

```
daweiro/
├── src/
│   ├── scraper.py          # Main scraping script
│   ├── csv_exporter.py     # CSV data management
│   └── utils.py           # Utilities and configuration
├── data/                  # Directory for CSV files (Docker volume)
├── logs/                  # Directory for logs (Docker volume)
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker orchestration
├── run.sh               # Launch script
├── config.env.example   # Default configuration
└── README.md            # This documentation
```

## Technical Features

### Intelligent Scraping
- **Playwright** for modern web navigation
- **Progressive scrolling** to load all videos
- **Multiple selectors** to adapt to TikTok changes
- **Rate limiting** to avoid detection

### Error Handling
- **Retry logic** with exponential backoff
- **Detailed logs** with colors
- **Configurable timeouts**
- **Fallback** in case of video failure

### Data Export
- **Standard CSV format**
- **Data validation** before export
- **Scraping statistics**
- **File persistence** outside the container

### Containerization
- **Optimized image** with Python 3.11
- **Persistent volumes** for data
- **Non-root user** for security
- **Configurable resource limits**

### Logs and Debugging

Logs are saved in the `logs/` folder:
```bash
# View logs in real-time
tail -f logs/scraper_*.log

# View container logs
docker logs tiktok-scraper
```