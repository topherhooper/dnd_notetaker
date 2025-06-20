"""Manage and share meeting artifacts"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import uuid

logger = logging.getLogger(__name__)


class Artifacts:
    """Manage all meeting artifacts and create shareable bundles"""
    
    def __init__(self, output_dir: Path, config=None):
        self.output_dir = output_dir
        self.config = config
        self.metadata = {
            "created": datetime.now().isoformat(),
            "id": str(uuid.uuid4())[:8],
            "files": {}
        }
    
    def create_share_bundle(self, video_path: Path, audio_path: Path, 
                          transcript_path: Path, notes_path: Path) -> str:
        """Create a shareable bundle of all artifacts
        
        For now, returns local path. In future, will upload and return URL.
        
        Args:
            video_path: Path to meeting video
            audio_path: Path to extracted audio
            transcript_path: Path to transcript
            notes_path: Path to generated notes
            
        Returns:
            Shareable URL/path for all artifacts
        """
        if self.config and self.config.dry_run:
            # Dry run mode - just show what would happen
            print(f"[DRY RUN] Would save artifacts to: {self.output_dir}/")
            print(f"  - notes.md")
            print(f"  - transcript.json")
            print(f"  - audio.mp3")
            print(f"  - index.html (viewer)")
            print(f"  - artifacts.json (metadata)")
            return f"file://{self.output_dir}/index.html"
            
        # Record file metadata
        self.metadata["files"] = {
            "video": {
                "name": "meeting.mp4",
                "size": self._get_file_size(video_path),
                "path": str(video_path.relative_to(self.output_dir))
            },
            "audio": {
                "name": "audio.mp3",
                "size": self._get_file_size(audio_path),
                "path": str(audio_path.relative_to(self.output_dir))
            },
            "transcript": {
                "name": "transcript.txt",
                "size": self._get_file_size(transcript_path),
                "path": str(transcript_path.relative_to(self.output_dir))
            },
            "notes": {
                "name": "notes.txt",
                "size": self._get_file_size(notes_path),
                "path": str(notes_path.relative_to(self.output_dir))
            }
        }
        
        # Create HTML viewer
        self._create_html_viewer()
        
        # Save metadata
        metadata_path = self.output_dir / "artifacts.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        # For now, return local path
        # TODO: Implement cloud upload
        share_url = f"file://{self.output_dir}/index.html"
        
        return share_url
    
    def _get_file_size(self, path: Path) -> str:
        """Get human-readable file size"""
        if self.config and self.config.dry_run:
            return "0 B"  # Return dummy size in dry run
            
        if not path.exists():
            return "0 B"
            
        size = path.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _create_html_viewer(self):
        """Create a simple HTML viewer for the artifacts"""
        if self.config and self.config.dry_run:
            return  # Skip HTML creation in dry run
            
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meeting Notes - {self.metadata['created'][:10]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .meta {{
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .artifact {{
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .artifact h3 {{
            margin-top: 0;
            color: #444;
        }}
        .artifact-meta {{
            color: #888;
            font-size: 13px;
            margin-bottom: 10px;
        }}
        .download-btn {{
            display: inline-block;
            padding: 8px 16px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
        }}
        .download-btn:hover {{
            background: #0056b3;
        }}
        .notes-content {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: Georgia, serif;
            line-height: 1.6;
            max-height: 400px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📝 Meeting Notes</h1>
        <div class="meta">
            Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
            Session ID: {self.metadata['id']}
        </div>
        
        <div class="artifact">
            <h3>📖 Generated Notes</h3>
            <div class="notes-content" id="notes-content">Loading notes...</div>
        </div>
        
        <div class="artifact">
            <h3>📄 Full Transcript</h3>
            <div class="artifact-meta">Size: {self.metadata['files']['transcript']['size']}</div>
            <a href="transcript.txt" class="download-btn" download>Download Transcript</a>
        </div>
        
        <div class="artifact">
            <h3>🎵 Audio Recording</h3>
            <div class="artifact-meta">Size: {self.metadata['files']['audio']['size']}</div>
            <audio controls style="width: 100%; margin: 10px 0;">
                <source src="audio.mp3" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
            <br>
            <a href="audio.mp3" class="download-btn" download>Download Audio</a>
        </div>
        
        <div class="artifact">
            <h3>🎬 Video Recording</h3>
            <div class="artifact-meta">Size: {self.metadata['files']['video']['size']}</div>
            <a href="meeting.mp4" class="download-btn" download>Download Video</a>
        </div>
    </div>
    
    <script>
        // Load notes content
        fetch('notes.txt')
            .then(response => response.text())
            .then(text => {{
                document.getElementById('notes-content').textContent = text;
            }})
            .catch(err => {{
                document.getElementById('notes-content').textContent = 'Error loading notes.';
            }});
    </script>
</body>
</html>"""
        
        html_path = self.output_dir / "index.html"
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        logger.info("✓ Created HTML viewer for artifacts")