import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL, API_ENDPOINTS, INTERVIEW_DURATION_SECONDS } from '../config';
import Timer from './Timer';
import Message from './Message';
import AudioRecorder from './AudioRecorder';
import './ChatInterface.css';

const ChatInterface = ({ sessionId, firstQuestion, startTime }) => {
  const [messages, setMessages] = useState([]);
  const [isWaitingForQuestion, setIsWaitingForQuestion] = useState(false);
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [currentQuestionNumber, setCurrentQuestionNumber] = useState(1);

  const messagesEndRef = useRef(null);
  const messageIdCounter = useRef(1);
  const processingRef = useRef(false);  // Prevent race conditions

  // Initialize with first question
  useEffect(() => {
    if (firstQuestion) {
      setMessages([
        {
          id: messageIdCounter.current++,
          sender: 'interviewer',
          text: firstQuestion,
          timestamp: new Date(),
        },
      ]);
    }
  }, [firstQuestion]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check interview time
  useEffect(() => {
    const checkTime = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      if (elapsed >= INTERVIEW_DURATION_SECONDS) {
        setInterviewComplete(true);
        clearInterval(checkTime);
      }
    }, 1000);

    return () => clearInterval(checkTime);
  }, [startTime]);

  const handleTranscriptionComplete = async (transcription) => {
    // Prevent concurrent processing
    if (processingRef.current) {
      console.warn('Already processing an answer, ignoring new transcription');
      return;
    }

    processingRef.current = true;

    // Add candidate's answer to messages
    const candidateMessage = {
      id: messageIdCounter.current++,
      sender: 'candidate',
      text: transcription,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, candidateMessage]);

    // Submit answer and get next question
    setIsWaitingForQuestion(true);

    try {
      const response = await axios.post(
        `${API_BASE_URL}${API_ENDPOINTS.SUBMIT_ANSWER}`,
        {
          session_id: sessionId,
          answer: transcription,
        }
      );

      // Handle conclusion and next question - mutually exclusive
      if (response.data.is_concluded) {
        setInterviewComplete(true);
        // Only show conclusion message when concluded
        if (response.data.conclusion_message) {
          const conclusionMessage = {
            id: messageIdCounter.current++,
            sender: 'interviewer',
            text: response.data.conclusion_message,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, conclusionMessage]);
        }
      } else if (response.data.next_question) {
        // Only show next question if NOT concluded
        const interviewerMessage = {
          id: messageIdCounter.current++,
          sender: 'interviewer',
          text: response.data.next_question,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, interviewerMessage]);
        setCurrentQuestionNumber((prev) => prev + 1);
      }
    } catch (err) {
      console.error('Error submitting answer:', err);
      // Add error message
      const errorMessage = {
        id: messageIdCounter.current++,
        sender: 'interviewer',
        text: 'There was an error processing your answer. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsWaitingForQuestion(false);
      processingRef.current = false;  // Reset processing flag
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h1>Screening Interview</h1>
        <div className="interview-progress">
          Question {currentQuestionNumber}
        </div>
      </div>

      <Timer startTime={startTime} totalDuration={INTERVIEW_DURATION_SECONDS} />

      <div className="chat-messages">
        {messages.map((message) => (
          <Message
            key={message.id}
            sender={message.sender}
            text={message.text}
            timestamp={message.timestamp}
          />
        ))}

        {isWaitingForQuestion && (
          <div className="typing-indicator">
            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="typing-text">Interviewer is typing...</span>
          </div>
        )}

        {interviewComplete && (
          <div className="interview-complete">
            <div className="complete-icon">✓</div>
            <h2>Interview Complete</h2>
            <p>Thank you for completing the screening interview. Your responses have been recorded.</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {!interviewComplete && (
        <AudioRecorder
          sessionId={sessionId}
          onTranscriptionComplete={handleTranscriptionComplete}
          disabled={isWaitingForQuestion || processingRef.current}
        />
      )}
    </div>
  );
};

export default ChatInterface;
