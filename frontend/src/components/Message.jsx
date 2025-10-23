import './Message.css';

const Message = ({ sender, text, timestamp }) => {
  const isInterviewer = sender === 'interviewer';

  const formatTimestamp = (date) => {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={`message ${isInterviewer ? 'message-interviewer' : 'message-candidate'}`}>
      <div className="message-bubble">
        <div className="message-header">
          <span className="message-sender">
            {isInterviewer ? 'Interviewer' : 'You'}
          </span>
          {timestamp && (
            <span className="message-timestamp">{formatTimestamp(timestamp)}</span>
          )}
        </div>
        <div className="message-text">{text}</div>
      </div>
    </div>
  );
};

export default Message;
