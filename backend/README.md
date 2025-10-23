# Screening Interview Chatbot - Backend

A FastAPI-based backend for conducting AI-powered screening interviews using LangGraph and OpenAI.

## Architecture Overview

This backend implements a multi-agent interview system using LangGraph's StateGraph architecture:

### LangGraph Interview Flow

The interview process is managed by a state machine with the following nodes:

1. **analyze_documents**: Analyzes the candidate's resume and job description to create a tailored interview strategy
2. **generate_question**: Generates contextual interview questions based on the strategy and conversation history
3. **process_answer**: Evaluates candidate responses and determines if follow-up questions are needed
4. **check_time**: Monitors the 30-minute time limit
5. **conclude_interview**: Gracefully ends the interview with an appropriate closing message

#### State Flow

```
START → analyze_documents → generate_question → check_time
                                                     ↓
                                        (time check passes)
                                                     ↓
                        ← ← ← ← ← ← ← ← ← process_answer
                        ↓
                (route decision)
                        ↓
        generate_question OR conclude_interview → END
```

#### Conditional Routing

- **check_time node**: Routes to "process_answer" if within time limits, otherwise to "conclude"
- **process_answer node**: Routes to "generate_question" for next question or "conclude" if limits reached

### Key Features

- **Stateful Conversation**: LangGraph manages conversation state across multiple interactions
- **Adaptive Questioning**: Questions adapt based on resume, job description, and previous answers
- **Time Management**: Automatic 30-minute interview limit enforcement
- **Document Processing**: Supports PDF and DOCX formats for resumes and job descriptions
- **Audio Transcription**: OpenAI Whisper integration for speech-to-text

## Project Structure

```
backend/
├── main.py                 # FastAPI application with all endpoints
├── interview_graph.py      # LangGraph state machine implementation
├── models.py              # Pydantic models for API and state management
├── document_processor.py  # PDF and DOCX text extraction
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- OpenAI API key

### Step 1: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the backend directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### Step 4: Run the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Step 5: Verify Installation

Open your browser and navigate to:
- API docs: `http://localhost:8000/docs` (Swagger UI)
- Alternative docs: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/`

## API Endpoints

### 1. Upload Documents
**POST** `/upload-documents`

Upload resume and job description to create an interview session.

**Request**: `multipart/form-data`
- `resume`: File (PDF or DOCX)
- `job_description`: File (PDF or DOCX)

**Response**:
```json
{
  "session_id": "uuid",
  "message": "Documents uploaded and processed successfully",
  "resume_length": 1234,
  "job_description_length": 567
}
```

### 2. Start Interview
**POST** `/start-interview`

Initialize the interview and get the first question.

**Request**:
```json
{
  "session_id": "uuid"
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "first_question": "Tell me about your experience with...",
  "message": "Interview started successfully"
}
```

### 3. Transcribe Audio
**POST** `/transcribe-audio`

Convert audio to text using OpenAI Whisper.

**Request**: `multipart/form-data`
- `audio`: Audio file (various formats supported)

**Response**:
```json
{
  "transcribed_text": "My answer is..."
}
```

### 4. Submit Answer
**POST** `/submit-answer`

Submit candidate's answer and get the next question.

**Request**:
```json
{
  "session_id": "uuid",
  "answer": "My experience includes..."
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "next_question": "Can you elaborate on...",
  "is_concluded": false,
  "conclusion_message": null,
  "time_remaining_seconds": 1500
}
```

### 5. Interview Status
**GET** `/interview-status/{session_id}`

Get current status of an interview session.

**Response**:
```json
{
  "session_id": "uuid",
  "is_active": true,
  "is_concluded": false,
  "questions_asked": 5,
  "time_elapsed_seconds": 300,
  "time_remaining_seconds": 1500,
  "conclusion_reason": null
}
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` (required): Your OpenAI API key
- `OPENAI_MODEL` (optional): OpenAI model to use (default: "gpt-4o-mini")
- `WHISPER_MODEL` (optional): Whisper model for transcription (default: "whisper-1")

### Interview Settings

You can modify these in `interview_graph.py`:

- `MAX_INTERVIEW_TIME_SECONDS`: Maximum interview duration (default: 1800 seconds / 30 minutes)
- `MAX_QUESTIONS`: Maximum number of questions to ask (default: 15)

### Model Configuration

The default model is `gpt-4o-mini` for cost-effectiveness. For better quality, you can use:
- `gpt-4o`: Latest GPT-4 Omni model
- `gpt-4-turbo`: Fast GPT-4 variant

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (create test files first)
pytest
```

### Code Style

The project follows Python best practices:
- Type hints for better IDE support
- Docstrings for all functions
- Proper error handling and logging
- Modular architecture

### Logging

Logs are written to stdout with INFO level by default. You can adjust logging in each module:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # More verbose
```

## Troubleshooting

### Issue: "OPENAI_API_KEY not found"
- Ensure `.env` file exists in the backend directory
- Verify the API key is correctly set in `.env`
- Check that `python-dotenv` is installed

### Issue: "Document processing failed"
- Verify the uploaded file is a valid PDF or DOCX
- Check file is not corrupted or password-protected
- Ensure file contains extractable text (not just images)

### Issue: "Failed to start interview"
- Verify OpenAI API key is valid and has credits
- Check network connectivity
- Review logs for specific error messages

### Issue: Port 8000 already in use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn main:app --port 8001
```

## Production Considerations

For production deployment:

1. **Database**: Replace in-memory session storage with Redis or PostgreSQL
2. **File Storage**: Use S3 or similar for uploaded documents
3. **Authentication**: Add API key or OAuth authentication
4. **Rate Limiting**: Implement rate limiting to prevent abuse
5. **CORS**: Restrict allowed origins in production
6. **HTTPS**: Use reverse proxy (nginx) with SSL certificates
7. **Monitoring**: Add application monitoring (Sentry, DataDog, etc.)
8. **Scaling**: Use multiple workers with Gunicorn

Example production command:
```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Technology Stack

- **FastAPI**: Modern web framework for building APIs
- **LangGraph**: State machine for multi-agent workflows
- **LangChain**: LLM orchestration and tooling
- **OpenAI**: GPT models for conversation, Whisper for transcription
- **Pydantic**: Data validation and settings management
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX text extraction

## License

This project is part of the xquizit interview system.

## Support

For issues or questions, please check the logs and API documentation first. Common issues are covered in the Troubleshooting section above.
