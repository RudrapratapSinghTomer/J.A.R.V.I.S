import webbrowser
import logging
import urllib.parse

logger = logging.getLogger("jarvis.skills.youtube")

def play_video(query: str):
    """
    Search and play a video on YouTube.
    Uses yt-dlp to find the best match and opens it directly.
    """
    if not query:
        return False
        
    logger.info(f"YouTube: Searching for '{query}'...")
    
    try:
        import subprocess
        import sys
        # Use yt-dlp to get the first video URL
        # --get-id combined with 'ytsearch1:' gets the ID of the first result
        cmd = [sys.executable, "-m", "yt_dlp", "--get-id", f"ytsearch1:{query}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        video_id = result.stdout.strip()
        
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"YouTube: Found video ID {video_id}. Opening {video_url}...")
            webbrowser.open(video_url)
            return True
        else:
            # Fallback to search results if yt-dlp fails to find a specific ID
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(search_url)
            return True
            
    except Exception as e:
        logger.error(f"YouTube skill failed to get direct link: {e}")
        # Fallback to standard search
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(search_url)
        return True

def stop_music():
    """
    Stop any playing music/video. 
    Uses psutil to find and terminate browser processes gracefully.
    """
    import psutil
    logger.info("Stopping music/video playback...")
    
    browsers = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"]
    killed = False
    
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'].lower() in browsers:
                proc.terminate()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if not killed:
        logger.info("No active browser sessions found to stop.")
    
    return True

if __name__ == "__main__":
    # Test
    play_video("Iron Man Mark 85 Theme")
