"""
FastAPI Main Application
Backend server for the screening interview chatbot.
"""

import os
import uuid
import logging
import time
import tempfile
from pathlib import Path
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
import requests

from models import (
    SessionData,
    UploadDocumentsResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    TranscribeAudioResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    InterviewStatusResponse,
    ErrorResponse,
    Message,
)
from document_processor import extract_text_from_document, DocumentProcessingError
from interview_graph import create_interview_graph, InterviewGraphBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    gemini_api_key: str
    deepinfra_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global state
settings: Optional[Settings] = None
interview_graph: Optional[InterviewGraphBuilder] = None
sessions: Dict[str, SessionData] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    global settings, interview_graph
    try:
        settings = Settings()
        logger.info("Settings loaded successfully")

        # Initialize interview graph with Gemini
        interview_graph = create_interview_graph(
            gemini_api_key=settings.gemini_api_key,
            model_name=settings.gemini_model
        )
        logger.info("Interview graph initialized with Gemini")

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

    yield

    # Shutdown - cleanup resources
    logger.info("Shutting down application...")
    try:
        # Clear session data
        sessions.clear()
        logger.info("Cleared session data")

        # Set globals to None for cleanup
        interview_graph = None
        settings = None

        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Initialize FastAPI app
app = FastAPI(
    title="Screening Interview Chatbot API",
    description="Backend API for conducting automated screening interviews",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "Screening Interview Chatbot API",
        "status": "operational",
        "version": "1.0.0"
    }


@app.post(
    "/upload-documents",
    response_model=UploadDocumentsResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_documents(
    resume: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    job_description: UploadFile = File(..., description="Job description file (PDF or DOCX)")
):
    """
    Upload resume and job description documents to create a new interview session.

    Args:
        resume: Resume file (PDF or DOCX format)
        job_description: Job description file (PDF or DOCX format)

    Returns:
        Session ID and document processing confirmation
    """
    logger.info(f"Received document upload request - Resume: {resume.filename}, JD: {job_description.filename}")

    temp_files = []
    try:
        # Validate file types
        resume_ext = Path(resume.filename).suffix.lower()
        jd_ext = Path(job_description.filename).suffix.lower()

        allowed_extensions = {'.pdf', '.docx', '.doc'}
        if resume_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resume file type not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        if jd_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job description file type not supported. Allowed: {', '.join(allowed_extensions)}"
            )

        # Save resume to temporary file
        resume_temp = tempfile.NamedTemporaryFile(delete=False, suffix=resume_ext)
        temp_files.append(resume_temp.name)
        resume_content = await resume.read()
        resume_temp.write(resume_content)
        resume_temp.close()

        # Save job description to temporary file
        jd_temp = tempfile.NamedTemporaryFile(delete=False, suffix=jd_ext)
        temp_files.append(jd_temp.name)
        jd_content = await job_description.read()
        jd_temp.write(jd_content)
        jd_temp.close()

        # Extract text from documents
        resume_text = extract_text_from_document(resume_temp.name)
        jd_text = extract_text_from_document(jd_temp.name)

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Create session data
        session_data = SessionData(
            session_id=session_id,
            resume_text=resume_text,
            job_description_text=jd_text
        )

        # Store session
        sessions[session_id] = session_data

        logger.info(f"Created session {session_id} - Resume: {len(resume_text)} chars, JD: {len(jd_text)} chars")

        return UploadDocumentsResponse(
            session_id=session_id,
            message="Documents uploaded and processed successfully",
            resume_length=len(resume_text),
            job_description_length=len(jd_text)
        )

    except DocumentProcessingError as e:
        logger.error(f"Document processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document processing failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in upload_documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file}: {str(e)}")


@app.post(
    "/start-interview",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_200_OK
)
async def start_interview(request: StartInterviewRequest):
    """
    Initialize an interview with the given session ID and return the first question.

    Args:
        request: Request containing session_id

    Returns:
        First interview question
    """
    logger.info(f"Starting interview for session {request.session_id}")

    # Validate session exists
    if request.session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found"
        )

    session = sessions[request.session_id]

    # Check if interview already started
    if session.start_time is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview has already been started for this session"
        )

    try:
        # Initialize interview state
        from datetime import datetime
        session.start_time = datetime.now()

        initial_state = {
            "session_id": request.session_id,
            "resume_text": session.resume_text,
            "job_description_text": session.job_description_text,
            "messages": [],
            "interview_strategy": "",
            "key_topics": [],
            "questions_asked": 0,
            "current_question": None,
            "current_topic": None,
            "needs_followup": False,
            "topic_followup_counts": {},
            "start_time": time.time(),
            "time_elapsed": 0.0,
            "is_concluded": False,
            "conclusion_reason": None
        }

        # Run the graph to generate first question
        result = interview_graph.invoke(initial_state)

        # Update session with results
        session.interview_strategy = result.get("interview_strategy", "")
        session.key_topics = result.get("key_topics", [])
        session.questions_asked = result.get("questions_asked", 0)

        # Extract the first question
        first_question = result.get("current_question", "")

        # Add to conversation history
        if first_question:
            session.conversation_history.append(Message(
                role="assistant",
                content=first_question
            ))

        logger.info(f"Interview started for session {request.session_id}")

        return StartInterviewResponse(
            session_id=request.session_id,
            first_question=first_question,
            message="Interview started successfully"
        )

    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview: {str(e)}"
        )


