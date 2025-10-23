import { useState } from 'react';
import axios from 'axios';
import { API_BASE_URL, API_ENDPOINTS } from '../config';
import './UploadScreen.css';

const UploadScreen = ({ onInterviewStart }) => {
  const [resume, setResume] = useState(null);
  const [jobDescription, setJobDescription] = useState(null);
  const [resumeDragActive, setResumeDragActive] = useState(false);
  const [jobDescDragActive, setJobDescDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  const validateFile = (file) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'
    ];
    const validExtensions = ['.pdf', '.docx', '.doc'];

    const isValidType = validTypes.includes(file.type);
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

    return isValidType || hasValidExtension;
  };

  const handleFileDrop = (e, type) => {
    e.preventDefault();
    if (type === 'resume') {
      setResumeDragActive(false);
    } else {
      setJobDescDragActive(false);
    }

    const file = e.dataTransfer.files[0];
    if (file && validateFile(file)) {
      if (type === 'resume') {
        setResume(file);
      } else {
        setJobDescription(file);
      }
      setError(null);
    } else {
      setError('Invalid file type. Please upload a PDF or DOCX file.');
    }
  };

  const handleFileSelect = (e, type) => {
    const file = e.target.files[0];
    if (file && validateFile(file)) {
      if (type === 'resume') {
        setResume(file);
      } else {
        setJobDescription(file);
      }
      setError(null);
    } else {
      setError('Invalid file type. Please upload a PDF or DOCX file.');
    }
  };

  const handleDragOver = (e, type) => {
    e.preventDefault();
    if (type === 'resume') {
      setResumeDragActive(true);
    } else {
      setJobDescDragActive(true);
    }
  };

  const handleDragLeave = (e, type) => {
    e.preventDefault();
    if (type === 'resume') {
      setResumeDragActive(false);
    } else {
      setJobDescDragActive(false);
    }
  };

  const handleStartInterview = async () => {
    if (!resume || !jobDescription) {
      setError('Please upload both resume and job description.');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      // Upload documents
      const formData = new FormData();
      formData.append('resume', resume);
      formData.append('job_description', jobDescription);

      const uploadResponse = await axios.post(
        `${API_BASE_URL}${API_ENDPOINTS.UPLOAD_DOCUMENTS}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      const sessionId = uploadResponse.data.session_id;

      // Start interview
      const interviewResponse = await axios.post(
        `${API_BASE_URL}${API_ENDPOINTS.START_INTERVIEW}`,
        { session_id: sessionId }
      );

      const firstQuestion = interviewResponse.data.first_question;

      // Pass session ID and first question to parent
      onInterviewStart({
        sessionId,
        firstQuestion,
        startTime: Date.now(),
      });
    } catch (err) {
      console.error('Error starting interview:', err);
      setError(
        err.response?.data?.detail ||
        'Failed to start interview. Please try again.'
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-screen">
      <div className="upload-container">
        <div className="upload-header">
          <h1>AI Screening Interview</h1>
          <p>Upload your resume and the job description to begin the interview</p>
        </div>

        {error && (
          <div className="upload-error">
            {error}
          </div>
        )}

        <div className="upload-sections">
          {/* Resume Upload */}
          <div className="upload-section">
            <h2>Resume</h2>
            <div
              className={`upload-dropzone ${resumeDragActive ? 'drag-active' : ''} ${resume ? 'has-file' : ''}`}
              onDrop={(e) => handleFileDrop(e, 'resume')}
              onDragOver={(e) => handleDragOver(e, 'resume')}
              onDragLeave={(e) => handleDragLeave(e, 'resume')}
            >
              {resume ? (
                <div className="file-info">
                  <div className="file-icon">📄</div>
                  <div className="file-details">
                    <div className="file-name">{resume.name}</div>
                    <div className="file-size">
                      {(resume.size / 1024).toFixed(2)} KB
                    </div>
                  </div>
                  <button
                    className="file-remove"
                    onClick={() => setResume(null)}
                    aria-label="Remove resume"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <div className="dropzone-content">
                  <div className="upload-icon">📤</div>
                  <p>Drag and drop your resume here</p>
                  <p className="upload-hint">or</p>
                  <label className="file-select-button">
                    Choose File
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx"
                      onChange={(e) => handleFileSelect(e, 'resume')}
                      hidden
                    />
                  </label>
                  <p className="file-types">Supported: PDF, DOCX</p>
                </div>
              )}
            </div>
          </div>

          {/* Job Description Upload */}
          <div className="upload-section">
            <h2>Job Description</h2>
            <div
              className={`upload-dropzone ${jobDescDragActive ? 'drag-active' : ''} ${jobDescription ? 'has-file' : ''}`}
              onDrop={(e) => handleFileDrop(e, 'jobDescription')}
              onDragOver={(e) => handleDragOver(e, 'jobDescription')}
              onDragLeave={(e) => handleDragLeave(e, 'jobDescription')}
            >
              {jobDescription ? (
                <div className="file-info">
                  <div className="file-icon">📄</div>
                  <div className="file-details">
                    <div className="file-name">{jobDescription.name}</div>
                    <div className="file-size">
                      {(jobDescription.size / 1024).toFixed(2)} KB
                    </div>
                  </div>
                  <button
                    className="file-remove"
                    onClick={() => setJobDescription(null)}
                    aria-label="Remove job description"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <div className="dropzone-content">
                  <div className="upload-icon">📤</div>
                  <p>Drag and drop job description here</p>
                  <p className="upload-hint">or</p>
                  <label className="file-select-button">
                    Choose File
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx"
                      onChange={(e) => handleFileSelect(e, 'jobDescription')}
                      hidden
                    />
                  </label>
                  <p className="file-types">Supported: PDF, DOCX</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <button
          className="start-interview-button"
          onClick={handleStartInterview}
          disabled={!resume || !jobDescription || isUploading}
        >
          {isUploading ? (
            <>
              <div className="button-spinner"></div>
              Starting Interview...
            </>
          ) : (
            'Start Interview'
          )}
        </button>
      </div>
    </div>
  );
};

export default UploadScreen;
