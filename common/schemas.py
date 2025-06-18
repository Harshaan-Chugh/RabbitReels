from pydantic import BaseModel # type: ignore
from typing import Optional, Literal


class PromptJob(BaseModel):
    job_id: str
    prompt: str
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
    speaker: Literal["peter", "stewie"]
    text: str

class DialogJob(BaseModel):
    job_id: str
    title: str
    turns: list[Turn]
