// API configuration
export const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  UPLOAD_DOCUMENTS: '/upload-documents',
  START_INTERVIEW: '/start-interview',
  TRANSCRIBE_AUDIO: '/transcribe-audio',
  SUBMIT_ANSWER: '/submit-answer',
  INTERVIEW_STATUS: '/interview-status',
};

export const INTERVIEW_DURATION_MS = 30 * 60 * 1000; // 30 minutes in milliseconds
export const INTERVIEW_DURATION_SECONDS = 30 * 60; // 30 minutes in seconds
