#!/usr/bin/env python3
"""
Audio file splitter - splits an audio file into multiple parts based on timestamps
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing invalid characters.
    """
    # Replace invalid characters with underscores or remove them
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Strip leading/trailing spaces
    filename = filename.strip()
    return filename


def parse_timestamp(timestamp: str) -> int:
    """
    Convert timestamp (HH:MM:SS or MM:SS) to seconds.
    """
    parts = timestamp.split(':')
    parts = [int(p) for p in parts]
    
    if len(parts) == 2:  # MM:SS
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:  # HH:MM:SS
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def format_timestamp(seconds: int) -> str:
    """
    Convert seconds to HH:MM:SS format for ffmpeg.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def is_valid_audio_file(file_path: Path) -> bool:
    """
    Validate if an audio file is valid and not corrupted using ffprobe.
    
    Args:
        file_path: Path to the audio file to validate
        
    Returns:
        True if the file is valid, False otherwise
    """
    try:
        # Use ffprobe to check if file is valid
        cmd = [
            'ffprobe',
            '-v', 'error',  # Only show errors
            '-select_streams', 'a:0',  # Select first audio stream
            '-show_entries', 'stream=codec_name,duration',  # Get basic info
            '-of', 'default=noprint_wrappers=1',
            str(file_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10  # 10 second timeout for validation
        )
        
        # If return code is 0 and we got output, file is valid
        if result.returncode == 0 and result.stdout:
            # Check if we got codec_name in output (indicates valid audio)
            return 'codec_name' in result.stdout
        
        return False
        
    except (subprocess.TimeoutExpired, Exception) as e:
        # If ffprobe fails or times out, consider file invalid
        return False


def parse_tracklist(tracklist: str) -> List[Tuple[str, str]]:
    """
    Parse the tracklist string into a list of (timestamp, song_name) tuples.
    """
    tracks = []
    lines = tracklist.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Split on first space to get timestamp and song name
        parts = line.split(None, 1)
        if len(parts) == 2:
            timestamp, song_name = parts
            tracks.append((timestamp, song_name))
    
    return tracks


def split_audio(input_file: str, tracks: List[Tuple[str, str]], output_dir: str = None):
    """
    Split audio file into multiple parts based on timestamps.
    
    Args:
        input_file: Path to the input audio file
        tracks: List of (timestamp, song_name) tuples
        output_dir: Output directory (default: create folder named after input file)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Create output directory
    if output_dir is None:
        # Use the input file's stem (filename without extension) as folder name
        output_dir = input_path.parent / input_path.stem
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Get file extension
    file_ext = input_path.suffix
    
    # Counter for statistics
    skipped_count = 0
    processed_count = 0
    failed_count = 0
    
    # Process each track
    for i, (timestamp, song_name) in enumerate(tracks):
        track_num = i + 1
        total_tracks = len(tracks)
        
        start_time = parse_timestamp(timestamp)
        
        # Determine end time (start of next track or end of file)
        if i + 1 < len(tracks):
            end_timestamp, _ = tracks[i + 1]
            end_time = parse_timestamp(end_timestamp)
            duration = end_time - start_time
        else:
            # Last track - extract to end of file
            duration = None
        
        # Create sanitized filename
        sanitized_name = sanitize_filename(song_name)
        output_file = output_dir / f"{sanitized_name}{file_ext}"
        
        print(f"[{track_num}/{total_tracks}] {song_name} ({timestamp})")
        
        # Check if file already exists and is valid
        if output_file.exists():
            file_size = output_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            # First check file size (quick check)
            if file_size < 1024 * 1024:  # < 1 MB
                print(f"  ⚠ Exists but small ({file_size_mb:.2f} MB) - re-extracting")
            else:
                # File size looks good, validate it's a valid audio file
                print(f"  Validating existing file ({file_size_mb:.2f} MB)...", end='', flush=True)
                if is_valid_audio_file(output_file):
                    print(f" ✓ Valid - skipping")
                    skipped_count += 1
                    continue
                else:
                    print(f" ✗ Invalid/corrupted - re-extracting")
        
        # Build ffmpeg command with progress output
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-ss', str(start_time),
        ]
        
        if duration is not None:
            cmd.extend(['-t', str(duration)])
        
        cmd.extend([
            '-c', 'copy',  # Copy codec without re-encoding
            '-y',  # Overwrite output file if exists
            '-loglevel', 'warning',  # Only show warnings/errors
            '-stats',  # Show progress stats
            str(output_file)
        ])
        
        # Execute ffmpeg with real-time output
        print(f"  → Extracting to: {output_file.name}")
        try:
            # Use Popen for real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Wait for process to complete
            stdout, _ = process.communicate(timeout=300)  # 5 minute timeout
            
            if process.returncode == 0:
                # Verify output file was created and has reasonable size
                if output_file.exists():
                    file_size_mb = output_file.stat().st_size / (1024 * 1024)
                    print(f"  ✓ Success ({file_size_mb:.2f} MB)")
                    processed_count += 1
                else:
                    print(f"  ✗ Failed: Output file not created")
                    failed_count += 1
            else:
                print(f"  ✗ Failed with exit code {process.returncode}")
                if stdout:
                    print(f"  Error output: {stdout}")
                failed_count += 1
                
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"  ✗ Timeout: Process took longer than 5 minutes")
            failed_count += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_count += 1
        
        print()  # Blank line between tracks
    
    # Print summary
    print("=" * 50)
    print(f"Summary:")
    print(f"  Processed: {processed_count}")
    print(f"  Skipped:   {skipped_count}")
    print(f"  Failed:    {failed_count}")
    print(f"  Total:     {len(tracks)}")
    print("=" * 50)
    print(f"\nOutput directory: {output_dir}")


def read_tracklist_file(tracklist_file: str) -> str:
    """
    Read the tracklist from a file.
    
    Args:
        tracklist_file: Path to the file containing timestamps and song names
        
    Returns:
        The contents of the tracklist file as a string
    """
    tracklist_path = Path(tracklist_file)
    
    if not tracklist_path.exists():
        raise FileNotFoundError(f"Tracklist file not found: {tracklist_file}")
    
    with open(tracklist_path, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    """
    Main function - parses command line arguments and splits the audio file.
    """
    parser = argparse.ArgumentParser(
        description='Split an audio file into multiple parts based on timestamps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s audio.m4a tracklist.txt
  
Tracklist file format:
  00:00 Song Title One
  02:30 Song Title Two
  05:15 Song Title Three
  ...
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Path to the input audio file (m4a, mp3, etc.)'
    )
    
    parser.add_argument(
        'tracklist_file',
        help='Path to the file containing timestamps and song names'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output directory (default: folder named after input file)',
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        # Read the tracklist from file
        tracklist_content = read_tracklist_file(args.tracklist_file)
        
        # Parse the tracklist
        tracks = parse_tracklist(tracklist_content)
        
        if not tracks:
            print("Error: No tracks found in tracklist file", file=sys.stderr)
            sys.exit(1)
        
        print(f"Found {len(tracks)} tracks to extract")
        
        # Split the audio
        split_audio(args.input_file, tracks, args.output)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

