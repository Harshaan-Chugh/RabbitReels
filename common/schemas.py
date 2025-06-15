from pydantic import BaseModel # Does Automatic validation/parsing of incoming JSON
from typing import Optional

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
