from pydantic import BaseModel # type: ignore
from typing import Optional, Literal


class PromptJob(BaseModel):
    job_id: str
    prompt: str
    character_theme: str = "rick_and_morty"  # Add theme, with a default
    title: Optional[str] = None

class ScriptJob(BaseModel):
    job_id: str
    title: str
    script: str

class RenderJob(BaseModel):
    job_id: str
    title: str
    storage_path: str

class PublishJob(BaseModel):
    job_id: str
    title: str
    storage_path: str

class Turn(BaseModel):
    speaker: str  # Make speaker a generic string instead of Literal
    text: str

class DialogJob(BaseModel):
    job_id: str
    title: str
    character_theme: str  # Pass theme along to the video creator
    turns: list[Turn]

class VideoStatus(BaseModel):
    job_id: str
    status: Literal["queued", "rendering", "done", "error"]
    progress: Optional[float] = None  # 0.0 to 1.0
    error_msg: Optional[str] = None
    download_url: Optional[str] = None
    youtube_url: Optional[str] = None