@app.post(
    "/transcribe-audio",
    response_model=TranscribeAudioResponse,
    status_code=status.HTTP_200_OK
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    session_id: str = Form(None, description="Session ID for tracking")
):
    """
    Transcribe audio file to text using DeepInfra Whisper model.

    Args:
        audio: Audio file to transcribe

    Returns:
        Transcribed text
    """
    logger.info(f"Received transcription request for file: {audio.filename}, session: {session_id}")

    # Validate session if provided
    if session_id and session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # Read audio content
        audio_content = await audio.read()

        # Determine content type based on file extension
        content_type = "audio/webm"  # default
        if audio.filename:
            suffix = Path(audio.filename).suffix.lower()
            content_type_map = {
                ".wav": "audio/wav",
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".webm": "audio/webm",
                ".ogg": "audio/ogg"
            }
            content_type = content_type_map.get(suffix, "audio/webm")

        # Prepare DeepInfra API request
        headers = {
            "Authorization": f"Bearer {settings.deepinfra_api_key}"
        }

        files = {
            "audio": (audio.filename or "audio.webm", audio_content, content_type)
        }

        # Call DeepInfra Whisper API (increased timeout for long recordings)
        response = requests.post(
            "https://api.deepinfra.com/v1/inference/openai/whisper-large-v3",
            headers=headers,
            files=files,
            timeout=120  # 2 minutes for long recordings
        )

        # Check for errors
        if response.status_code != 200:
            logger.error(f"DeepInfra API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription service error: {response.text}"
            )

        # Parse response
        result = response.json()
        transcribed_text = result.get("text", "")

        if not transcribed_text:
            logger.warning("Empty transcription received from DeepInfra")
            transcribed_text = ""

        logger.info(f"Transcription successful: {len(transcribed_text)} characters")

        return TranscribeAudioResponse(transcription=transcribed_text, session_id=session_id)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during transcription: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to transcription service: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {str(e)}"
        )


@app.post(
    "/submit-answer",
    response_model=SubmitAnswerResponse,
    status_code=status.HTTP_200_OK
)
async def submit_answer(request: SubmitAnswerRequest):
    """
    Submit candidate's answer and receive the next question.

    Args:
        request: Request containing session_id and answer text

    Returns:
        Next question or interview conclusion
    """
    logger.info(f"Received answer submission for session {request.session_id}")

    # Validate session exists
    if request.session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found"
        )

    session = sessions[request.session_id]

    # Check if interview has been started
    if session.start_time is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview has not been started yet. Call /start-interview first."
        )

    # Check if interview is already concluded
    if session.is_concluded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview has already been concluded"
        )

    try:
        # Add user answer to conversation history
        session.conversation_history.append(Message(
            role="user",
            content=request.answer
        ))

        # Build messages for graph state
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in session.conversation_history
        ]

        # Calculate time elapsed
        from datetime import datetime
        time_elapsed = (datetime.now() - session.start_time).total_seconds()

        # Create state for graph
        current_state = {
            "session_id": request.session_id,
            "resume_text": session.resume_text,
            "job_description_text": session.job_description_text,
            "messages": messages,
            "interview_strategy": session.interview_strategy or "",
            "key_topics": session.key_topics,
            "questions_asked": session.questions_asked,
            "current_question": None,
            "current_topic": None,
            "needs_followup": False,
            "topic_followup_counts": getattr(session, 'topic_followup_counts', {}),
            "start_time": session.start_time.timestamp(),
            "time_elapsed": time_elapsed,
            "is_concluded": False,
            "conclusion_reason": None
        }

        # Process through graph
        result = interview_graph.invoke(current_state)

        # Update session
        session.questions_asked = result.get("questions_asked", session.questions_asked)
        session.topic_followup_counts = result.get("topic_followup_counts", session.topic_followup_counts)
        session.is_concluded = result.get("is_concluded", False)
        session.conclusion_reason = result.get("conclusion_reason")

        # Get next question or conclusion
        next_question = result.get("current_question")

        # Add assistant response to history
        if next_question:
            session.conversation_history.append(Message(
                role="assistant",
                content=next_question
            ))

        # Calculate time remaining
        max_time = 30 * 60  # 30 minutes in seconds
        time_remaining = max(0, max_time - time_elapsed)

        logger.info(f"Processed answer for session {request.session_id}, concluded: {session.is_concluded}")

        return SubmitAnswerResponse(
            session_id=request.session_id,
            next_question=next_question if not session.is_concluded else None,
            is_concluded=session.is_concluded,
            conclusion_message=next_question if session.is_concluded else None,
            time_remaining_seconds=time_remaining
        )

    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process answer: {str(e)}"
        )


@app.get(
    "/interview-status/{session_id}",
    response_model=InterviewStatusResponse,
    status_code=status.HTTP_200_OK
)
async def get_interview_status(session_id: str):
    """
    Get the current status of an interview session.

    Args:
        session_id: ID of the session to check

    Returns:
        Interview status information
    """
    logger.info(f"Status check for session {session_id}")

    # Validate session exists
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    session = sessions[session_id]

    # Calculate time metrics
    time_elapsed_seconds = None
    time_remaining_seconds = None

    if session.start_time is not None:
        from datetime import datetime
        time_elapsed_seconds = (datetime.now() - session.start_time).total_seconds()
        max_time = 30 * 60  # 30 minutes
        time_remaining_seconds = max(0, max_time - time_elapsed_seconds)

    return InterviewStatusResponse(
        session_id=session_id,
        is_active=session.is_active,
        is_concluded=session.is_concluded,
        questions_asked=session.questions_asked,
        time_elapsed_seconds=time_elapsed_seconds,
        time_remaining_seconds=time_remaining_seconds,
        conclusion_reason=session.conclusion_reason
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "detail": str(exc.detail)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Custom exception handler for unexpected exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
