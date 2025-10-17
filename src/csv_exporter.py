"""
CSV Data Management for TikTok Scraper
Handles data export, formatting, and CSV file operations
"""

import pandas as pd
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from utils import logger, config, clean_text, format_number


class CSVExporter:
    """Handles CSV export operations for TikTok data"""
    
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename or config.csv_filename
        self.filepath = os.path.join(config.output_dir, self.filename)
        self.data: List[Dict[str, Any]] = []
        
        # CSV columns
        self.columns = [
            'video_id',
            'video_url', 
            'description',
            'thumbnail_url',
            'views_count',
            'likes_count', 
            'comments_count',
            'scraped_at',
            'account_username'
        ]
        
        logger.info(f"CSV exporter initialized: {self.filepath}")
    
    def add_video_data(self, video_data: Dict[str, Any]) -> bool:
        """Add video data to the collection"""
        try:
            # Validate required fields
            if not video_data.get('video_url'):
                logger.warning("Skipping video: missing video_url")
                return False
            
            # Clean and format the data
            processed_data = self._process_video_data(video_data)
            
            # Add to collection
            self.data.append(processed_data)
            logger.debug(f"Added video data: {processed_data.get('video_id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding video data: {str(e)}")
            return False
    
    def _process_video_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean video data"""
        processed = {
            'video_id': self._extract_video_id(raw_data.get('video_url', '')),
            'video_url': raw_data.get('video_url', ''),
            'description': clean_text(raw_data.get('description', '')),
            'thumbnail_url': raw_data.get('thumbnail_url', ''),
            'views_count': format_number(raw_data.get('views_count', '0')),
            'likes_count': format_number(raw_data.get('likes_count', '0')),
            'comments_count': format_number(raw_data.get('comments_count', '0')),
            'scraped_at': datetime.now().isoformat(),
            'account_username': config.tiktok_username
        }
        
        return processed
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL"""
        if not url:
            return ""
        
        try:
            # Handle different TikTok URL formats
            if "/video/" in url:
                video_id = url.split("/video/")[1].split("?")[0]
                return video_id
            elif "tiktok.com" in url:
                # Try to extract from various URL patterns
                parts = url.split("/")
                for part in parts:
                    if part.isdigit() and len(part) > 10:
                        return part
        except Exception as e:
            logger.debug(f"Could not extract video ID from {url}: {str(e)}")
        
        return ""
    
    def save_to_csv(self, append: bool = False) -> bool:
        """Save data to CSV file"""
        try:
            if not self.data:
                logger.warning("No data to save")
                return False
            
            # Create directory if it doesn't exist
            os.makedirs(config.output_dir, exist_ok=True)
            
            # Determine file mode
            file_mode = 'a' if append and os.path.exists(self.filepath) else 'w'
            write_header = not (append and os.path.exists(self.filepath))
            
            # Write to CSV
            with open(self.filepath, file_mode, newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.columns)
                
                if write_header:
                    writer.writeheader()
                
                writer.writerows(self.data)
            
            logger.success(f"Saved {len(self.data)} videos to {self.filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving CSV: {str(e)}")
            return False
    
    def save_with_pandas(self, append: bool = False) -> bool:
        """Save data using pandas (alternative method)"""
        try:
            if not self.data:
                logger.warning("No data to save")
                return False
            
            # Create DataFrame
            df = pd.DataFrame(self.data)
            
            # Ensure all columns exist
            for col in self.columns:
                if col not in df.columns:
                    df[col] = ""
            
            # Reorder columns
            df = df[self.columns]
            
            # Create directory if it doesn't exist
            os.makedirs(config.output_dir, exist_ok=True)
            
            # Save to CSV
            if append and os.path.exists(self.filepath):
                df.to_csv(self.filepath, mode='a', header=False, index=False, encoding='utf-8')
            else:
                df.to_csv(self.filepath, index=False, encoding='utf-8')
            
            logger.success(f"Saved {len(self.data)} videos to {self.filepath} using pandas")
            return True
            
        except Exception as e:
            logger.error(f"Error saving CSV with pandas: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about collected data"""
        if not self.data:
            return {
                'total_videos': 0,
                'total_views': 0,
                'total_likes': 0,
                'total_comments': 0
            }
        
        total_views = sum(video.get('views_count', 0) for video in self.data)
        total_likes = sum(video.get('likes_count', 0) for video in self.data)
        total_comments = sum(video.get('comments_count', 0) for video in self.data)
        
        return {
            'total_videos': len(self.data),
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'avg_views': total_views // len(self.data) if self.data else 0,
            'avg_likes': total_likes // len(self.data) if self.data else 0,
            'avg_comments': total_comments // len(self.data) if self.data else 0
        }
    
    def clear_data(self):
        """Clear collected data"""
        self.data.clear()
        logger.info("Cleared collected data")
    
    def load_existing_data(self) -> bool:
        """Load existing CSV data if file exists"""
        try:
            if not os.path.exists(self.filepath):
                logger.info("No existing CSV file found")
                return True
            
            # Load existing data
            df = pd.read_csv(self.filepath)
            self.data = df.to_dict('records')
            
            logger.info(f"Loaded {len(self.data)} existing videos from {self.filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading existing data: {str(e)}")
            return False
    
    def get_file_info(self) -> Dict[str, Any]:
        """Get information about the CSV file"""
        if not os.path.exists(self.filepath):
            return {
                'exists': False,
                'size': 0,
                'modified': None
            }
        
        stat = os.stat(self.filepath)
        return {
            'exists': True,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'path': self.filepath
        }


def create_sample_data() -> List[Dict[str, Any]]:
    """Create sample data for testing"""
    return [
        {
            'video_url': 'https://www.tiktok.com/@hugodecrypte/video/1234567890123456789',
            'description': 'Sample video description',
            'thumbnail_url': 'https://example.com/thumbnail.jpg',
            'views_count': '1.2K',
            'likes_count': '150',
            'comments_count': '25'
        },
        {
            'video_url': 'https://www.tiktok.com/@hugodecrypte/video/9876543210987654321',
            'description': 'Another sample video',
            'thumbnail_url': 'https://example.com/thumbnail2.jpg',
            'views_count': '5.5M',
            'likes_count': '2.1K',
            'comments_count': '300'
        }
    ]


# Example usage
if __name__ == "__main__":
    # Test the CSV exporter
    exporter = CSVExporter("test_videos.csv")
    
    # Add sample data
    sample_data = create_sample_data()
    for video in sample_data:
        exporter.add_video_data(video)
    
    # Save to CSV
    exporter.save_to_csv()
    
    # Print stats
    stats = exporter.get_stats()
    print(f"Stats: {stats}")
    
    # Print file info
    file_info = exporter.get_file_info()
    print(f"File info: {file_info}")
