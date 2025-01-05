import os
from pathlib import Path
from audio_offset_finder.audio_offset_finder import find_offset_between_files
import mutagen
import xml.etree.ElementTree as ET
import xml.dom.minidom
import argparse
import subprocess

AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.aiff', 
    '.alac', '.opus', '.ac3'
}

VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
    '.mpg', '.mpeg', '.3gp', '.ts'
}

def get_audio_length(filepath):
    audio = mutagen.File(filepath)
    if audio is None:
        raise ValueError(f"Could not read audio file: {filepath}")
    return float(f"{audio.info.length:.6f}")

def get_media_length(filepath):
    try:
        # Try Mutagen first
        media = mutagen.File(filepath)
        if media is not None:
            return float(f"{media.info.length:.6f}")
        
        # If Mutagen fails, fallback to FFmpeg
        cmd = ['ffmpeg', '-i', str(filepath), '2>&1']
        try:
            # Run ffmpeg command and capture output
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stderr  # FFmpeg outputs to stderr
            
            # Look for duration in FFmpeg output
            duration_str = None
            for line in output.split('\n'):
                if 'Duration:' in line:
                    time_str = line.split('Duration:')[1].split(',')[0].strip()
                    # Convert HH:MM:SS.ms to seconds
                    h, m, s = time_str.split(':')
                    duration = float(h) * 3600 + float(m) * 60 + float(s)
                    return float(f"{duration:.6f}")
            
            raise ValueError(f"Could not find duration in FFmpeg output for: {filepath}")
            
        except subprocess.SubprocessError as e:
            raise ValueError(f"FFmpeg failed to read media file: {filepath}") from e
            
    except Exception as e:
        raise ValueError(f"Could not read media file: {filepath}") from e

def create_vdjedit(audio_path, video_path, output_dir, offset, score, overwrite=False):
    # Validate inputs
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Get file sizes
    audio_size = os.path.getsize(audio_path)
    video_size = os.path.getsize(video_path)
    
    # Get media lengths
    audio_length = get_media_length(audio_path)
    video_length = get_media_length(video_path)
    
    # Calculate final length based on offset
    if offset > 0:
        length = min(audio_length - offset, video_length)
    else:
        length = min(audio_length, video_length + offset)
    
    # Create XML structure
    root = ET.Element("edit")
    root.set("source", str(audio_path))
    root.set("sourcesize", str(audio_size))
    
    video_elem = ET.SubElement(root, "video")
    video_sub = ET.SubElement(video_elem, "video")
    
    # Set attributes based on whether offset is positive or negative
    if offset <= 0:
        video_sub.set("pos", "0.0")
        video_sub.set("sourcepos", f"{abs(offset):.6f}")
    else:
        video_sub.set("pos", f"{abs(offset):.6f}")
        video_sub.set("sourcepos", "0.0")
    
    video_sub.set("length", f"{length:.6f}")
    video_sub.set("source", str(video_path))
    video_sub.set("sourcesize", str(video_size))
    
    # Create output filename
    audio_filename = Path(audio_path).stem
    output_filename = audio_filename
    
    if offset > 0:
        output_filename += "(Negative)"
    if score < 5:
        output_filename += "(Substandard)"
    
    output_path = Path(output_dir) / f"{output_filename}.vdjedit"
    
    # Check if file exists and respect overwrite flag
    if output_path.exists() and not overwrite:
        print(f"Skipping {output_filename}.vdjedit - file already exists")
        return

    # Format XML with proper indentation
    xmlstr = xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xmlstr)

def main():
    # Get the directory where the script is running from
    current_dir = Path().absolute()
    
    parser = argparse.ArgumentParser(description='Create VDJEdit files from audio and video pairs')
    parser.add_argument('--audio-source', '-a', type=str, 
                       default=str(current_dir),
                       help='Directory containing audio files (default: current directory)')
    parser.add_argument('--video-source', '-v', type=str,
                       default=str(current_dir),
                       help='Directory containing video files (default: current directory)')
    parser.add_argument('--output-dir', '-o', type=str,
                       default=str(current_dir),
                       help='Directory for output files (default: current directory)')
    parser.add_argument('--overwrite', '-w', action='store_true',
                       help='Overwrite existing .vdjedit files')

    args = parser.parse_args()

    # Convert to Path objects after string manipulation
    audio_dir = Path(args.audio_source.rstrip('/').rstrip('\\'))
    video_dir = Path(args.video_source.rstrip('/').rstrip('\\'))
    output_dir = Path(args.output_dir.rstrip('/').rstrip('\\'))
    
    # Validate directories exist
    if not audio_dir.exists():
        print(f"Audio directory not found: {audio_dir}")
        return
    if not video_dir.exists():
        print(f"Video directory not found: {video_dir}")
        return
    if not output_dir.exists():
        print(f"Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

    # Get all audio files
    audio_files = []
    for ext in AUDIO_EXTENSIONS:
        audio_files.extend(audio_dir.glob(f"*{ext}"))
        audio_files.extend(audio_dir.glob(f"*{ext.upper()}"))
    
    # Remove duplicates and sort
    audio_files = sorted(set(audio_files))  # Convert to set to remove duplicates
    
    if not audio_files:
        print(f"No audio files found in {audio_dir}")
        return
        
    print(f"Found {len(audio_files)} audio files")
    
    # Track counts
    created = 0    # renamed from successful
    failed = 0
    skipped = 0    # new counter
    
    # Process each audio file
    processed_files = set()
    
    for audio_file in sorted(audio_files):
        try:
            if audio_file.stem in processed_files:
                continue
                
            processed_files.add(audio_file.stem)
            
            # Look for matching video with any supported extension
            video_file = None
            for ext in VIDEO_EXTENSIONS:
                potential_video = video_dir / f"{audio_file.stem}{ext}"
                if potential_video.exists():
                    video_file = potential_video
                    break
                # Also check uppercase extensions
                potential_video = video_dir / f"{audio_file.stem}{ext.upper()}"
                if potential_video.exists():
                    video_file = potential_video
                    break
            
            if video_file:
                print(f"Processing: {audio_file.name}")
                
                # First check for any existing .vdjedit with base name
                base_output_path = output_dir / f"{audio_file.stem}.vdjedit"
                if base_output_path.exists() and not args.overwrite:
                    print(f"Skipping {audio_file.name} - output file already exists")
                    skipped += 1    # increment skipped instead of failed
                    continue
                
                # Get offset and score
                results = find_offset_between_files(str(audio_file), str(video_file))
                offset = results["time_offset"]
                score = results["standard_score"]
                
                # Construct final filename with potential suffixes
                output_filename = audio_file.stem
                if offset > 0:
                    output_filename += "(Negative)"
                if score < 5:
                    output_filename += "(Substandard)"
                final_output_path = output_dir / f"{output_filename}.vdjedit"
                
                # Second check with exact filename
                if final_output_path.exists() and not args.overwrite:
                    print(f"Skipping {audio_file.name} - output file {output_filename}.vdjedit already exists")
                    skipped += 1    # increment skipped instead of failed
                    continue
                
                create_vdjedit(audio_file, video_file, output_dir, offset, score, args.overwrite)
                print(f"Created VDJEdit file for: {audio_file.name}")
                created += 1    # renamed from successful
            else:
                print(f"No matching video found for: {audio_file.name}")
                failed += 1
        except Exception as e:
            print(f"Error processing {audio_file.name}: {str(e)}")
            failed += 1
    
    print(f"\nProcessing complete: {created} created, {skipped} skipped, {failed} failed")

if __name__ == "__main__":
    main()
