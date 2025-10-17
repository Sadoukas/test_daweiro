#!/bin/bash

# TikTok Scraper - Docker Run Script
# This script provides easy commands to run the TikTok scraper

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image"
    echo "  run         Run the scraper (default)"
    echo "  run-interactive  Run with interactive shell"
    echo "  logs        Show container logs"
    echo "  clean       Clean up containers and images"
    echo "  help        Show this help message"
    echo ""
    echo "Options:"
    echo "  --username USERNAME    TikTok username to scrape (default: hugodecrypte)"
    echo "  --max-videos NUMBER    Maximum videos to scrape (default: 3)"
    echo "  --headless            Run in headless mode (default)"
    echo "  --visible             Run with visible browser"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run --username hugodecrypte --max-videos 100"
    echo "  $0 run-interactive"
    echo "  $0 logs"
}

# Default values
USERNAME="hugodecrypte"
MAX_VIDEOS="3"
HEADLESS_MODE="true"
COMMAND="run"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        build|run|run-interactive|logs|clean|help)
            COMMAND="$1"
            shift
            ;;
        --username)
            USERNAME="$2"
            shift 2
            ;;
        --max-videos)
            MAX_VIDEOS="$2"
            shift 2
            ;;
        --headless)
            HEADLESS_MODE="true"
            shift
            ;;
        --visible)
            HEADLESS_MODE="false"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Create necessary directories
mkdir -p data logs

# Function to build Docker image
build_image() {
    print_info "Building Docker image..."
    docker build -t tiktok-scraper .
    print_success "Docker image built successfully!"
}

# Function to run the scraper
run_scraper() {
    print_info "Running TikTok scraper..."
    print_info "Username: @$USERNAME"
    print_info "Max videos: $MAX_VIDEOS"
    print_info "Headless mode: $HEADLESS_MODE"
    
    docker run --rm \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        -e TIKTOK_USERNAME="$USERNAME" \
        -e MAX_VIDEOS="$MAX_VIDEOS" \
        -e HEADLESS_MODE="$HEADLESS_MODE" \
        tiktok-scraper
    
    print_success "Scraping completed! Check the data/ directory for CSV files."
}

# Function to run with interactive shell
run_interactive() {
    print_info "Starting interactive container..."
    docker run --rm -it \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        -e TIKTOK_USERNAME="$USERNAME" \
        -e MAX_VIDEOS="$MAX_VIDEOS" \
        -e HEADLESS_MODE="$HEADLESS_MODE" \
        tiktok-scraper /bin/bash
}

# Function to show logs
show_logs() {
    print_info "Showing container logs..."
    docker logs tiktok-scraper 2>/dev/null || print_warning "No running container found"
}

# Function to clean up
clean_up() {
    print_info "Cleaning up Docker resources..."
    
    # Stop and remove containers
    docker stop tiktok-scraper 2>/dev/null || true
    docker rm tiktok-scraper 2>/dev/null || true
    
    # Remove image
    docker rmi tiktok-scraper 2>/dev/null || true
    
    print_success "Cleanup completed!"
}

# Main execution
case $COMMAND in
    build)
        build_image
        ;;
    run)
        build_image
        run_scraper
        ;;
    run-interactive)
        build_image
        run_interactive
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_up
        ;;
    help)
        show_usage
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac
