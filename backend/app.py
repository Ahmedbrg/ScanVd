"""
ScanVD — Video Content Scanner Backend
Upload a video, type what you're looking for, and get exact timestamps.
Uses OpenAI Whisper for speech-to-text transcription with word-level timestamps.
"""

import os
import sys
import uuid
import shutil
import subprocess
import traceback
import whisper
import cv2
from ultralytics import YOLO
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="ScanVD - Video Content Scanner")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Find ffmpeg binary (required by Whisper to extract audio from video)
FFMPEG_PATH = None

def find_ffmpeg():
    """Find the ffmpeg binary path. Returns the path or None."""
    global FFMPEG_PATH

    # 1. Try system ffmpeg first
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        FFMPEG_PATH = "ffmpeg"
        print("✓ ffmpeg found (system)!")
        return True
    except FileNotFoundError:
        pass

    # 2. Try imageio-ffmpeg bundled binary (most reliable fallback)
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_exe):
            FFMPEG_PATH = ffmpeg_exe
            print(f"✓ ffmpeg found (imageio-ffmpeg): {ffmpeg_exe}")
            return True
    except ImportError:
        pass

    # 3. Try common winget install locations
    common_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"),
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
    ]
    for path in common_paths:
        ffmpeg_exe = os.path.join(path, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            FFMPEG_PATH = ffmpeg_exe
            print(f"✓ ffmpeg found: {ffmpeg_exe}")
            return True
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                if "ffmpeg.exe" in files:
                    FFMPEG_PATH = os.path.join(root, "ffmpeg.exe")
                    print(f"✓ ffmpeg found: {FFMPEG_PATH}")
                    return True

    print("=" * 60)
    print("  ERROR: ffmpeg is NOT installed!")
    print("  Whisper needs ffmpeg to extract audio from videos.")
    print()
    print("  Install it with:")
    print("    pip install imageio-ffmpeg")
    print()
    print("  Then run again (no restart needed).")
    print("=" * 60)
    return False

FFMPEG_AVAILABLE = find_ffmpeg()

# Monkey-patch Whisper's load_audio to use our discovered ffmpeg binary
# This is needed because imageio-ffmpeg's binary is NOT named "ffmpeg.exe"
# (it's named something like "ffmpeg-win-x86_64-v7.1.exe")
if FFMPEG_PATH and FFMPEG_PATH != "ffmpeg":
    import numpy as np
    import whisper.audio

    _ORIGINAL_SAMPLE_RATE = whisper.audio.SAMPLE_RATE

    def _patched_load_audio(file, sr=_ORIGINAL_SAMPLE_RATE):
        """Load audio using our discovered ffmpeg binary."""
        cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-threads", "0",
            "-i", file,
            "-f", "s16le",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-ar", str(sr),
            "-"
        ]
        try:
            out = subprocess.run(
                cmd, capture_output=True, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            ).stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg error: {e.stderr.decode(errors='replace')}") from e

        return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

    whisper.audio.load_audio = _patched_load_audio
    print("✓ Whisper patched to use discovered ffmpeg binary")

# Directories
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load Whisper model (using "base" for speed; use "medium" or "large" for better accuracy)
print("Loading Whisper model...")
model = whisper.load_model("base")
print("Whisper model loaded!")

# Load YOLOv8 model for object detection
print("Loading YOLOv8 model...")
yolo_model = YOLO("yolov8n.pt")
print("YOLOv8 model loaded!")

