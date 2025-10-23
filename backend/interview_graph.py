"""
Interview Graph Module
LangGraph-based multi-agent architecture for conducting screening interviews.
"""

import logging
import time
from typing import Literal, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from models import InterviewState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Interview configuration
MAX_INTERVIEW_TIME_SECONDS = 30 * 60  # 30 minutes
MAX_QUESTIONS = 16 # Reasonable limit to prevent infinite loops


class InterviewGraphBuilder:
    """Builds and manages the LangGraph interview workflow."""

    def __init__(self, gemini_api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize the interview graph builder.

        Args:
            gemini_api_key: Google Gemini API key
            model_name: Gemini model to use (default: gemini-2.5-flash)
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
            google_api_key=gemini_api_key
        )
        self.graph = None
        self._build_graph()

    def _build_graph(self):
        """Build the LangGraph state machine for interviews."""
        builder = StateGraph(InterviewState)

        # Add nodes
        builder.add_node("analyze_documents", self._analyze_documents)
        builder.add_node("generate_question", self._generate_question)
        builder.add_node("process_answer", self._process_answer)
        builder.add_node("check_time", self._check_time)
        builder.add_node("conclude_interview", self._conclude_interview)

        # Define edges
        # Start with document analysis
        builder.add_edge(START, "analyze_documents")

        # After analysis, generate first question
        builder.add_edge("analyze_documents", "generate_question")

        # After generating question, check time constraints
        builder.add_edge("generate_question", "check_time")

        # Add conditional edges from check_time
        builder.add_conditional_edges(
            "check_time",
            self._should_continue_or_end,
            {
                "wait_for_answer": END,  # Stop and wait for user input
                "process_answer": "process_answer",
                "conclude": "conclude_interview",
            }
        )

        # After processing answer, decide next action
        builder.add_conditional_edges(
            "process_answer",
            self._route_after_answer,
            {
                "generate_question": "generate_question",
                "conclude": "conclude_interview",
            }
        )

        # Conclude ends the interview
        builder.add_edge("conclude_interview", END)

        # Compile the graph
        self.graph = builder.compile()
        logger.info("Interview graph compiled successfully")

    def _analyze_documents(self, state: InterviewState) -> Dict[str, Any]:
        """
        Analyze resume and job description to create interview strategy.

        Args:
            state: Current interview state

        Returns:
            Updated state with interview strategy
        """
        logger.info(f"Analyzing documents for session {state['session_id']}")

        system_prompt = """You are an expert technical interviewer. Analyze the candidate's resume and the job description.

        Your task:
        1. Identify key skills and experiences in the resume that match the job requirements
        2. Identify potential gaps or areas to explore
        3. Create a focused interview strategy with 3-5 key topics to cover
        4. Prioritize topics that will best assess the candidate's fit for the role

        Provide a clear, structured analysis."""

        user_prompt = f"""Resume:
{state['resume_text']}

Job Description:
{state['job_description_text']}

Based on the above, provide:
1. Key matching qualifications
2. Areas to explore in depth
3. 3-5 specific topics for interview questions"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages)
        strategy = response.content

        # Extract key topics (simplified - in production, use structured output)
        topics = self._extract_topics(strategy)

        logger.info(f"Generated interview strategy with {len(topics)} topics")

        return {
            "interview_strategy": strategy,
            "key_topics": topics,
            "messages": [{"role": "system", "content": strategy}]
        }

    def _extract_topics(self, strategy: str) -> list[str]:
        """Extract key topics from strategy text."""
        # Simple extraction - look for numbered or bulleted lists
        topics = []
        lines = strategy.split('\n')
        for line in lines:
            line = line.strip()
            # Look for lines that might be topics
            if any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '*']):
                # Clean up the topic
                topic = line.lstrip('0123456789.-* ').strip()
                if len(topic) > 10 and len(topics) < 5:  # Reasonable topic length
                    topics.append(topic)

        # Default topics if extraction fails
        if not topics:
            topics = ["Technical skills", "Experience and background", "Problem-solving approach"]

        return topics

    def _generate_question(self, state: InterviewState) -> Dict[str, Any]:
        """
        Generate the next interview question based on context.

        Args:
            state: Current interview state

        Returns:
            Updated state with new question
        """
        questions_asked = state.get("questions_asked", 0)
        logger.info(f"Generating question #{questions_asked + 1} for session {state['session_id']}")

        # Check if we need to generate a follow-up question
        if state.get("needs_followup", False):
            current_topic = state.get("current_topic", "the previous topic")

            # Check follow-up count for this topic
            topic_followup_counts = state.get("topic_followup_counts", {})
            followup_count = topic_followup_counts.get(current_topic, 0)

            # Maximum 2 follow-ups per topic
            if followup_count >= 2:
                logger.info(f"Max follow-ups (2) reached for topic '{current_topic}', moving to next topic")
                # Reset flag and continue to new topic generation below
                # Don't return here, fall through to generate new topic question
            else:
                # Extract ONLY the Q&A for the current topic
                messages = state.get("messages", [])
                topic_conversation = []

                # Go through messages and find ones related to current topic
                for msg in messages:
                    if isinstance(msg, dict):
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        msg_topic = msg.get("topic", "")
                    else:
                        msg_type = type(msg).__name__
                        if msg_type == "HumanMessage":
                            role = "user"
                        elif msg_type == "AIMessage":
                            role = "assistant"
                        else:
                            continue
                        content = msg.content if hasattr(msg, 'content') else ""
                        msg_topic = getattr(msg, 'topic', '') if hasattr(msg, 'topic') else ""

                    # Only include messages for current topic
                    if msg_topic == current_topic and role in ["assistant", "user"]:
                        speaker = "Interviewer" if role == "assistant" else "Candidate"
                        topic_conversation.append(f"{speaker}: {content}")

                topic_context = "\n".join(topic_conversation) if topic_conversation else "First question on this topic"

                system_prompt = f"""You are conducting a professional screening interview.

