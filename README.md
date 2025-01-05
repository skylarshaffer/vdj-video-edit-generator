# vdj-video-edit-generator
Generate a simple, automatically offset Video Edit file for Virtual DJ from similar source audio and video files.

A single Python script to run on specified files, folders, or against its own parent folder.

## Overview

1. **File Discovery**
   - Scans the audio source directory for supported audio files
   - For each audio file, looks for a matching video file (same name, any supported extension) in the video source directory

2. **Duration Detection**
   - Uses Mutagen for fast media duration detection
   - Falls back to FFmpeg if there is no length metadata or for formats Mutagen cannot parse

3. **Audio Analysis**
   - For each matched pair, analyzes the audio streams to find the time offset between them.
   - If match confidence is low, (Substandard) is appended to the output .vdjedit file.
   - If music video begins AFTER audio file, (Negative) is appended to the output .vdjedit file.

4. **Output .vdjedit**
   - Creates a .vdjedit file for each matched pair
   - Skips existing files unless --overwrite (-w) flag is used
   
   ### Standard .vdjedit file:
   ```XML
   <?xml version="1.0" ?>
   <edit source="[AUDIO FILENAME]" sourcesize="[AUDIO SIZE (BYTES)]">
      <video>
         <video pos="", sourcepos="", length="", source="[VIDEO FILENAME]", sourcesize="[VIDEO SIZE (BYTES)]"/>
      </video>
   </edit>
   ```
   - For positive offsets (video starts after audio):
      - pos: 0.0
      - sourcepos: absolute value of offset rounded to 6 decimals
      - length: remaining video length OR remaining song length, whatever is smaller

   - For negative offsets (video starts before audio):
      - pos: absolute value of offset rounded to 6 decimals
      - sourcepos: 0.0
      - length: remaining video length OR remaining song length, whatever is smaller

## Prerequisites

- Python 3.9&lt;version&lt;3.12 (latest is incompatible with audio-offset-finder)
- FFmpeg installed and callable by `ffmpeg` command
- Required Python packages:
    - audio-offset-finder
    - mutagen

## Installation

1. Install FFmpeg (Windows):
   - Download from https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.7z
   - Move FFmpeg's bin directory to permanent home and then add to system PATH
   - OR just drop extracted ffmpeg.exe in C:\Windows\System32

2. Install Python dependencies:
   ```bash
   pip install audio-offset-finder mutagen
   ```

## Usage

The script can be run using either named arguments or positional arguments:

### Arguments

1. `--audio-source`, `-a`: Directory containing audio files
2. `--video-source`, `-v`: Directory containing corresponding video files (or specify a specific filename)
3. `--output-dir`, `-o`: Directory where .vdjedit files will be created (or specify a specific filename if one file only)
4. `--overwrite`, `-w`: Optional flag to overwrite existing .vdjedit files (default: False)

### Example with Some Arguments:
```bash
python createvdjedit.py -v "path/to/videos" --overwrite
```

### Example with Named Arguments with Overwrite:
```bash
python createvdjedit.py --audio-source "path/to/audio" --video-source "path/to/videos" --output-dir "path/to/output" --overwrite
```

### Example with Positional Arguments without Overwrite:
```bash
python createvdjedit.py "path/to/audio" "path/to/videos" "path/to/output"
```

## File Matching

- The script looks for files with known audio extensions (below) in the audio directory
- For each audio file, it looks for a matching video file with a known video extension (below) in the video directory
- By default, the script will skip files that already have a corresponding .vdjedit file in the output directory
- Use the --overwrite (-w) flag to replace existing .vdjedit files
- Matching is case-insensitive and based on filename. Make sure you rename your video files to match your source audio files.
- Output files are created in the output directory with the following naming conventions:
  - `filename.vdjedit` for standard files (music video file starts BEFORE audio file)
  - `filename(Negative).vdjedit` for negative offsets (music video file starts AFTER audio file)
  - `filename(Substandard).vdjedit` for low-quality matches (significant audio difference between video and audio files)
  - `filename(Negative)(Substandard).vdjedit` for low-quality matches with negative offsets

## Supported File Formats

### Audio

- .mp3
- .wav
- .flac
- .m4a
- .aac
- .ogg
- .wma
- .aiff
- .alac
- .opus
- .ac3

### Video

- .mp4
- .mkv
- .avi
- .mov
- .wmv
- .flv
- .webm
- .m4v
- .mpg
- .mpeg
- .3gp
- .ts

## AI Disclosure

This code was written almost entirely by brute-force debug and revision by claude-3.5-sonnet in Cursor. I claim no responsibility for any of the above doe, I only shared because I figured someone else might be able to use it as well.