def extract_objects(video_path, sample_rate_fps=1.0):
    """Extract objects from video frames at a given FPS using YOLOv8."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30 # fallback
        
    frame_interval = int(fps / sample_rate_fps)
    if frame_interval < 1:
        frame_interval = 1

    objects_timeline = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            
            # Run YOLO
            results = yolo_model(frame, verbose=False)
            
            # Extract class names
            detected_classes = set()
            for r in results:
                for c in r.boxes.cls:
                    detected_classes.add(yolo_model.names[int(c)])
            
            if detected_classes:
                 objects_timeline.append({
                     "timestamp": timestamp,
                     "formatted_time": format_time(timestamp),
                     "objects": list(detected_classes)
                 })

        frame_count += 1

    cap.release()
    return objects_timeline

# In-memory store for transcriptions: { video_id: { segments: [...], full_text: str } }
transcriptions = {}


def format_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file and transcribe it using Whisper."""
    # Validate file type
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save uploaded file
    video_id = str(uuid.uuid4())
    video_filename = f"{video_id}{ext}"
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Check ffmpeg before attempting transcription
    if not FFMPEG_AVAILABLE:
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(
            status_code=500,
            detail="ffmpeg is not installed. Install it with: winget install --id=Gyan.FFmpeg -e  — then restart your terminal."
        )

    # Transcribe with Whisper
    try:
        print(f"Transcribing video: {file.filename}...")
        result = model.transcribe(
            video_path,
            word_timestamps=True,
            verbose=False,
            fp16=False,
        )
        print(f"Transcription complete for: {file.filename}")
    except Exception as e:
        # Print full traceback to console so we can see what went wrong
        print(f"\n{'='*60}")
        print(f"ERROR transcribing {file.filename}:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        # Clean up file on error
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    # Process segments with word-level detail
    segments = []
    for segment in result.get("segments", []):
        seg_data = {
            "id": segment["id"],
            "start": segment["start"],
            "end": segment["end"],
            "start_formatted": format_time(segment["start"]),
            "end_formatted": format_time(segment["end"]),
            "text": segment["text"].strip(),
        }

        # Include word-level timestamps if available
        if "words" in segment:
            seg_data["words"] = [
                {
                    "word": w["word"].strip(),
                    "start": w["start"],
                    "end": w["end"],
                    "start_formatted": format_time(w["start"]),
                    "end_formatted": format_time(w["end"]),
                }
                for w in segment["words"]
            ]

        segments.append(seg_data)

    # Detect objects in the video
    try:
        print(f"Detecting objects in video: {file.filename}...")
        # Sample at 1 frame every 2 seconds to be faster, adjust as needed
        objects_data = extract_objects(video_path, sample_rate_fps=0.5)
        print(f"Object detection complete for: {file.filename}")
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR detecting objects in {file.filename}:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        objects_data = []

    # Store transcription
    transcriptions[video_id] = {
        "segments": segments,
        "objects": objects_data,
        "full_text": result.get("text", ""),
        "language": result.get("language", "unknown"),
        "video_path": video_path,
        "video_filename": video_filename,
        "original_name": file.filename,
    }

    return {
        "video_id": video_id,
        "message": "Video uploaded and transcribed successfully",
        "language": result.get("language", "unknown"),
        "full_text": result.get("text", ""),
        "segment_count": len(segments),
    }


class SearchRequest(BaseModel):
    video_id: str
    query: str


@app.post("/api/search")
async def search_video(request: SearchRequest):
    """Search through the transcription for matching content."""
    if request.video_id not in transcriptions:
        raise HTTPException(status_code=404, detail="Video not found. Please upload again.")

    data = transcriptions[request.video_id]
    query = request.query.lower().strip()

    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    results = []

    # Search through segments
    for segment in data["segments"]:
        segment_text = segment["text"].lower()

        if query in segment_text:
            # Found a match in this segment
            match = {
                "segment_id": segment["id"],
                "start": segment["start"],
                "end": segment["end"],
                "start_formatted": segment["start_formatted"],
                "end_formatted": segment["end_formatted"],
                "text": segment["text"],
                "match_type": "segment",
            }

            # Try to find word-level match for precise timestamp
            if "words" in segment:
                query_words = query.split()
                words = segment["words"]

                for i in range(len(words)):
                    # Check if query starts at this word
                    window_text = " ".join(
                        w["word"].lower() for w in words[i:i + len(query_words) + 5]
                    )
                    if query in window_text:
                        match["precise_start"] = words[i]["start"]
                        match["precise_start_formatted"] = words[i]["start_formatted"]
                        match["match_type"] = "word"
                        break

            results.append(match)

    # Also do partial / fuzzy matching for words within segments
    if not results:
        query_words = query.split()
        for segment in data["segments"]:
            segment_text_lower = segment["text"].lower()
            # Check if any query words appear individually
            matching_words = [w for w in query_words if w in segment_text_lower]
            if len(matching_words) >= max(1, len(query_words) // 2):
                results.append({
                    "segment_id": segment["id"],
                    "start": segment["start"],
                    "end": segment["end"],
                    "start_formatted": segment["start_formatted"],
                    "end_formatted": segment["end_formatted"],
                    "text": segment["text"],
                    "match_type": "partial",
                    "matched_words": matching_words,
                })

    # Search through objects
    for obj_frame in data.get("objects", []):
        obj_text_lower = " ".join(obj_frame["objects"]).lower()
        if query in obj_text_lower:
            results.append({
                "segment_id": f"obj_{obj_frame['timestamp']}",
                "start": obj_frame["timestamp"],
                "end": obj_frame["timestamp"] + 1,
                "start_formatted": obj_frame["formatted_time"],
                "end_formatted": format_time(obj_frame["timestamp"] + 1),
                "text": f"Detected objects: {', '.join(obj_frame['objects'])}",
                "match_type": "object",
            })

    # Sort results by start time
    results.sort(key=lambda x: x["start"])

    return {
        "query": request.query,
        "result_count": len(results),
        "results": results,
        "full_text": data["full_text"],
    }


@app.get("/api/video/{video_id}")
async def get_video(video_id: str):
    """Serve the uploaded video file."""
    if video_id not in transcriptions:
        raise HTTPException(status_code=404, detail="Video not found.")

    video_path = transcriptions[video_id]["video_path"]
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk.")

    return FileResponse(video_path, media_type="video/mp4")


@app.get("/api/transcript/{video_id}")
async def get_transcript(video_id: str):
    """Get the full transcription for a video."""
    if video_id not in transcriptions:
        raise HTTPException(status_code=404, detail="Video not found.")

    data = transcriptions[video_id]
    return {
        "video_id": video_id,
        "language": data["language"],
        "full_text": data["full_text"],
        "segments": data["segments"],
    }


# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)
print(f"Frontend directory: {FRONTEND_DIR}")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {FRONTEND_DIR}")
