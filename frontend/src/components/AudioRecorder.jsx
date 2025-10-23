import { useState, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL, API_ENDPOINTS } from '../config';
import './AudioRecorder.css';

const AudioRecorder = ({ sessionId, onTranscriptionComplete, disabled }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    // Prevent starting if already recording or transcribing
    if (isRecording || isTranscribing) {
      console.warn('Already recording or transcribing');
      return;
    }

    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioForTranscription(audioBlob);

        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      if (err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow microphone permissions.');
      } else if (err.name === 'NotFoundError') {
        setError('No microphone found. Please connect a microphone.');
      } else {
        setError('Error accessing microphone. Please try again.');
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendAudioForTranscription = async (audioBlob) => {
    setIsTranscribing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('session_id', sessionId);

      const response = await axios.post(
        `${API_BASE_URL}${API_ENDPOINTS.TRANSCRIBE_AUDIO}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      if (response.data.transcription) {
        onTranscriptionComplete(response.data.transcription);
      } else {
        setError('Transcription failed. Please try again.');
      }
    } catch (err) {
      console.error('Error transcribing audio:', err);
      setError('Failed to transcribe audio. Please try again.');
    } finally {
      setIsTranscribing(false);
    }
  };

  return (
    <div className="audio-recorder">
      {error && (
        <div className="audio-recorder-error">
          {error}
        </div>
      )}

      <div className="audio-recorder-controls">
        {!isRecording && !isTranscribing && (
          <button
            className="record-button"
            onClick={startRecording}
            disabled={disabled}
            aria-label="Start recording"
          >
            <div className="record-icon"></div>
            <span>Record Answer</span>
          </button>
        )}

        {isRecording && (
          <button
            className="stop-button"
            onClick={stopRecording}
            aria-label="Stop recording"
          >
            <div className="stop-icon"></div>
            <span>Stop Recording</span>
          </button>
        )}

        {isTranscribing && (
          <div className="transcribing-indicator">
            <div className="spinner"></div>
            <span>Transcribing...</span>
          </div>
        )}
      </div>

      {isRecording && (
        <div className="recording-indicator">
          <div className="recording-pulse"></div>
          <span>Recording in progress...</span>
        </div>
      )}
    </div>
  );
};

export default AudioRecorder;
