# Audio File Splitter

A Python tool to split audio files (m4a, mp3, etc.) into separate tracks based on timestamps.

## Requirements

- Python 3.6+
- ffmpeg (must be installed on your system)

### Installing ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

## Usage

1. Create a tracklist file (e.g., `tracklist.txt`) with timestamps and song names:
```
00:00 Song One
02:30 Song Two
05:15 Song Three
```

2. Run the script with the audio file and tracklist file as arguments:
```bash
python3 split_audio.py <audio_file> <tracklist_file>
```

### Command Line Options

```
python3 split_audio.py [-h] [-o OUTPUT] input_file tracklist_file

positional arguments:
  input_file            Path to the input audio file (m4a, mp3, etc.)
  tracklist_file        Path to the file containing timestamps and song names

optional arguments:
  -h, --help            Show help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory (default: folder named after input file)
```

## Example

Given an input file and tracklist:
```bash
python3 split_audio.py "/Users/antonio/Downloads/Audio/The BEST Electro Swing Playlist.m4a" tracklist_example.txt
```

Where `tracklist_example.txt` contains:
```
00:00 Mamma Mia - Abba
02:34 Celebration - Kool and The Gang
04:37 Le Freak - Chic
...
```

The script will:
1. Create a folder: `/Users/antonio/Downloads/Audio/The BEST Electro Swing Playlist/`
2. Extract each track:
   - `Mamma Mia - Abba.m4a` (from 00:00 to 02:34)
   - `Celebration - Kool and The Gang.m4a` (from 02:34 to 04:37)
   - `Le Freak - Chic.m4a` (from 04:37 to next timestamp)
   - ... and so on until the end of the file

## Batch Processing

To process multiple audio files at once, use the batch processing script:

1. Place all your `.m4a` files in the `audio/` folder

2. For each `.m4a` file, create a corresponding `.txt` file with the same name containing the tracklist:
   - `My Audio.m4a` → `My Audio.txt`
   - Each `.txt` file should contain timestamps and song names (one per line)

3. Check which tracklists are ready (optional):
```bash
cd audio
./check_tracklists.sh
```

4. Run the batch script:
```bash
cd audio
./process_all_audio.sh
```

The script will:
- Find all `.m4a` files in the `audio/` folder
- Look for corresponding `.txt` tracklist files
- Process each pair automatically
- Skip files without tracklists or with empty tracklists
- Display a summary of results

### Tracklist File Format

Each tracklist `.txt` file should contain timestamps and song names:
```
00:00 First Song Title
02:30 Second Song Title
05:15 Third Song Title
```

Lines starting with `#` are treated as comments and ignored.

## Features

- Automatic filename sanitization
- Supports HH:MM:SS and MM:SS timestamp formats
- Uses ffmpeg's copy codec for fast, lossless splitting
- Creates output folder automatically
- Handles files with spaces and special characters
- Batch processing support for multiple audio files