Current Topic: {current_topic}

Generate ONE focused follow-up question that:
1. Digs deeper into their most recent answer on THIS topic
2. Asks for specific examples, details, or clarification
3. Explores impact, challenges, or results
4. Stays strictly on topic: {current_topic}
5. Is conversational and natural

Just provide the question, no commentary."""

                user_prompt = f"""Conversation on THIS topic so far (Follow-up #{followup_count + 1} of max 2):
{topic_context}

Generate a follow-up question based on the conversation above."""

                messages_for_llm = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = self.llm.invoke(messages_for_llm)
                question = response.content.strip()

                logger.info(f"Generated follow-up #{followup_count + 1} for topic '{current_topic}': {question[:100]}...")

                # Update follow-up count for this topic
                topic_followup_counts[current_topic] = followup_count + 1

                return {
                    "current_question": question,
                    "current_topic": current_topic,
                    "questions_asked": questions_asked + 1,
                    "needs_followup": False,
                    "topic_followup_counts": topic_followup_counts,
                    "messages": [{"role": "assistant", "content": question, "topic": current_topic}]
                }

        # Special handling for first question - always introductory
        if questions_asked == 0:
            system_prompt = """You are starting a professional screening interview.

Generate a warm, welcoming introductory question that:
1. Invites the candidate to introduce themselves
2. Sets a conversational, friendly tone
3. Allows them to share relevant background and experience
4. Is professional but not intimidating

Examples of good introductory questions:
- "Thanks for joining us today! To start, could you tell me a bit about yourself and what drew you to this position?"
- "Welcome! I'd love to hear about your background and what excites you about this role."
- "Let's begin - can you walk me through your professional journey and what brings you here today?"

Generate ONE similar introductory question. Just provide the question itself, no additional commentary."""

            user_prompt = "Please generate a welcoming introductory interview question."

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = self.llm.invoke(messages)
            question = response.content.strip()

            logger.info(f"Generated introductory question: {question[:100]}...")

            return {
                "current_question": question,
                "current_topic": "introduction",
                "questions_asked": 1,
                "messages": [{"role": "assistant", "content": question, "topic": "introduction"}]
            }

        # Determine which topic to focus on for subsequent questions
        topics = state.get("key_topics", [])
        current_topic_idx = (questions_asked - 1) % len(topics) if topics else 0
        current_topic = topics[current_topic_idx] if topics else "general background"

        # Track which topics have been covered
        covered_topics = []
        remaining_topics = []
        if topics:
            for i, topic in enumerate(topics):
                if i < current_topic_idx:
                    covered_topics.append(topic)
                elif i > current_topic_idx:
                    remaining_topics.append(topic)

        system_prompt = f"""You are conducting a professional screening interview.

Interview Strategy:
{state.get('interview_strategy', 'General screening interview')}

Topic Progress:
- Topics already explored: {', '.join(covered_topics) if covered_topics else 'None yet'}
- CURRENT FOCUS: {current_topic}
- Topics remaining: {', '.join(remaining_topics) if remaining_topics else 'None (revisiting covered topics)'}

Generate ONE clear, focused interview question that:
1. Focuses on: {current_topic}
2. Allows the candidate to demonstrate their skills and experience
3. Is conversational and professional
4. Builds naturally on the conversation so far

Just provide the question itself, no additional commentary."""

        # Build conversation history for context
        conversation_context = self._build_conversation_context(state.get("messages", []))

        user_prompt = f"""Based on the conversation so far, generate the next interview question focusing on: {current_topic}

Previous conversation:
{conversation_context}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages)
        question = response.content.strip()

        logger.info(f"Generated question: {question[:100]}...")

        return {
            "current_question": question,
            "current_topic": current_topic,
            "questions_asked": questions_asked + 1,
            "messages": [{"role": "assistant", "content": question, "topic": current_topic}]
        }

    def _build_conversation_context(self, messages: list) -> str:
        """Build a readable conversation context from messages."""
        if not messages:
            return "This is the first question."

        context_lines = []
        for msg in messages:  
            # Handle both dict messages and LangChain message objects
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
            else:
                # Handle LangChain message objects (SystemMessage, HumanMessage, AIMessage)
                msg_type = type(msg).__name__
                if msg_type == "HumanMessage":
                    role = "user"
                elif msg_type == "AIMessage":
                    role = "assistant"
                elif msg_type == "SystemMessage":
                    role = "system"
                else:
                    role = "unknown"
                content = msg.content if hasattr(msg, 'content') else ""

            # Format for display
            if role == "assistant":
                context_lines.append(f"Interviewer: {content}")
            elif role == "user":
                context_lines.append(f"Candidate: {content}")

        return "\n".join(context_lines) if context_lines else "This is the first question."

    def _process_answer(self, state: InterviewState) -> Dict[str, Any]:
        """
        Process candidate's answer and determine if follow-up is needed.

        Args:
            state: Current interview state

        Returns:
            Updated state with follow-up decision
        """
        logger.info(f"Processing answer for session {state['session_id']}")

        # Get the last message (candidate's answer)
        messages = state.get("messages", [])
        if not messages:
            logger.warning("No messages found to process")
            return {"needs_followup": False}

        last_msg = messages[-1]
        # Check if last message is from user (HumanMessage)
        if isinstance(last_msg, dict):
            is_user = last_msg.get("role") == "user"
            candidate_answer = last_msg.get("content", "")
        else:
            is_user = type(last_msg).__name__ == "HumanMessage"
            candidate_answer = last_msg.content if hasattr(last_msg, 'content') else ""

        if not is_user:
            logger.warning("Last message is not from candidate")
            return {"needs_followup": False}

        system_prompt = """You are evaluating a candidate's interview answer.

        Analyze the answer and determine:
        1. Is the answer complete and substantive?
        2. Does it demonstrate relevant experience?
        3. Would a follow-up question add significant value?

        Respond with ONLY 'yes' if a follow-up would be valuable, or 'no' if the answer is sufficient."""

        user_prompt = f"""Question: {state.get('current_question', '')}

Candidate's Answer: {candidate_answer}

Should we ask a follow-up question? (yes/no)"""

        messages_for_llm = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages_for_llm)
        needs_followup = 'yes' in response.content.lower()

        logger.info(f"Follow-up needed: {needs_followup}")

        return {
            "needs_followup": needs_followup
        }

    def _check_time(self, state: InterviewState) -> Dict[str, Any]:
        """
        Check if interview time limit has been reached.

        Args:
            state: Current interview state

        Returns:
            Updated state with time information
        """
        current_time = time.time()
        start_time = state.get("start_time", current_time)
        time_elapsed = current_time - start_time

        logger.info(f"Time check: {time_elapsed:.2f} seconds elapsed")

        return {
            "time_elapsed": time_elapsed,
            "start_time": start_time  # Ensure start_time is set
        }

    def _should_continue_or_end(self, state: InterviewState) -> Literal["wait_for_answer", "process_answer", "conclude"]:
        """
        Determine if interview should continue or conclude.

        Args:
            state: Current interview state

        Returns:
            Next node to route to
        """
        time_elapsed = state.get("time_elapsed", 0)
        questions_asked = state.get("questions_asked", 0)

        # Check if we've exceeded time limit
        if time_elapsed >= MAX_INTERVIEW_TIME_SECONDS:
            logger.info("Time limit reached, concluding interview")
            # Don't mutate state in conditional edge - just route
            return "conclude"

        # Check if we've asked too many questions
        if questions_asked >= MAX_QUESTIONS:
            logger.info("Maximum questions reached, concluding interview")
            # Don't mutate state in conditional edge - just route
            return "conclude"

        # Check if this is just after generating a question (waiting for answer)
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            # Check if last message is from assistant (AIMessage)
            if isinstance(last_msg, dict):
                is_assistant = last_msg.get("role") == "assistant"
            else:
                is_assistant = type(last_msg).__name__ == "AIMessage"

            if is_assistant:
                logger.info("Waiting for candidate answer")
                return "wait_for_answer"  # Stop and wait for user input

        return "wait_for_answer"  # Default: wait for answer

    def _route_after_answer(self, state: InterviewState) -> Literal["generate_question", "conclude"]:
        """
        Route to next node after processing an answer.

        Args:
            state: Current interview state

        Returns:
            Next node to route to
        """
        time_elapsed = state.get("time_elapsed", 0)
        questions_asked = state.get("questions_asked", 0)

        # Check time and question limits again
        if time_elapsed >= MAX_INTERVIEW_TIME_SECONDS:
            state["conclusion_reason"] = "time_limit"
            return "conclude"

        if questions_asked >= MAX_QUESTIONS:
            state["conclusion_reason"] = "max_questions"
            return "conclude"

        # If interview is explicitly concluded
        if state.get("is_concluded", False):
            return "conclude"

        # Continue with next question
        return "generate_question"

    def _conclude_interview(self, state: InterviewState) -> Dict[str, Any]:
        """
        Generate conclusion message for the interview.

        Args:
            state: Current interview state

        Returns:
            Updated state with conclusion
        """
        logger.info(f"Concluding interview for session {state['session_id']}")

        # Determine conclusion reason based on state
        time_elapsed = state.get("time_elapsed", 0)
        questions_asked = state.get("questions_asked", 0)

        if time_elapsed >= MAX_INTERVIEW_TIME_SECONDS:
            reason = "time_limit"
        elif questions_asked >= MAX_QUESTIONS:
            reason = "max_questions"
        else:
            reason = state.get("conclusion_reason", "completed")

        if reason == "time_limit":
            conclusion_message = f"Thank you for your time! We've reached the 30-minute mark for this screening interview. We covered {questions_asked} areas, and I appreciate your detailed responses. We'll be in touch soon regarding next steps."
        elif reason == "max_questions":
            conclusion_message = f"Thank you so much for your thoughtful answers! We've covered {questions_asked} important topics today. I have all the information I need for this screening round. We'll review your responses and get back to you soon about next steps."
        else:
            conclusion_message = "Thank you for taking the time to interview with us today. We appreciate your interest in the position and will be in touch regarding next steps."

        logger.info(f"Interview concluded successfully with reason: {reason}")

        return {
            "is_concluded": True,
            "conclusion_reason": reason,
            "current_question": conclusion_message,
            "messages": [{"role": "assistant", "content": conclusion_message}]
        }

    def invoke(self, initial_state: Dict[str, Any]) -> InterviewState:
        """
        Run the interview graph with initial state.

        Args:
            initial_state: Initial state for the interview

        Returns:
            Final interview state
        """
        try:
            logger.info(f"Starting interview graph for session {initial_state.get('session_id')}")
            result = self.graph.invoke(initial_state)
            logger.info("Interview graph execution completed")
            return result
        except Exception as e:
            logger.error(f"Error executing interview graph: {str(e)}", exc_info=True)
            raise


def create_interview_graph(gemini_api_key: str, model_name: str = "gemini-2.5-flash") -> InterviewGraphBuilder:
    """
    Factory function to create an interview graph.

    Args:
        gemini_api_key: Google Gemini API key
        model_name: Gemini model to use

    Returns:
        Configured InterviewGraphBuilder instance
    """
    return InterviewGraphBuilder(gemini_api_key=gemini_api_key, model_name=model_name)
