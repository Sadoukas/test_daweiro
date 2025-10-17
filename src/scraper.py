"""
Main TikTok Scraper using Playwright
Scrapes video data from TikTok profiles and exports to CSV
"""

import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from utils import (
    logger, config, retry_handler, rate_limiter, 
    get_tiktok_profile_url, log_config
)
from csv_exporter import CSVExporter


class TikTokScraper:
    """Main TikTok scraper class using Playwright"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.csv_exporter = CSVExporter()
        self.scraped_videos: List[str] = []  # Track scraped video URLs
        
        logger.info("TikTok Scraper initialized")
    
    async def start_browser(self):
        """Start Playwright browser with configuration"""
        try:
            playwright = await async_playwright().start()
            
            # Browser launch options
            browser_options = {
                'headless': config.headless_mode,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            }
            
            # Launch browser
            if config.browser_type == 'chromium':
                self.browser = await playwright.chromium.launch(**browser_options)
            elif config.browser_type == 'firefox':
                self.browser = await playwright.firefox.launch(**browser_options)
            else:
                self.browser = await playwright.webkit.launch(**browser_options)
            
            # Create context with realistic settings
            self.context = await self.browser.new_context(
                viewport={'width': config.window_width, 'height': config.window_height},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='fr-FR',
                timezone_id='Europe/Paris'
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set timeouts
            self.page.set_default_timeout(config.page_load_timeout)
            self.page.set_default_navigation_timeout(config.page_load_timeout)
            
            logger.success("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            raise
    
    async def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    async def navigate_to_profile(self, username: str) -> bool:
        """Navigate to TikTok profile"""
        try:
            profile_url = get_tiktok_profile_url(username)
            logger.info(f"Navigating to profile: {profile_url}")
            
            await self.page.goto(profile_url, wait_until='networkidle')
            await asyncio.sleep(2)  # Wait for page to stabilize
            
            # Check if profile exists
            if "User not found" in await self.page.content():
                logger.error(f"Profile @{username} not found")
                return False
            
            logger.success(f"Successfully navigated to @{username}")
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to profile: {str(e)}")
            return False
    
    async def scroll_and_load_videos(self) -> int:
        """Scroll through profile to load all videos"""
        try:
            logger.info("Starting to scroll and load videos...")
            
            videos_loaded = 0
            no_new_videos_count = 0
            max_no_new_videos = 3
            
            while videos_loaded < config.max_videos and no_new_videos_count < max_no_new_videos:
                # Get current video count
                initial_count = len(await self.get_visible_video_elements())
                
                # Scroll down
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(config.scroll_delay)
                
                # Wait for new content to load
                await self.page.wait_for_timeout(2000)
                
                # Check if new videos were loaded
                final_count = len(await self.get_visible_video_elements())
                
                if final_count > initial_count:
                    videos_loaded = final_count
                    no_new_videos_count = 0
                    logger.info(f"Loaded {videos_loaded} videos so far...")
                else:
                    no_new_videos_count += 1
                    logger.debug(f"No new videos loaded (attempt {no_new_videos_count})")
                
                # Rate limiting
                await rate_limiter.wait()
            
            logger.success(f"Finished loading videos. Total: {videos_loaded}")
            return videos_loaded
            
        except Exception as e:
            logger.error(f"Error scrolling and loading videos: {str(e)}")
            return 0
    
    async def get_visible_video_elements(self) -> List[Any]:
        """Get all visible video elements on the page"""
        try:
            # Multiple selectors to try (TikTok changes frequently)
            selectors = [
                '[data-e2e="user-post-item"]',
                '[data-e2e="user-post-item-desc"]',
                '.tiktok-1g04lal-DivItemContainer',
                '[data-e2e="video-feed-item"]',
                'div[class*="DivItemContainer"]',
                # Nouveaux sélecteurs pour la grille
                'div[class*="DivItemContainer"]',
                'div[data-e2e="user-post-item"]'
            ]
            
            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    logger.debug(f"Found {len(elements)} video elements with selector: {selector}")
                    return elements
            
            logger.warning("No video elements found with any selector")
            return []
            
        except Exception as e:
            logger.error(f"Error getting video elements: {str(e)}")
            return []
    
    async def extract_video_data(self, video_element: Any) -> Optional[Dict[str, Any]]:
        """Extract data from a single video element (grid view only)"""
        try:
            video_data = {}
            
            # Extract video URL
            video_url = await self.extract_video_url(video_element)
            if not video_url:
                return None
            
            video_data['video_id'] = video_url.split('/')[-1]
            video_data['video_url'] = video_url
            
            # Extract views from grid (only available on profile page)
            views_count = await self.extract_views_from_grid(video_element)
            video_data['views_count'] = views_count
            
            # Extract thumbnail
            thumbnail = await self.extract_thumbnail(video_element)
            video_data['thumbnail_url'] = thumbnail
            
            # Set account username
            video_data['account_username'] = config.tiktok_username
            
            # Set timestamp
            video_data['scraped_at'] = datetime.now().isoformat()
            
            # Initialize other fields (will be filled when clicking on video)
            video_data['description'] = ""
            video_data['likes_count'] = "0"
            video_data['comments_count'] = "0"
            
            logger.debug(f"Added video data: {video_data['video_id']}")
            return video_data
            
        except Exception as e:
            logger.error(f"Error extracting video data: {str(e)}")
            return None
    
    async def extract_video_url(self, element: Any) -> Optional[str]:
        """Extract video URL from element"""
        try:
            # Try multiple selectors for video link
            link_selectors = [
                'a[href*="/video/"]',
                '[data-e2e="video-link"]',
                'a[href*="tiktok.com"]'
            ]
            
            for selector in link_selectors:
                link_element = await element.query_selector(selector)
                if link_element:
                    href = await link_element.get_attribute('href')
                    if href and '/video/' in href:
                        if href.startswith('/'):
                            return f"https://www.tiktok.com{href}"
                        return href
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting video URL: {str(e)}")
            return None
    
    async def extract_description(self, element: Any) -> str:
        """Extract video description"""
        try:
            desc_selectors = [
                '[data-e2e="browse-video-desc"]',
                '[data-e2e="video-desc"]',
                '.tiktok-1g04lal-DivItemContainer span',
                '[data-e2e="user-post-item-desc"]'
            ]
            
            for selector in desc_selectors:
                desc_element = await element.query_selector(selector)
                if desc_element:
                    text = await desc_element.inner_text()
                    if text and text.strip():
                        return text.strip()
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extracting description: {str(e)}")
            return ""
    
    async def extract_thumbnail(self, element: Any) -> str:
        """Extract thumbnail URL"""
        try:
            img_selectors = [
                'img[data-e2e="video-cover"]',
                'img[alt*="video"]',
                'img'
            ]
            
            for selector in img_selectors:
                img_element = await element.query_selector(selector)
                if img_element:
                    src = await img_element.get_attribute('src')
                    if src and ('tiktok' in src or 'amazonaws' in src):
                        return src
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extracting thumbnail: {str(e)}")
            return ""
    
    async def extract_views_from_grid(self, element: Any) -> str:
        """Extract view count"""
        try:
            # Essayer de trouver les vues dans le conteneur parent ou proche
            view_selectors = [
                '[data-e2e="video-views"]',
                '.video-count',
                'strong.video-count',
                '[data-e2e="like-count"]',
                'strong'
            ]
            
            # Chercher dans l'élément actuel
            for selector in view_selectors:
                view_element = await element.query_selector(selector)
                if view_element:
                    text = await view_element.inner_text()
                    if text and any(char.isdigit() for char in text):
                        return text.strip()
            
            # Chercher dans le conteneur parent
            parent = await element.query_selector('xpath=..')
            if parent:
                for selector in view_selectors:
                    view_element = await parent.query_selector(selector)
                    if view_element:
                        text = await view_element.inner_text()
                        if text and any(char.isdigit() for char in text):
                            return text.strip()
            
            return "0"
            
        except Exception as e:
            logger.debug(f"Error extracting views: {str(e)}")
            return "0"
    
    async def extract_likes(self, element: Any) -> str:
        """Extract like count"""
        try:
            like_selectors = [
                '[data-e2e="browse-like-count"]',
                '[data-e2e="like-count"]',
                '[data-e2e="video-views"]',
                'strong'
            ]
            
            for selector in like_selectors:
                like_element = await element.query_selector(selector)
                if like_element:
                    text = await like_element.inner_text()
                    if text and any(char.isdigit() for char in text):
                        return text.strip()
            
            return "0"
            
        except Exception as e:
            logger.debug(f"Error extracting likes: {str(e)}")
            return "0"
    
    async def extract_comments(self, element: Any) -> str:
        """Extract comment count"""
        try:
            comment_selectors = [
                '[data-e2e="browse-comment-count"]',
                '[data-e2e="comment-count"]',
                '[data-e2e="video-views"]',
                'strong'
            ]
            
            for selector in comment_selectors:
                comment_element = await element.query_selector(selector)
                if comment_element:
                    text = await comment_element.inner_text()
                    if text and any(char.isdigit() for char in text):
                        return text.strip()
            
            return "0"
            
        except Exception as e:
            logger.debug(f"Error extracting comments: {str(e)}")
            return "0"
    
    async def extract_data_from_individual_video(self, video_url: str) -> Dict[str, str]:
        """Click on video and extract description, likes, comments"""
        try:
            logger.debug(f"Extracting data from individual video: {video_url}")
            
            # Navigate to the video
            await self.page.goto(video_url, wait_until='networkidle')
            await asyncio.sleep(2)  # Wait for page to load
            
            # Extract description
            description = await self.extract_description_from_video()
            
            # Extract likes
            likes = await self.extract_likes_from_video()
            
            # Extract comments
            comments = await self.extract_comments_from_video()
            
            # Go back to profile
            await self.page.go_back()
            await asyncio.sleep(1)
            
            return {
                'description': description,
                'likes_count': likes,
                'comments_count': comments
            }
            
        except Exception as e:
            logger.error(f"Error extracting data from individual video: {str(e)}")
            return {
                'description': "",
                'likes_count': "0",
                'comments_count': "0"
            }
    
    async def extract_description_from_video(self) -> str:
        """Extract description from individual video page"""
        try:
            desc_selectors = [
                '[data-e2e="browse-video-desc"]',
                '[data-e2e="video-desc"]',
                '.tiktok-1g04lal-DivItemContainer span',
                '[data-e2e="user-post-item-desc"]'
            ]
            
            for selector in desc_selectors:
                desc_element = await self.page.query_selector(selector)
                if desc_element:
                    text = await desc_element.inner_text()
                    if text and text.strip():
                        return text.strip()
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extracting description from video: {str(e)}")
            return ""
    
    async def extract_likes_from_video(self) -> str:
        """Extract likes from individual video page"""
        try:
            like_selectors = [
                '[data-e2e="browse-like-count"]',
                '[data-e2e="like-count"]',
                '[data-e2e="video-views"]',
                'strong'
            ]
            
            for selector in like_selectors:
                like_element = await self.page.query_selector(selector)
                if like_element:
                    text = await like_element.inner_text()
                    if text and any(char.isdigit() for char in text):
                        return text.strip()
            
            return "0"
            
        except Exception as e:
            logger.debug(f"Error extracting likes from video: {str(e)}")
            return "0"
    
    async def extract_comments_from_video(self) -> str:
        """Extract comments from individual video page"""
        try:
            comment_selectors = [
                '[data-e2e="browse-comment-count"]',
                '[data-e2e="comment-count"]',
                '[data-e2e="video-views"]',
                'strong'
            ]
            
            for selector in comment_selectors:
                comment_element = await self.page.query_selector(selector)
                if comment_element:
                    text = await comment_element.inner_text()
                    if text and any(char.isdigit() for char in text):
                        return text.strip()
            
            return "0"
            
        except Exception as e:
            logger.debug(f"Error extracting comments from video: {str(e)}")
            return "0"
    
    async def scrape_profile(self, username: str) -> bool:
        """Main scraping method"""
        try:
            logger.info(f"Starting to scrape profile: @{username}")
            log_config()
            
            # Start browser
            await self.start_browser()
            
            # Navigate to profile
            if not await self.navigate_to_profile(username):
                return False
            
            # Load all videos
            total_videos = await self.scroll_and_load_videos()
            if total_videos == 0:
                logger.warning("No videos found on profile")
                return False
            
            # Extract data from all videos
            video_elements = await self.get_visible_video_elements()
            logger.info(f"Extracting data from {len(video_elements)} videos...")
            
            scraped_count = 0
            for i in range(config.max_videos):
                try:
                    # Re-get video elements after each navigation (DOM elements become stale)
                    current_video_elements = await self.get_visible_video_elements()
                    if i >= len(current_video_elements):
                        logger.warning(f"Not enough videos found. Requested: {config.max_videos}, Available: {len(current_video_elements)}")
                        break
                    
                    video_element = current_video_elements[i]
                    video_data = await self.extract_video_data(video_element)
                    
                    if video_data and video_data.get('video_url'):
                        # Check if already scraped
                        if video_data['video_url'] not in self.scraped_videos:
                            # Extract additional data by clicking on the video
                            additional_data = await self.extract_data_from_individual_video(video_data['video_url'])
                            
                            # Update video data with additional information
                            video_data['description'] = additional_data['description']
                            video_data['likes_count'] = additional_data['likes_count']
                            video_data['comments_count'] = additional_data['comments_count']
                            
                            self.csv_exporter.add_video_data(video_data)
                            self.scraped_videos.append(video_data['video_url'])
                            scraped_count += 1
                            
                            logger.debug(f"Scraped video {scraped_count}/{config.max_videos}")
                    
                    # Rate limiting between extractions
                    await asyncio.sleep(config.extraction_delay)
                    
                except Exception as e:
                    logger.error(f"Error processing video {i}: {str(e)}")
                    continue
            
            # Save to CSV
            if self.csv_exporter.data:
                self.csv_exporter.save_to_csv()
                
                # Print statistics
                stats = self.csv_exporter.get_stats()
                logger.success(f"Scraping completed! Scraped {stats['total_videos']} videos")
                logger.info(f"Total views: {stats['total_views']:,}")
                logger.info(f"Total likes: {stats['total_likes']:,}")
                logger.info(f"Total comments: {stats['total_comments']:,}")
                
                return True
            else:
                logger.error("No data was scraped")
                return False
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return False
        finally:
            await self.close_browser()


async def main():
    """Main function to run the scraper"""
    scraper = TikTokScraper()
    
    try:
        success = await scraper.scrape_profile(config.tiktok_username)
        if success:
            logger.success("Scraping completed successfully!")
        else:
            logger.error("Scraping failed!")
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
