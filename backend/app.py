"""
ScanVD — Video Content Scanner Backend
Upload a video, type what you're looking for, and get exact timestamps.
Uses OpenAI Whisper for speech-to-text transcription with word-level timestamps.
"""

import os
import sys
<<<<<<< HEAD
import uuid
import shutil
import subprocess
import traceback
import whisper
import cv2
=======
import subprocess
import whisper
import cv2
import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
>>>>>>> 6b84c23 (update)
from ultralytics import YOLO
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

<<<<<<< HEAD
app = FastAPI(title="ScanVD - Video Content Scanner")
=======
# make the app
app = FastAPI()
app.title = "ScanVD - Video Content Scanner"
>>>>>>> 6b84c23 (update)

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

<<<<<<< HEAD
def extract_objects(video_path, sample_rate_fps=1.0):
    """Extract objects from video frames at a given FPS using YOLOv8."""
=======
# Load CLIP model for description search
print("Loading CLIP model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
print("CLIP model loaded!")

def extract_visual_features(video_path, sample_rate_fps=1.0):
    """Extract objects and CLIP embeddings from video frames at a given FPS."""
>>>>>>> 6b84c23 (update)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30 # fallback
        
    frame_interval = int(fps / sample_rate_fps)
    if frame_interval < 1:
        frame_interval = 1

<<<<<<< HEAD
    objects_timeline = []
=======
    visual_timeline = []
>>>>>>> 6b84c23 (update)
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
            
<<<<<<< HEAD
            if detected_classes:
                 objects_timeline.append({
                     "timestamp": timestamp,
                     "formatted_time": format_time(timestamp),
                     "objects": list(detected_classes)
=======
            # Run CLIP
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                
                inputs = clip_processor(images=pil_image, return_tensors="pt").to(device)
                with torch.no_grad():
                    # Get the vision outputs from the model
                    vision_outputs = clip_model.vision_model(**inputs)
                    pooled_output = vision_outputs.pooler_output
                    # Project to 512 dimensions
                    image_features = clip_model.visual_projection(pooled_output)
                
                # Normalize the features
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                embedding = image_features.cpu().numpy().flatten().tolist()
            except Exception as e:
                print("Error extracting CLIP features:")
                print(e)
                embedding = []
            
            if detected_classes or embedding:
                 visual_timeline.append({
                     "timestamp": timestamp,
                     "formatted_time": format_time(timestamp),
                     "objects": list(detected_classes),
                     "clip_embedding": embedding
>>>>>>> 6b84c23 (update)
                 })

        frame_count += 1

    cap.release()
<<<<<<< HEAD
    return objects_timeline

# In-memory store for transcriptions: { video_id: { segments: [...], full_text: str } }
transcriptions = {}


def format_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
=======
    return visual_timeline

# store the videos here
transcriptions = {}

def format_time(seconds):
    # calculate hours, minutes, seconds
    h = int(seconds / 3600)
    m = int((seconds - (h * 3600)) / 60)
    s = int(seconds - (h * 3600) - (m * 60))
    
    # add leading zeros
    str_h = str(h)
    if len(str_h) == 1:
        str_h = "0" + str_h
        
    str_m = str(m)
    if len(str_m) == 1:
        str_m = "0" + str_m
        
    str_s = str(s)
    if len(str_s) == 1:
        str_s = "0" + str_s
        
    result = str_h + ":" + str_m + ":" + str_s
    return result
>>>>>>> 6b84c23 (update)


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file and transcribe it using Whisper."""
<<<<<<< HEAD
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
=======
    # check file extension
    filename = file.filename
    ext = ""
    if "." in filename:
        parts = filename.split(".")
        ext = "." + parts[len(parts)-1].lower()
        
    is_good = False
    if ext == ".mp4" or ext == ".avi" or ext == ".mov" or ext == ".mkv":
        is_good = True
    if ext == ".webm" or ext == ".flv" or ext == ".wmv" or ext == ".m4v":
        is_good = True
        
    if is_good == False:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type! Please upload mp4, avi, mov, mkv, webm, flv, wmv, or m4v."
        )

    # generate a random string for the video id
    video_id = ""
    import random
    letters_and_numbers = "abcdefghijklmnopqrstuvwxyz1234567890"
    for i in range(20):
        video_id = video_id + random.choice(letters_and_numbers)
        
    video_filename = video_id + ext
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    try:
        # read the file and save it
        file_data = file.file.read()
        f = open(video_path, "wb")
        f.write(file_data)
        f.close()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to save file!")
>>>>>>> 6b84c23 (update)

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
<<<<<<< HEAD
        # Print full traceback to console so we can see what went wrong
        print(f"\n{'='*60}")
        print(f"ERROR transcribing {file.filename}:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        # Clean up file on error
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
=======
        # print error to console
        print("ERROR transcribing file:")
        print(e)
        
        # delete file if it exists
        is_file_there = os.path.exists(video_path)
        if is_file_there == True:
            os.remove(video_path)
            
        raise HTTPException(status_code=500, detail="Transcription failed!")
>>>>>>> 6b84c23 (update)

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

<<<<<<< HEAD
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
=======
        # add words if they exist
        if "words" in segment:
            words_list = []
            for w in segment["words"]:
                word_obj = {}
                word_obj["word"] = w["word"].strip()
                word_obj["start"] = w["start"]
                word_obj["end"] = w["end"]
                word_obj["start_formatted"] = format_time(w["start"])
                word_obj["end_formatted"] = format_time(w["end"])
                words_list.append(word_obj)
            seg_data["words"] = words_list

        segments.append(seg_data)

    # Detect objects and features in the video
    try:
        print(f"Detecting visual features in video: {file.filename}...")
        # Sample at 1 frame every 2 seconds to be faster, adjust as needed
        visual_data = extract_visual_features(video_path, sample_rate_fps=0.5)
        print(f"Visual extraction complete for: {file.filename}")
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR detecting features in {file.filename}:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        visual_data = []

    # Get unique objects
    unique_objects = set()
    for item in visual_data:
        unique_objects.update(item["objects"])
>>>>>>> 6b84c23 (update)

    # Store transcription
    transcriptions[video_id] = {
        "segments": segments,
<<<<<<< HEAD
        "objects": objects_data,
=======
        "visual_data": visual_data,
        "unique_objects": list(unique_objects),
>>>>>>> 6b84c23 (update)
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
<<<<<<< HEAD
=======
        "unique_objects": list(unique_objects),
>>>>>>> 6b84c23 (update)
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

<<<<<<< HEAD
    # Also do partial / fuzzy matching for words within segments
    if not results:
        query_words = query.split()
        for segment in data["segments"]:
            segment_text_lower = segment["text"].lower()
            # Check if any query words appear individually
            matching_words = [w for w in query_words if w in segment_text_lower]
            if len(matching_words) >= max(1, len(query_words) // 2):
=======
    # Also do partial fuzzy matching
    if len(results) == 0:
        query_words = query.split(" ")
        for segment in data["segments"]:
            segment_text_lower = segment["text"].lower()
            
            # get matching words
            matching_words = []
            for w in query_words:
                if w in segment_text_lower:
                    matching_words.append(w)
                    
            # calculate half
            half = int(len(query_words) / 2)
            if half == 0:
                half = 1
                
            if len(matching_words) >= half:
>>>>>>> 6b84c23 (update)
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

<<<<<<< HEAD
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
=======
    # 1. First encode query with CLIP
    query_embedding = None
    try:
        inputs = clip_processor(text=[query], return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            # Get text outputs from the model
            text_outputs = clip_model.text_model(**inputs)
            pooled_output = text_outputs.pooler_output
            # Project to 512 dimensions
            text_features = clip_model.text_projection(pooled_output)
            
        # Normalize the embedding
        text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
        query_embedding = text_features.cpu().numpy().flatten()
    except Exception as e:
        print("Oops, CLIP encoding failed:")
        print(e)

    # Search through objects and descriptions
    for frame_data in data.get("visual_data", []):
        
        # Check if it matches an object first
        is_object_match = False
        for obj in frame_data["objects"]:
            if query in obj.lower():
                is_object_match = True
                
        if is_object_match == True:
            results.append({
                "segment_id": "obj_" + str(frame_data['timestamp']),
                "start": frame_data["timestamp"],
                "end": frame_data["timestamp"] + 1,
                "start_formatted": frame_data["formatted_time"],
                "end_formatted": format_time(frame_data["timestamp"] + 1),
                "text": "Detected objects: " + ", ".join(frame_data['objects']),
                "match_type": "object",
            })
            continue # Skip semantic match if it's already an exact object match

        # 2. Semantic search using CLIP
        if query_embedding is not None:
            if "clip_embedding" in frame_data:
                # Make sure the embedding is not empty
                if len(frame_data["clip_embedding"]) > 0:
                    frame_emb = np.array(frame_data["clip_embedding"])
                    similarity = np.dot(query_embedding, frame_emb)
                    
                    # I tested this and 0.26 seems to be a good threshold
                    if similarity > 0.26:
                        results.append({
                            "segment_id": "desc_" + str(frame_data['timestamp']),
                            "start": frame_data["timestamp"],
                            "end": frame_data["timestamp"] + 1,
                            "start_formatted": frame_data["formatted_time"],
                            "end_formatted": format_time(frame_data["timestamp"] + 1),
                            "text": "Visual match for: '" + query + "'",
                            "match_type": "description",
                            "similarity": float(similarity)
                        })
>>>>>>> 6b84c23 (update)

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
<<<<<<< HEAD
=======
        "unique_objects": data.get("unique_objects", []),
>>>>>>> 6b84c23 (update)
    }


# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)
print(f"Frontend directory: {FRONTEND_DIR}")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {FRONTEND_DIR}")
