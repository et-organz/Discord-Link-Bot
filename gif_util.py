import os
from moviepy import VideoFileClip
import yt_dlp

def download_video(url, save_path):
    """Download the video file from a URL using yt-dlp."""
    ydl_opts = {
        'format': 'best',  # Best available quality
        'outtmpl': save_path,  # Save path for the downloaded video
        'noplaylist': True,  # Don't download playlists, only single video
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def video_to_gif(input_path, output_path, start_time, duration=5, fps=10):
    """Convert part of a video file to a GIF."""
    clip = VideoFileClip(input_path)
    
    # Ensure start_time + duration doesn't exceed video duration
    if start_time + duration > clip.duration:
        duration = clip.duration - start_time

    # Generate subclip and resize
    clip = clip.subclipped(start_time, start_time + duration)
    clip = clip.resized(height=300)

    # Write output GIF
    clip.write_gif(output_path, fps=fps)
