"""Shared data models for RabbitReels services."""

from pydantic import BaseModel # type: ignore
from typing import Optional, Literal


class PromptJob(BaseModel):
    """Job for generating a script from a prompt."""
    job_id: str
    prompt: str
    character_theme: str = "rick_and_morty"
    title: Optional[str] = None

class ScriptJob(BaseModel):
    """Job containing a generated script."""
    job_id: str
    title: str
    script: str

class RenderJob(BaseModel):
    """Job for rendering a video."""
    job_id: str
    title: str
    storage_path: str

class PublishJob(BaseModel):
    """Job for publishing a video to YouTube."""
    job_id: str
    title: str
    storage_path: str

class Turn(BaseModel):
    """A single dialog turn in a conversation."""
    speaker: str
    text: str

class DialogJob(BaseModel):
    """Job containing dialog turns for video creation."""
    job_id: str
    title: str
    character_theme: str
    turns: list[Turn]

class VideoStatus(BaseModel):
    """Status information for a video generation job."""
    job_id: str
    status: Literal["queued", "rendering", "done", "error"]
    progress: Optional[float] = None
    error_msg: Optional[str] = None
    download_url: Optional[str] = None
    youtube_url: Optional[str] = None
