"""
Data Models Module
Pydantic models for state management and API request/response schemas.
"""

from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the message was created")


class InterviewState(TypedDict):
    """
    State schema for the LangGraph interview workflow.
    Uses TypedDict for LangGraph compatibility.
    """
    # Session identification
    session_id: str

    # Document content
    resume_text: str
    job_description_text: str

    # Conversation tracking
    messages: Annotated[List[Dict[str, Any]], add_messages]

    # Interview strategy and context
    interview_strategy: str
    key_topics: List[str]
    questions_asked: int

    # Current state
    current_question: Optional[str]
    current_topic: Optional[str]
    needs_followup: bool
    topic_followup_counts: Dict[str, int]  # Track follow-up count per topic

    # Time tracking
    start_time: float
    time_elapsed: float

    # Interview status
    is_concluded: bool
    conclusion_reason: Optional[str]


class SessionData(BaseModel):
    """Data stored for each interview session."""
    session_id: str
    resume_text: str
    job_description_text: str
    conversation_history: List[Message] = Field(default_factory=list)
    interview_strategy: Optional[str] = None
    key_topics: List[str] = Field(default_factory=list)
    questions_asked: int = 0
    topic_followup_counts: Dict[str, int] = Field(default_factory=dict)
    start_time: Optional[datetime] = None
    is_active: bool = True
    is_concluded: bool = False
    conclusion_reason: Optional[str] = None


class UploadDocumentsRequest(BaseModel):
    """Request model for document upload (not used directly with multipart/form-data)."""
    pass


class UploadDocumentsResponse(BaseModel):
    """Response model for document upload."""
    session_id: str
    message: str
    resume_length: int
    job_description_length: int


class StartInterviewRequest(BaseModel):
    """Request model for starting an interview."""
    session_id: str


class StartInterviewResponse(BaseModel):
    """Response model for starting an interview."""
    session_id: str
    first_question: str
    message: str


class TranscribeAudioRequest(BaseModel):
    """Request model for audio transcription (not used directly with multipart/form-data)."""
    pass


class TranscribeAudioResponse(BaseModel):
    """Response model for audio transcription."""
    transcription: str
    session_id: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting an answer."""
    session_id: str
    answer: str


class SubmitAnswerResponse(BaseModel):
    """Response model for submitting an answer."""
    session_id: str
    next_question: Optional[str] = None
    is_concluded: bool = False
    conclusion_message: Optional[str] = None
    time_remaining_seconds: Optional[float] = None


class InterviewStatusResponse(BaseModel):
    """Response model for interview status."""
    session_id: str
    is_active: bool
    is_concluded: bool
    questions_asked: int
    time_elapsed_seconds: Optional[float] = None
    time_remaining_seconds: Optional[float] = None
    conclusion_reason: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: Optional[str] = None
