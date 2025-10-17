"""
Utility functions for TikTok scraper
Handles logging, configuration, error handling, and common operations
"""

import os
import logging
import asyncio
import random
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()


class Logger:
    """Custom logger with colored output and file logging"""
    
    def __init__(self, name: str = "tiktok_scraper"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(
            f"logs/scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        """Log info message with green color"""
        self.logger.info(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
    
    def warning(self, message: str):
        """Log warning message with yellow color"""
        self.logger.warning(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
    
    def error(self, message: str):
        """Log error message with red color"""
        self.logger.error(f"{Fore.RED}{message}{Style.RESET_ALL}")
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def success(self, message: str):
        """Log success message with bright green color"""
        self.logger.info(f"{Fore.GREEN}{Style.BRIGHT}{message}{Style.RESET_ALL}")


class Config:
    """Configuration manager for the scraper"""
    
    def __init__(self):
        self.tiktok_username = os.getenv("TIKTOK_USERNAME", "hugodecrypte")
        self.max_videos = int(os.getenv("MAX_VIDEOS", "100"))
        self.scroll_delay = int(os.getenv("SCROLL_DELAY", "3"))
        self.extraction_delay = int(os.getenv("EXTRACTION_DELAY", "1"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "5"))
        
        # Timeouts
        self.page_load_timeout = int(os.getenv("PAGE_LOAD_TIMEOUT", "30")) * 1000
        self.element_wait_timeout = int(os.getenv("ELEMENT_WAIT_TIMEOUT", "10")) * 1000
        self.scroll_timeout = int(os.getenv("SCROLL_TIMEOUT", "5")) * 1000
        
        # Output
        self.output_dir = os.getenv("OUTPUT_DIR", "data")
        self.csv_filename = os.getenv("CSV_FILENAME", "tiktok_videos.csv")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Browser
        self.headless_mode = os.getenv("HEADLESS_MODE", "true").lower() == "true"
        self.browser_type = os.getenv("BROWSER_TYPE", "chromium")
        self.window_width = int(os.getenv("WINDOW_WIDTH", "1920"))
        self.window_height = int(os.getenv("WINDOW_HEIGHT", "1080"))
        
        # Rate limiting
        self.min_delay = int(os.getenv("MIN_DELAY_BETWEEN_ACTIONS", "2"))
        self.max_delay = int(os.getenv("MAX_DELAY_BETWEEN_ACTIONS", "5"))
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)


class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
        
        raise last_exception


class RateLimiter:
    """Handles rate limiting between actions"""
    
    def __init__(self, min_delay: int = 2, max_delay: int = 5):
        self.min_delay = min_delay
        self.max_delay = max_delay
    
    async def wait(self):
        """Wait for a random delay between min and max delay"""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)


def clean_text(text: str) -> str:
    """Clean and normalize text data"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = " ".join(text.split())
    
    # Remove emojis and special characters if needed
    # text = text.encode('ascii', 'ignore').decode('ascii')
    
    return text.strip()


def format_number(text: str) -> int:
    """Convert TikTok number format (1.2K, 1.5M) to integer"""
    if not text:
        return 0
    
    text = text.upper().replace(",", "").replace(" ", "")
    
    try:
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        elif "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        elif "B" in text:
            return int(float(text.replace("B", "")) * 1000000000)
        else:
            return int(text)
    except (ValueError, TypeError):
        return 0


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from TikTok URL"""
    if not url:
        return None
    
    try:
        # Handle different TikTok URL formats
        if "/video/" in url:
            return url.split("/video/")[1].split("?")[0]
        elif "tiktok.com" in url and "/" in url:
            parts = url.split("/")
            for i, part in enumerate(parts):
                if part.isdigit() and len(part) > 10:
                    return part
    except Exception:
        pass
    
    return None


def get_tiktok_profile_url(username: str) -> str:
    """Generate TikTok profile URL"""
    username = username.replace("@", "")
    return f"https://www.tiktok.com/@{username}"


# Global instances
logger = Logger()
config = Config()
retry_handler = RetryHandler(config.max_retries)
rate_limiter = RateLimiter(config.min_delay, config.max_delay)


def log_config():
    """Log current configuration"""
    logger.info("=== Configuration ===")
    logger.info(f"Target account: @{config.tiktok_username}")
    logger.info(f"Max videos: {config.max_videos}")
    logger.info(f"Headless mode: {config.headless_mode}")
    logger.info(f"Output directory: {config.output_dir}")
    logger.info(f"CSV filename: {config.csv_filename}")
    logger.info("====================")
