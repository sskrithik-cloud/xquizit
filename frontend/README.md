# Screening Interview Chatbot - Frontend

A modern React-based frontend for conducting AI-powered screening interviews with voice recording capabilities.

## Features

- **Document Upload**: Drag-and-drop or file picker for resume and job description (PDF/DOCX)
- **Voice Recording**: Browser-based audio recording with transcription
- **Real-time Chat**: Clean chat interface with distinct interviewer/candidate message styling
- **Timer**: Visual countdown showing elapsed time out of 30 minutes
- **Progress Tracking**: Question counter and progress indicators
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Accessibility**: WCAG 2.1 AA compliant with proper ARIA labels and keyboard navigation

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Axios** - HTTP client for API calls
- **MediaRecorder API** - Browser-based audio recording
- **CSS3** - Modern styling with gradients and animations

## Prerequisites

- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`
- Modern browser with microphone support

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## Running the Application

1. Start the development server:
```bash
npm run dev
```

2. Open your browser and navigate to:
```
http://localhost:5173
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── UploadScreen.jsx       # Document upload interface
│   │   ├── UploadScreen.css
│   │   ├── ChatInterface.jsx      # Main interview chat interface
│   │   ├── ChatInterface.css
│   │   ├── AudioRecorder.jsx      # Voice recording component
│   │   ├── AudioRecorder.css
│   │   ├── Message.jsx            # Reusable message bubble
│   │   ├── Message.css
│   │   ├── Timer.jsx              # Interview timer component
│   │   └── Timer.css
│   ├── App.jsx                    # Main app with state management
│   ├── App.css
│   ├── config.js                  # API configuration
│   ├── main.jsx                   # App entry point
│   └── index.css                  # Global styles
├── package.json
└── vite.config.js
```

## Component Architecture

### App.jsx
Main application component that manages the interview state and switches between UploadScreen and ChatInterface.

### UploadScreen
- Handles resume and job description uploads
- Validates file types (PDF/DOCX)
- Drag-and-drop support
- Uploads files to backend and initiates interview

### ChatInterface
- Displays conversation history
- Manages interview flow and timing
- Integrates AudioRecorder for voice responses
- Shows typing indicators and completion messages

### AudioRecorder
- Records audio using MediaRecorder API
- Sends audio to backend for transcription
- Handles microphone permissions
- Shows recording/transcribing states

### Message
- Reusable message bubble component
- Distinct styling for interviewer (blue, left) vs candidate (green, right)
- Timestamp display

### Timer
- Shows elapsed time in MM:SS format
- Visual progress bar
- Warning state at 80% (24 minutes)
- Expired state at 30 minutes

## API Integration

The frontend connects to these backend endpoints:

- `POST /upload-documents` - Upload resume and job description
- `POST /start-interview` - Get first interview question
- `POST /transcribe-audio` - Send audio for transcription
- `POST /submit-answer` - Submit answer and get next question
- `GET /interview-status/{session_id}` - Check interview status

## Browser Compatibility

- Chrome 91+
- Firefox 88+
- Safari 14+
- Edge 91+

## Microphone Permissions

The application requires microphone access for voice recording. Users will be prompted to allow microphone access when they first click the "Record Answer" button.

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Important Notes

- Ensure the backend API is running before starting the frontend
- The app uses `http://localhost:8000` as the default backend URL (configurable in `src/config.js`)
- Audio is recorded in WebM format and sent to the backend for transcription
- The interview automatically concludes after 30 minutes
- Session state is stored in component state (not persisted across page refreshes)

## Troubleshooting

### Microphone not working
- Check browser permissions
- Ensure you're using HTTPS or localhost
- Verify microphone is connected and not used by another application

### CORS errors
- Ensure backend has proper CORS configuration
- Backend should allow requests from `http://localhost:5173`

### Upload failing
- Verify file types are PDF or DOCX
- Check file size limits on backend
- Ensure backend API is running

## Future Enhancements

- Session persistence with localStorage
- Text input option alongside voice recording
- Download interview transcript
- Multi-language support
- Dark mode
