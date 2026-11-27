"""
AURA AI Router Engine
Intent detection, planning, tool executing, knowledge base, memory lookup, and request routing.
"""

import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime
import zoneinfo

from app.core.llm_client import llm_client
from app.memory.memory_engine import memory_engine
from app.memory.project_manager import project_manager
from app.knowledge.knowledge_manager import knowledge_manager
from app.tools.tool_manager import tool_manager
from app.database.schemas import ChatEventType, RouteDecision
from app.logs.activity_logger import activity_logger
from app.database.database import db
from app.core.quality_validator import quality_validator
from app.config import settings

logger = logging.getLogger(__name__)

# System prompt for AURA
AURA_SYSTEM_PROMPT = """You are AURA (Autonomous Universal Reasoning Agent), a super intelligent AI chatbot developed and owned by Ketan Lade.

MISSION:
You are exclusively a super intelligent, highly polished conversational assistant. 
You do not build websites, you do not write full applications, you do not have an agentic planner mode. Your sole purpose is to provide the most intelligent, thoughtful, and articulate text-based responses possible.

USER PROFILE: GENERAL
You are serving the User. 
His career goals: Full Stack Web Developer, AI SaaS platforms.
His preferred tech stack: React, Next.js, Tailwind CSS, Node.js, Spring Boot, MongoDB.
Communication Style: Be direct, practical, and focus on step-by-step implementation. Provide real-world examples.

CORE MODE: SUPER INTELLIGENT CHATBOT
Purpose: Conversation, explanations, analysis, learning, brainstorming, and answering complex queries.
Requirements: 
- Streaming responses token-by-token.
- Rich Markdown rendering (headings, bullet points, syntax-highlighted code snippets if asked).
- Tables and structured formatting for clarity.
- Long context handling and flawless memory of the conversation.

CONVERSATIONAL RULES:
- Never introduce yourself with robotic phrases. Introduce yourself naturally.
- State findings directly with concise, natural, premium language.
- Avoid robotic filler like "Let's think" or "Okay, let's begin".
- Match your response length to the complexity of the query. For simple questions, be concise. For complex queries, be thorough.
- You are a chatbot, not an autonomous agent. Do not attempt to execute multi-step plans or build projects.

MEMORY SYSTEM:
Remember previous files, previous prompts, and context from this conversation. Maintain perfect conversational continuity.
"""

# Intent classification prompt for 8 strict categories
INTENT_PROMPT = """Analyze this user message and determine the correct intent.
Possible intents:
1. CHAT: general conversation, calculations, recommendations, simple advice, planning, or trip schedules.
2. RESEARCH: searching for recent facts, information lookup, news, academic comparisons.
3. AGENT: code debugging, refactoring, systems automation, deployment, file edits.
4. WEBSITE_BUILDER: creating or building HTML/JS/CSS websites, ecommerce sites, landing pages, or portfolios.
5. APP_BUILDER: building full web apps, dashboards, CRM platforms, SaaS structures.
6. CODING: writing specific code snippets, explaining programming concepts, teaching coding.
7. FILE_ANALYSIS: uploading and asking questions on files, PDFs, logs, or databases.
8. DOCUMENT_GENERATION: creating text documents, summaries, slide decks (PPT), or reports.

User message: {message}

Respond ONLY with a JSON object in this format:
{{
    "intent": "intent_name",
    "reasoning": "brief explanation"
}}
"""


class IntentRouter:
    """Stage 1: Intent Routing. Determines category & tools."""
    def __init__(self, engine: "RouterEngine"):
        self.engine = engine

    async def classify(self, message: str) -> str:
        return await self.engine.classify_query(message)

    async def route(self, message: str) -> RouteDecision:
        return await self.engine.analyze_intent(message)


class ContextManager:
    """Stage 2: Context Gathering. Manages knowledge base & memories."""
    def __init__(self, engine: "RouterEngine"):
        self.engine = engine

    async def get_knowledge_context(self, message: str, conversation_id: str | None = None) -> str:
        try:
            kb_matches = await knowledge_manager.search_knowledge(message, conversation_id=conversation_id, limit=3)
            if kb_matches:
                items = []
                for match in kb_matches:
                    items.append(f"Source Document '{match.filename}' [Relevance: {match.score:.2f}]:\n{match.content}")
                return "\n\n--- UPLOADED KNOWLEDGE BASE DOCUMENTS ---\n" + "\n\n".join(items)
        except Exception as e:
            logger.error(f"ContextManager failed to query knowledge base: {e}")
        return ""

    async def get_memory_context(self, message: str, conversation_id: str) -> str:
        try:
            mem_matches = await memory_engine.search_memory(message, conversation_id, limit=2)
            high_rel = [m for m in mem_matches if m.relevance > 0.4]
            if high_rel:
                items = []
                for m in high_rel:
                    role_str = "User" if m.role == "user" else "Assistant"
                    items.append(f"Past Exchange ({role_str}): \"{m.content}\"")
                return "\n\n--- SEMANTIC MEMORIES RECALLED ---\n" + "\n".join(items)
        except Exception as e:
            logger.error(f"ContextManager failed to query long-term memory: {e}")
        return ""


class ToolRouter:
    """Stage 3: Tool Selection & Execution."""
    def __init__(self, engine: "RouterEngine"):
        self.engine = engine

    async def execute_tool(self, tool_name: str, tool_params: dict, conversation_id: str | None = None) -> tuple[bool, str]:
        try:
            params = {**tool_params}
            if conversation_id:
                params["conversation_id"] = conversation_id
            
            # Generate idempotency key for non-idempotent tools
            idempotency_key = None
            if tool_name in ("file_writer", "code_runner", "git", "browser_automation"):
                import hashlib
                key_data = f"{tool_name}:{conversation_id}:{str(sorted(params.items()))}"
                idempotency_key = hashlib.sha256(key_data.encode()).hexdigest()[:32]
            
            result = await tool_manager.execute(tool_name, idempotency_key=idempotency_key, **params)
            if result.success:
                return True, result.output
            return False, result.error or "Tool failed"
        except Exception as e:
            logger.error(f"ToolRouter failed executing {tool_name}: {e}")
            return False, str(e)


class AnswerValidator:
    """Stage 4: Post-Generation Response Validation."""
    def __init__(self, engine: "RouterEngine"):
        self.engine = engine

    def validate_and_clean(self, response: str) -> str:
        cleaned = response.strip()
        
        # Remove robotic greetings if they leaked through
        robotic_prefixes = [
            "Greetings. I am AURA, an Autonomous Universal Reasoning Agent.",
            "Greetings, I am AURA, an Autonomous Universal Reasoning Agent.",
            "Greetings. I am AURA.",
        ]
        for prefix in robotic_prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                
        # Remove self-chat thinking indicators
        thinking_phrases = [
            "Let's think.", "Let's synthesize.", "Okay, let's", "First, let's"
        ]
        for phrase in thinking_phrases:
            if cleaned.startswith(phrase):
                cleaned = cleaned[len(phrase):].strip()
                
        return cleaned


class RouterEngine:
    """
    Handles intent detection and request routing.

    Flow:
    1. Analyze user intent (heuristics + LLM classification fallback)
    2. Fetch long-term memory (ChromaDB) and knowledge base context (ChromaDB)
    3. Trigger planner if goal is detected
    4. Run tools (including Playwright search & subprocess Code Runner)
    5. Construct prompts and stream LLM completions
    6. Record activities in SQLite logs
    """

    def __init__(self):
        self.intent_router = IntentRouter(self)
        self.context_manager = ContextManager(self)
        self.tool_router = ToolRouter(self)
        self.answer_validator = AnswerValidator(self)

    # Keyword patterns for fast routing (avoid LLM call for obvious cases)
    TOOL_KEYWORDS = {
        "calculator": [
            "calculate", "compute", "math",
            "multiply", "divide", "add", "subtract", "sum of",
            "square root", "sqrt", "percentage",
        ],
        "system_info": [
            "system info", "system information", "cpu", "memory usage",
            "disk space", "disk usage", "ram", "uptime", "os info",
        ],
        "file_reader": [
            "read file", "read the file", "show file", "open file",
            "file contents", "cat ", "show me the file",
        ],
        "web_search": [
            "search for", "search the web", "look up", "google",
            "find out about", "search about", "web search",
        ],
        "code_runner": [
            "run script", "execute code", "run python", "run javascript",
            "run js", "test code", "execute script", "code runner",
        ],
        "knowledge_retrieval": [
            "knowledge base", "uploaded file", "uploaded document", "my document",
            "my doc", "my pdf", "uploaded pdf", "knowledge document", "pdf content",
            "in the pdf", "the uploaded pdf", "the uploaded doc", "the uploaded document",
        ],
    }

    SEARCH_TRIGGER_KEYWORDS = [
        "latest", "current", "today", "yesterday", "this week",
        "this month", "this year", "recent", "news about", "news on",
        "what happened", "update on", "price of", "stock price",
        "weather in", "score of", "who won", "results of",
        "2024", "2025", "2026",
    ]

    SEARCH_QUESTION_PATTERNS = [
        "who is ", "what is the latest", "what are the latest",
        "tell me about the recent", "what's happening with",
        "how much does", "where can i find",
        "is there any news", "has there been",
    ]

    PLANNER_KEYWORDS = [
        "plan a", "plan to", "steps to", "how to build", "create a plan",
        "decompose goal", "create website", "build website", "develop app",
        "planner goal", "goal:", "project plan", "roadmap for",
    ]

    async def analyze_intent(self, message: str) -> RouteDecision:
        """Detect user intent. Uses keyword matching first, LLM fallback second."""
        message_lower = message.lower().strip().rstrip("?.! ")

        # 1. Fast path: greetings & basic conversational phrases
        greetings = {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening", "greetings", "whats up", "what's up", "howdy"}
        conversational_phrases = [
            "how are you", "how's it going", "how is it going",
            "who are you", "what are you", "what is your name", "what's your name",
            "thank you", "thanks", "bye", "goodbye", "help me"
        ]
        
        words = [w.strip("?,.!") for w in message_lower.split()]
        is_greeting = len(words) <= 3 and any(w in greetings for w in words)
        is_conversational = any(phrase in message_lower for phrase in conversational_phrases)
        
        if is_greeting or is_conversational:
            return RouteDecision(
                needs_memory=True,
                direct_response=True,
                reasoning="Fast path conversational greeting/phrase match",
            )

        # 2. Planner Heuristics Check
        for keyword in self.PLANNER_KEYWORDS:
            if keyword in message_lower:
                return RouteDecision(
                    needs_planner=True,
                    needs_memory=True,
                    direct_response=False,
                    reasoning=f"Keyword match: '{keyword}' -> planner engine",
                )

        # 3. Tool Keywords Heuristics Check
        for tool_name, keywords in self.TOOL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    if tool_name == "web_search":
                        query = self._extract_search_query(message)
                        return RouteDecision(
                            needs_tool=True,
                            needs_search=True,
                            tool_name="web_search",
                            tool_params={"query": query},
                            needs_memory=True,
                            direct_response=False,
                            reasoning=f"Keyword match: '{keyword}' -> web_search",
                        )
                    params = self._extract_tool_params(tool_name, message)
                    return RouteDecision(
                        needs_tool=True,
                        tool_name=tool_name,
                        tool_params=params,
                        needs_memory=True,
                        needs_knowledge=(tool_name == "knowledge_retrieval"),
                        direct_response=False,
                        reasoning=f"Keyword match: '{keyword}' -> {tool_name}",
                    )

        # 4. Math expression check
        if self._looks_like_math(message):
            return RouteDecision(
                needs_tool=True,
                tool_name="calculator",
                tool_params={"expression": self._extract_math(message)},
                needs_memory=False,
                direct_response=False,
                reasoning="Detected mathematical expression -> calculator",
            )

        # 5. Search patterns check
        if self._needs_web_search(message_lower):
            query = self._extract_search_query(message)
            return RouteDecision(
                needs_tool=True,
                needs_search=True,
                tool_name="web_search",
                tool_params={"query": query},
                needs_memory=True,
                direct_response=False,
                reasoning="Detected factual or current question -> web_search",
            )

        # 6. Fallback: ask Cloud LLM to classify intent structured JSON
        try:
            tools_desc = "\n".join(
                [f"- {t.name}: {t.description}" for t in tool_manager.tools.values()]
            )
            prompt = INTENT_PROMPT.format(message=message, tools=tools_desc)
            decision_dict = await llm_client.generate_json(prompt)
            
            # Sanitise LLM outputs (ensure it didn't copy tool arguments directly into param keys)
            tool_name = decision_dict.get("tool_name")
            needs_tool = decision_dict.get("needs_tool", False)
            tool_params = decision_dict.get("tool_params", {})
            needs_knowledge = decision_dict.get("needs_knowledge", False)
            
            # Post-process knowledge base requests to route to knowledge_retrieval tool
            if needs_knowledge or tool_name == "knowledge_retrieval":
                needs_tool = True
                tool_name = "knowledge_retrieval"
                if "query" not in tool_params or not tool_params["query"]:
                    tool_params = {"query": message}
                needs_knowledge = True

            if needs_tool and tool_name == "calculator" and "expression" not in tool_params:
                # If calculator lacks 'expression' property due to 1B hallucination, extract expression
                tool_params = {"expression": self._extract_math(message)}
                
            return RouteDecision(
                needs_memory=decision_dict.get("needs_memory", True),
                needs_tool=needs_tool,
                tool_name=tool_name,
                tool_params=tool_params,
                needs_search=decision_dict.get("needs_search", False),
                needs_planner=decision_dict.get("needs_planner", False),
                needs_knowledge=needs_knowledge,
                direct_response=decision_dict.get("direct_response", True),
                reasoning=decision_dict.get("reasoning", "LLM classified routing"),
            )
        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}. Falling back to default chat routing.")

        # Default: direct LLM response with memory
        return RouteDecision(
            needs_memory=True,
            direct_response=True,
            reasoning="General conversation -> direct LLM response",
        )

    def _needs_web_search(self, message_lower: str) -> bool:
        """Check if query is real-time or factual."""
        for keyword in self.SEARCH_TRIGGER_KEYWORDS:
            if keyword in message_lower:
                return True
        for pattern in self.SEARCH_QUESTION_PATTERNS:
            if message_lower.startswith(pattern) or f" {pattern}" in message_lower:
                return True
        return False

    def _extract_search_query(self, message: str) -> str:
        """Strip prefixes and return clean search text."""
        lower = message.lower()
        prefixes = [
            "search for", "search the web for", "look up", "google",
            "find out about", "search about", "web search for",
            "can you search", "please search", "search",
        ]
        query = message
        for p in prefixes:
            if lower.startswith(p):
                query = message[len(p):].strip()
                break
        return query.rstrip("?.! ").strip()

    async def route_and_respond(
        self,
        message: str,
        conversation_id: str,
        timezone: str | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None
    ) -> AsyncGenerator[tuple[ChatEventType, str, dict | None], None]:
        """Main routing execution generator."""
        # Check settings for web search mode
        web_search_mode = "ask_first"
        try:
            row = await db.db.system_settings.find_one({"key": "web_search_mode"}, {"value": 1})
            if row:
                web_search_mode = row["value"]
        except Exception as e:
            logger.error(f"Failed to fetch web_search_mode: {e}")

        # Check if replying to search confirmation
        is_replying_to_search_prompt = False
        force_local = False
        force_web_search = False
        actual_message = message

        try:
            last_assistant_msg = await db.db.messages.find_one({"conversation_id": conversation_id, "role": "assistant"}, sort=[("created_at", -1)], projection={"content": 1})
            if last_assistant_msg:
                last_content = last_assistant_msg["content"]
                if "This may require a web search." in last_content and "Would you like:" in last_content:
                    is_replying_to_search_prompt = True
                    reply = message.strip().lower()
                    if reply in ("1", "1.", "local", "local answer", "1. local answer", "1. local"):
                        force_local = True
                    elif reply in ("2", "2.", "web", "web search", "2. web search", "2. web"):
                        force_web_search = True
        except Exception as e:
            logger.error(f"Failed to check last assistant message: {e}")
            
        if is_replying_to_search_prompt and (force_local or force_web_search):
            try:
                user_msgs = await db.db.messages.find({"conversation_id": conversation_id, "role": "user"}, projection={"content": 1}).sort("created_at", -1).limit(2).to_list(length=None)
                if len(user_msgs) >= 2:
                    actual_message = user_msgs[1]["content"]
            except Exception as e:
                logger.error(f"Failed to fetch original user query: {e}")
                actual_message = message

        # 1. Intent Routing Stage (Classify FIRST)
        category = await self.intent_router.classify(actual_message)

        # Intercept download link query
        msg_lower = actual_message.lower().strip()
        if "download link" in msg_lower or "download zip" in msg_lower or "export zip" in msg_lower or "export project" in msg_lower:
            active_project = await project_manager.get_active_project(conversation_id)
            if active_project:
                slug = active_project["slug"]
                download_url = f"http://localhost:8000/api/v1/projects/download?slug={slug}"
                response_text = f"Here is the download link for your active project **{active_project['name']}**:\n\n📥 [Download Project ZIP]({download_url})"
                yield (ChatEventType.TOKEN, response_text, None)
                await memory_engine.add_message(conversation_id, "user", message)
                await memory_engine.add_message(conversation_id, "assistant", response_text)
                yield (ChatEventType.DONE, "", None)
                return
            else:
                response_text = "No active project was found in this conversation. Please build or switch to a project first."
                yield (ChatEventType.TOKEN, response_text, None)
                await memory_engine.add_message(conversation_id, "user", message)
                await memory_engine.add_message(conversation_id, "assistant", response_text)
                yield (ChatEventType.DONE, "", None)
                return

        # Smart project detection & creation linking (Intent-Driven)
        active_project = None
        if category in ("WEBSITE_BUILDER", "APP_BUILDER", "AGENT"):
            active_project = await project_manager.get_active_project(conversation_id)
            if not active_project:
                active_project = await project_manager.detect_and_link_project(conversation_id, actual_message)

            is_create_intent = category in ("WEBSITE_BUILDER", "APP_BUILDER")
            create_trigger = False
            if active_project:
                if "new" in msg_lower and is_create_intent:
                    create_trigger = True
            else:
                if is_create_intent:
                    create_trigger = True
                    
            if create_trigger:
                import re
                match = re.search(r"create\s+(?:a|an|new)?\s+([a-zA-Z0-9_\-\s]+?)(?:\s+(?:website|app|project|store|site|dashboard|system|platform))", msg_lower)
                if match:
                    raw_name = match.group(1).strip()
                    raw_name = re.sub(r"^(?:new|simple|basic|modern|responsive)\s+", "", raw_name)
                    project_name = raw_name.title()
                    if "website" in msg_lower:
                        project_name += " Website"
                    elif "app" in msg_lower:
                        project_name += " App"
                    elif "store" in msg_lower:
                        project_name += " Store"
                    elif "dashboard" in msg_lower:
                        project_name += " Dashboard"
                else:
                    project_name = " ".join(actual_message.split()[:4]).title()
                    
                active_project = await project_manager.create_project(
                    name=project_name,
                    description=f"Generated from request: {actual_message}",
                    conversation_id=conversation_id,
                    project_type="web",
                    design_choices="Glassmorphism, dark mode, vibrant colors, harmonious layouts",
                    user_goals=f"Build and complete: {actual_message}"
                )

        # Document Upload Fast Path Bypass
        msg_lower = actual_message.lower().strip()
        if msg_lower.startswith("uploaded file:") or msg_lower.startswith("uploaded files:"):
            response_text = (
                "Document uploaded successfully.\n\n"
                "What would you like to do?\n"
                "• Summarize\n"
                "• Explain\n"
                "• Generate Notes\n"
                "• Create MCQs\n"
                "• Ask Questions"
            )
            yield (ChatEventType.TOKEN, response_text, None)
            await memory_engine.add_message(conversation_id, "user", message)
            await memory_engine.add_message(conversation_id, "assistant", response_text, {"routing": "Local fast path upload bypass"})
            yield (ChatEventType.DONE, "", None)
            return

        # Explicit Memory storage command bypass
        if category == "MEMORY":
            fact = actual_message
            for prefix in ["remember this:", "remember that:", "remember this", "remember that", "remember:"]:
                if msg_lower.startswith(prefix):
                    fact = actual_message[len(prefix):].strip().lstrip(":")
                    break
            
            from app.memory.vector_store import vector_store
            import uuid
            msg_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            if vector_store.memories_col and fact.strip():
                vector_store.memories_col.add(
                    ids=[msg_id],
                    documents=[fact],
                    metadatas=[
                        {
                            "conversation_id": conversation_id,
                            "role": "user",
                            "created_at": now,
                            "is_explicit_fact": True
                        }
                    ]
                )
            response_text = f"I've saved that to memory: \"{fact}\""
            yield (ChatEventType.TOKEN, response_text, None)
            await memory_engine.add_message(conversation_id, "user", message)
            await memory_engine.add_message(conversation_id, "assistant", response_text, {"routing": "Local explicit memory storage bypass"})
            yield (ChatEventType.DONE, "", None)
            return



        # TIME Queries: Use local system clock. Never use LLM. Never use web search.
        if category == "TIME":
            try:
                tz = zoneinfo.ZoneInfo(timezone) if timezone else None
            except Exception:
                tz = None
            now = datetime.now(tz) if tz else datetime.now().astimezone()
            time_str = now.strftime("%I:%M:%S %p %Z")
            response_text = f"The current local time is: {time_str}"
            yield (ChatEventType.TOKEN, response_text, None)
            await memory_engine.add_message(conversation_id, "user", message)
            await memory_engine.add_message(conversation_id, "assistant", response_text, {"routing": "Local clock time bypass"})
            yield (ChatEventType.DONE, "", None)
            return

        # DATE Queries: Use local system clock. Never use LLM. Never use web search.
        if category == "DATE":
            try:
                tz = zoneinfo.ZoneInfo(timezone) if timezone else None
            except Exception:
                tz = None
            now = datetime.now(tz) if tz else datetime.now().astimezone()
            date_str = now.strftime("%A, %B %d, %Y (%Z)")
            response_text = f"Today's date is: {date_str}"
            yield (ChatEventType.TOKEN, response_text, None)
            await memory_engine.add_message(conversation_id, "user", message)
            await memory_engine.add_message(conversation_id, "assistant", response_text, {"routing": "Local clock date bypass"})
            yield (ChatEventType.DONE, "", None)
            return

        # DOCUMENT Listing: Query database directly. Never use LLM.
        if category == "DOCUMENT":
            try:
                docs = await db.db.knowledge_documents.find({}, {"filename": 1, "file_size": 1, "chunk_count": 1, "upload_time": 1}).sort("upload_time", -1).to_list(length=None)
                if not docs:
                    response_text = "No documents found in the knowledge base."
                else:
                    response_text = "Here are the files currently indexed in the AURA Knowledge Base:\n\n"
                    response_text += "| Filename | Size | Chunks | Uploaded At |\n"
                    response_text += "| :--- | :--- | :--- | :--- |\n"
                    for d in docs:
                        size_kb = d['file_size'] / 1024
                        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                        response_text += f"| {d['filename']} | {size_str} | {d['chunk_count']} | {d['upload_time']} |\n"
            except Exception as e:
                response_text = f"Failed to list documents directly: {e}"
                
            yield (ChatEventType.TOKEN, response_text, None)
            await memory_engine.add_message(conversation_id, "user", message)
            await memory_engine.add_message(conversation_id, "assistant", response_text, {"routing": "Local SQLite knowledge_documents list bypass"})
            yield (ChatEventType.DONE, "", None)
            return

        # DEEP RESEARCH: Route to isolated DeepResearchEngine
        # Uses research_llm_client (Bedrock) — NEVER Chat/Agent providers
        is_deep_research = actual_message.strip().startswith("/deep-search ") or (category == "RESEARCH")
        if is_deep_research:
            topic = actual_message
            if actual_message.strip().startswith("/deep-search "):
                topic = actual_message.strip()[13:].strip()
                
            # Determine research depth from settings
            research_depth = "standard"
            try:
                depth_row = await db.db.system_settings.find_one({"key": "research_depth"}, {"value": 1})
                if depth_row:
                    research_depth = depth_row["value"]
            except Exception:
                pass

            yield (
                ChatEventType.SEARCH,
                f"Starting Deep Research on topic: \"{topic}\"...",
                {"status": "searching"}
            )
            
            # Store user query in database
            await memory_engine.add_message(conversation_id, "user", message)
            
            # Track final assistant report to save in SQLite history
            full_assistant_response = ""
            final_metadata = None
            
            from app.search.research_engine import research_engine, active_research_tasks
            
            try:
                async for event_type, data, metadata in research_engine.conduct_research(topic, conversation_id, research_depth):
                    if event_type == ChatEventType.TOKEN:
                        full_assistant_response += data
                        if metadata:
                            final_metadata = metadata
                    yield (event_type, data, metadata)
                    
                # Save compiled report message
                if full_assistant_response:
                    await memory_engine.add_message(
                        conversation_id, "assistant", full_assistant_response, final_metadata
                    )
            except Exception as e:
                logger.error(f"Router engine deep research task crashed: {e}")
                err_text = f"Deep research failed: {str(e)}"
                yield (ChatEventType.ERROR, err_text, None)
                await memory_engine.add_message(conversation_id, "assistant", err_text)
            finally:
                yield (ChatEventType.DONE, "", None)
                # Cancel task if connection closed prematurely
                task = active_research_tasks.pop(conversation_id, None)
                if task and not task.done():
                    logger.info(f"Aborting research task for conversation {conversation_id} inside finally block.")
                    task.cancel()
            return

        # SEARCH Queries confirmation check
        if category == "SEARCH":
            if web_search_mode == "never":
                # Force local execution, skip search prompt
                pass
            elif web_search_mode == "ask_first":
                if not force_local and not force_web_search:
                    prompt_text = "This may require a web search.\n\nWould you like:\n\n1. Local answer\n2. Web search"
                    yield (ChatEventType.TOKEN, prompt_text, None)
                    await memory_engine.add_message(conversation_id, "user", message)
                    await memory_engine.add_message(conversation_id, "assistant", prompt_text, {"routing": "Web search confirmation prompt"})
                    yield (ChatEventType.DONE, "", None)
                    return

        # Intent Routing Decision
        decision = await self.intent_router.route(actual_message)
        # Override decision based on new strict intent categories
        if category in ("WEBSITE_BUILDER", "APP_BUILDER", "AGENT"):
            decision.needs_tool = False
            decision.needs_search = False
            decision.needs_knowledge = False
            decision.needs_planner = True
            decision.reasoning = f"Routed to Autonomous Web/App Builder pipeline"
        elif category == "RESEARCH":
            decision.needs_planner = False
            decision.needs_search = True
            decision.tool_name = "web_search"
            decision.tool_params = {"query": self._extract_search_query(actual_message)}
            decision.reasoning = "Classified as RESEARCH"
        elif category == "FILE_ANALYSIS":
            decision.needs_planner = False
            decision.needs_tool = True
            decision.tool_name = "knowledge_retrieval"
            decision.tool_params = {"query": actual_message}
            decision.reasoning = "Classified as FILE ANALYSIS"
        else:
            # CHAT, CODING, DOCUMENT_GENERATION
            # Respond naturally like ChatGPT. No forced website builder. No file creation.
            decision.needs_tool = False
            decision.needs_search = False
            decision.needs_knowledge = False
            decision.needs_planner = False
            decision.direct_response = True
            decision.reasoning = f"Conversational response for intent: {category}"

        if decision.needs_planner:
            from app.execution.agent_engine import agent_engine
            # Store user query in database
            await memory_engine.add_message(conversation_id, "user", message)
            
            full_assistant_response = ""
            async for event_type, data, metadata in agent_engine.run_agent(actual_message, conversation_id):
                if event_type == ChatEventType.TOKEN:
                    full_assistant_response += data
                yield (event_type, data, metadata)
                
            if full_assistant_response:
                await memory_engine.add_message(conversation_id, "assistant", full_assistant_response)
            yield (ChatEventType.DONE, "", None)
            return

        # Initial skeleton yield
        initial_steps = [
            ("Understanding Request", "Waiting"),
            ("Loading Context", "Waiting"),
            ("Planning", "Waiting"),
            ("Tool Discovery", "Waiting"),
            ("Provider Selection", "Waiting"),
            ("External Operations", "Waiting"),
            ("Knowledge Processing", "Waiting"),
            ("Generating Response", "Waiting"),
            ("Validation", "Waiting"),
            ("Finished", "Waiting"),
        ]
        for step, detail in initial_steps:
            yield (ChatEventType.THINKING, detail, {"step": step, "status": "pending"})

        # Step 1: Understanding Request
        yield (ChatEventType.THINKING, "Analyzing query intent, language, and context", {"step": "Understanding Request", "status": "running"})

        await activity_logger.log(
            action_type="ROUTER_DECISION",
            category="router",
            description=f"Routed query: {decision.reasoning}",
            details=decision.model_dump(),
            status="info",
        )

        category = await self.intent_router.classify(actual_message)
        yield (ChatEventType.THINKING, f"Intent detected: {category}", {"step": "Understanding Request", "status": "completed"})

        # Step 2: Loading Context
        yield (ChatEventType.THINKING, "Loading conversation history, project, and workspace state", {"step": "Loading Context", "status": "running"})

        # Context components
        semantic_memories_context = ""
        knowledge_context = ""
        tool_result_context = ""

        # Step 6: Searching Knowledge Base
        yield (ChatEventType.THINKING, "Searching indexed local documents", {"step": "Searching Knowledge Base", "status": "running"})
        if decision.needs_knowledge and decision.tool_name != "knowledge_retrieval":
            knowledge_context = await self.context_manager.get_knowledge_context(actual_message, conversation_id)
            if knowledge_context:
                await activity_logger.log(
                    action_type="KNOWLEDGE_RETRIEVAL",
                    category="knowledge",
                    description="Retrieved relevant chunks from uploaded knowledge documents.",
                    details={"query": actual_message},
                    status="success",
                )
                yield (ChatEventType.THINKING, "Retrieved relevant chunks from knowledge documents", {"step": "Searching Knowledge Base", "status": "completed"})
            else:
                yield (ChatEventType.THINKING, "No relevant matches in knowledge base", {"step": "Searching Knowledge Base", "status": "completed"})
        else:
            yield (ChatEventType.THINKING, "Not required", {"step": "Searching Knowledge Base", "status": "skipped"})

        history = await memory_engine.get_messages_for_llm(conversation_id, limit=20)
        project_context = ""
        if active_project:
            project_context = await project_manager.get_project_context(active_project["id"])
            
        yield (ChatEventType.THINKING, "Context loaded successfully", {"step": "Loading Context", "status": "completed"})

        # Step 3: Planning
        yield (ChatEventType.THINKING, "Determining tool and search requirements", {"step": "Planning", "status": "running"})
        plan_desc = []
        if decision.needs_search: plan_desc.append("web search")
        if decision.needs_tool: plan_desc.append("tool usage")
        if decision.needs_knowledge: plan_desc.append("knowledge base")
        if decision.needs_planner: plan_desc.append("planner")
        
        yield (ChatEventType.THINKING, f"Plan ready: {', '.join(plan_desc) or 'direct response'}", {"step": "Planning", "status": "completed"})

        # Step 4: Tool Discovery
        yield (ChatEventType.THINKING, "Activating required tools", {"step": "Tool Discovery", "status": "running"})
        if decision.needs_tool and decision.tool_name:
            yield (ChatEventType.THINKING, f"Activated tool: {decision.tool_name}", {"step": "Tool Discovery", "status": "completed"})
        else:
            yield (ChatEventType.THINKING, "No tools required", {"step": "Tool Discovery", "status": "skipped"})

        # Step 5: Provider Selection
        yield (ChatEventType.THINKING, "Selecting fastest AI provider", {"step": "Provider Selection", "status": "running"})
        from app.core.model_manager import model_manager
        provider_name = model_manager.active_provider
        
        # Get active provider's current latency
        latencies = model_manager.stats["latencies"].get(provider_name, [])
        latency = round(latencies[-1], 3) if latencies else 0.0
        
        provider_display = provider_name.upper()
        if latency > 0:
            provider_display += f" ({latency}s)"
        yield (ChatEventType.THINKING, f"Selected: {provider_display}", {"step": "Provider Selection", "status": "completed"})

        # Step 6: External Operations
        if decision.needs_search:
            yield (ChatEventType.THINKING, "Searching trusted sources...", {"step": "External Operations", "status": "running"})
            yield (
                ChatEventType.SEARCH,
                f"Searching the web: \"{decision.tool_params.get('query', actual_message)}\"",
                {"status": "searching"},
            )
            yield (
                ChatEventType.TOOL_USE,
                decision.tool_name,
                {"params": decision.tool_params},
            )
            success, tool_output = await self.tool_router.execute_tool(
                decision.tool_name, decision.tool_params, conversation_id
            )
            yield (
                ChatEventType.TOOL_RESULT,
                tool_output,
                {"success": success},
            )
            if success:
                tool_result_context = f"\n\nTool '{decision.tool_name}' result:\n{tool_output}"
            else:
                tool_result_context = f"\n\nTool '{decision.tool_name}' execution failed: {tool_output}"

            await activity_logger.log(
                action_type="TOOL_EXECUTION",
                category="tools",
                description=f"Executed tool: '{decision.tool_name}' Status: {'success' if success else 'failed'}",
                details={"tool_name": decision.tool_name, "params": decision.tool_params, "success": success},
                status="success" if success else "error",
            )
            yield (ChatEventType.THINKING, f"Web search results retrieved", {"step": "External Operations", "status": "completed"})
        elif decision.needs_tool and decision.tool_name and decision.tool_name != "knowledge_retrieval":
            yield (ChatEventType.THINKING, f"Executing tool: {decision.tool_name}", {"step": "External Operations", "status": "running"})
            yield (
                ChatEventType.TOOL_USE,
                decision.tool_name,
                {"params": decision.tool_params},
            )
            success, tool_output = await self.tool_router.execute_tool(
                decision.tool_name, decision.tool_params, conversation_id
            )
            yield (
                ChatEventType.TOOL_RESULT,
                tool_output,
                {"success": success},
            )
            if success:
                tool_result_context = f"\n\nTool '{decision.tool_name}' result:\n{tool_output}"
            else:
                tool_result_context = f"\n\nTool '{decision.tool_name}' execution failed: {tool_output}"

            await activity_logger.log(
                action_type="TOOL_EXECUTION",
                category="tools",
                description=f"Executed tool: '{decision.tool_name}' Status: {'success' if success else 'failed'}",
                details={"tool_name": decision.tool_name, "params": decision.tool_params, "success": success},
                status="success" if success else "error",
            )
            yield (ChatEventType.THINKING, "Tool execution finished", {"step": "External Operations", "status": "completed"})
        else:
            yield (ChatEventType.THINKING, "No external operations required", {"step": "External Operations", "status": "skipped"})

        # Step 7: Knowledge Processing
        yield (ChatEventType.THINKING, "Reading information...", {"step": "Knowledge Processing", "status": "running"})
        if knowledge_context or msg_lower.startswith("uploaded file:") or msg_lower.startswith("uploaded files:"):
            yield (ChatEventType.THINKING, "Loaded uploaded documents context", {"step": "Reading uploaded documents", "status": "completed"})
        elif decision.needs_knowledge or decision.tool_name == "knowledge_retrieval":
            knowledge_context = await self.context_manager.get_knowledge_context(actual_message, conversation_id)
            if knowledge_context:
                yield (ChatEventType.THINKING, "Knowledge processing complete", {"step": "Knowledge Processing", "status": "completed"})
            else:
                yield (ChatEventType.THINKING, "No matching documents found", {"step": "Knowledge Processing", "status": "completed"})
        else:
            yield (ChatEventType.THINKING, "Not required", {"step": "Knowledge Processing", "status": "skipped"})

        # Long-term memory query (Folded into Knowledge Processing step conceptually for speed)
        is_continuation = self._is_continuation_query(actual_message)
        if decision.needs_memory and is_continuation:
            semantic_memories_context = await self.context_manager.get_memory_context(actual_message, conversation_id)

        # Step 8: Generating Response
        yield (ChatEventType.THINKING, "Writing answer...", {"step": "Generating Response", "status": "running"})

        messages = []
        messages.extend(history)

        system_prompt = AURA_SYSTEM_PROMPT
        if project_context:
            system_prompt = AURA_SYSTEM_PROMPT + "\n\n" + project_context + "\n\n" + (
                "CRITICAL INSTRUCTION: You are working on the active project described above. "
                "Any modifications or additions must be applied directly to the files in the project workspace folder "
                "under the `Projects/{slug}/` prefix (e.g. `Projects/{slug}/index.html`). "
                "When referencing or editing files, prefix the filepath with `Projects/{slug}/` (e.g. `Projects/{slug}/index.html`). "
                "Do NOT create new root-level file paths or start a new project from scratch unless explicitly requested. "
                "Modify the existing project files to preserve state and history."
            ).replace("{slug}", active_project["slug"])

        user_content = actual_message
        if knowledge_context:
            user_content = knowledge_context + "\n\n" + user_content
        if semantic_memories_context:
            user_content = semantic_memories_context + "\n\n" + user_content
        if tool_result_context:
            user_content += tool_result_context
            if decision.needs_search:
                user_content += "\n\nPlease construct a helpful, direct answer based on the search results. Cite sources."
            elif decision.tool_name == "knowledge_retrieval":
                user_content += "\n\nPlease construct a helpful, direct answer using the local knowledge base search results. Cite the specific uploaded documents."

        # Quality instructions
        system_prompt += (
            "\n\nImprove answer quality by:\n"
            "- ranking sources by authority (if applicable)\n"
            "- validating factual consistency\n"
            "- removing duplicate information\n"
            "- producing structured, well-formatted answers with comparative tables and pros/cons where relevant."
        )

        try:
            tz = zoneinfo.ZoneInfo(timezone) if timezone else None
        except Exception:
            tz = None
        now = datetime.now(tz) if tz else datetime.now().astimezone()
        system_prompt += f"\n\nCURRENT SYSTEM TIME: {now.strftime('%A, %B %d, %Y %I:%M:%S %p %Z')}."

        messages.append({"role": "user", "content": user_content})

        response_text = ""
        model_meta = None  # Initialize to avoid unbound variable warning
        try:
            # Stream the chat completion in real-time
            async for token, meta in llm_client.stream_chat(
                messages,
                system_prompt=system_prompt,
                category=category,
                preferred_provider=preferred_provider,
                preferred_model=preferred_model
            ):
                from app.router.stream_registry import stream_registry
                # Check for model metadata at the end
                if meta and meta.get("model_metadata"):
                    model_meta = meta["model_metadata"]
                    provider_name = model_meta.get("provider", provider_name)
                    latency = 0.0  # Will be calculated from timing
                
                # Cancel check
                if stream_registry.is_cancelled(conversation_id):
                    logger.info(f"Stream generation loop: detected cancellation for {conversation_id}, aborting LLM stream.")
                    break
                await stream_registry.wait_if_paused(conversation_id)

                if token:
                    response_text += token
                    yield (ChatEventType.TOKEN, token, None)
        except Exception as e:
            logger.error(f"Streaming inference failed: {e}")
            yield (ChatEventType.ERROR, f"Streaming error: {e}", None)
            return

        yield (ChatEventType.THINKING, "Answer written successfully", {"step": "Generating Response", "status": "completed"})

        # Step 9: Validation
        yield (ChatEventType.THINKING, "Validating response formatting and references...", {"step": "Validation", "status": "running"})
        
        # Clean response
        response_text = self.answer_validator.validate_and_clean(response_text)
        
        try:
            validation_result = await quality_validator.validate(actual_message, response_text)
            passed = validation_result.get("passed", True)
            feedback = validation_result.get("feedback", "")
            logger.info(f"Self-validation finished. Passed: {passed}. Feedback: {feedback}")
        except Exception as e:
            logger.warning(f"Quality validation failed to run: {e}")

        yield (ChatEventType.THINKING, "Validation complete", {"step": "Validation", "status": "completed"})

        # Step 10: Finished
        yield (ChatEventType.THINKING, "Execution completed", {"step": "Finished", "status": "completed"})

        # 9. Save conversations to databases
        metadata = {
            "routing": decision.reasoning,
        }
        if decision.needs_tool:
            metadata["tool_used"] = decision.tool_name
            metadata["tool_params"] = decision.tool_params
        if decision.needs_search:
            metadata["search"] = True
        if decision.needs_planner:
            metadata["planner"] = True

        await memory_engine.add_message(conversation_id, "user", message)
        await memory_engine.add_message(
            conversation_id, "assistant", response_text, metadata
        )

        # 10. Handle Auto-Title for conversations
        try:
            hist = await memory_engine.get_history(conversation_id)
            if len(hist) <= 2:  # First response pair
                conv = await memory_engine.get_conversation(conversation_id)
                if conv and conv["title"] == "New Conversation":
                    title = memory_engine.generate_title_from_message(actual_message)
                    await memory_engine.update_conversation_title(conversation_id, title)
        except Exception as e:
            logger.warning(f"Failed to auto-update title: {e}")

        completion_metadata = {
            "provider": provider_name,
            "latency": latency,
            "tokens": len(response_text) // 4,
            "project": active_project["name"] if active_project else None,
            "search": decision.needs_search,
        }
        
        # Add model metadata if available
        if model_meta:
            completion_metadata["model"] = {
                "provider": model_meta.get("provider"),
                "model": model_meta.get("model"),
                "fallback": model_meta.get("fallback", False),
                "fallback_from": model_meta.get("fallback_from"),
                "selection_source": model_meta.get("selection_source", "auto"),
            }
        
        yield (ChatEventType.DONE, "", completion_metadata)

    async def classify_query(self, message: str) -> str:
        """Classify user query into one of the 8 strict intents."""
        msg_lower = message.lower().strip().rstrip("?.! ")
        
        # 1. WEBSITE_BUILDER keywords
        website_keywords = ["create website", "build landing page", "build ecommerce site", "create portfolio"]
        if any(k in msg_lower for k in website_keywords):
            return "WEBSITE_BUILDER"
            
        # 2. APP_BUILDER keywords
        app_keywords = ["build app", "create dashboard", "build saas", "build crm"]
        if any(k in msg_lower for k in app_keywords):
            return "APP_BUILDER"
            
        # 3. RESEARCH keywords
        research_keywords = ["research", "find latest", "compare", "analyze"]
        if any(k in msg_lower for k in research_keywords):
            return "RESEARCH"
            
        # 4. AGENT keywords
        agent_keywords = ["fix", "debug", "deploy", "refactor", "integrate"]
        if any(k in msg_lower for k in agent_keywords):
            return "AGENT"
            
        # 5. CODING keywords
        coding_keywords = ["write code", "explain code", "teach programming"]
        if any(k in msg_lower for k in coding_keywords):
            return "CODING"
            
        # 6. DOCUMENT_GENERATION keywords
        document_keywords = ["summarize document", "generate report", "create ppt"]
        if any(k in msg_lower for k in document_keywords):
            return "DOCUMENT_GENERATION"

        # 7. FILE_ANALYSIS keywords
        file_keywords = ["analyze file", "read file", "parse database", "csv analysis", "log analysis"]
        if any(k in msg_lower for k in file_keywords):
            return "FILE_ANALYSIS"

        # Fallback to LLM classification
        try:
            prompt = INTENT_PROMPT.format(message=message)
            decision = await llm_client.generate_json(prompt)
            intent = decision.get("intent", "").upper().replace(" ", "_").strip()
            valid_intents = {
                "CHAT", "RESEARCH", "AGENT", "WEBSITE_BUILDER", 
                "APP_BUILDER", "CODING", "FILE_ANALYSIS", "DOCUMENT_GENERATION"
            }
            if intent in valid_intents:
                return intent
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            
        return "CHAT"

    def _is_continuation_query(self, message: str) -> bool:
        """Check if user query explicitly references earlier messages."""
        msg_lower = message.lower().strip().rstrip("?.! ")
        
        continuation_keywords = [
            "continue", "explain more", "what about that", "tell me more",
            "go on", "elaborate", "keep going", "and then", "what does that mean",
            "why is that", "explain that", "what about it", "how about that",
            "tell me about it", "what was the first", "what was that",
            "repeat that", "what did you say", "do it again"
        ]
        
        if any(msg_lower.startswith(k) or msg_lower == k for k in continuation_keywords):
            return True
            
        words = msg_lower.split()
        if len(words) <= 3 and any(w in {"it", "that", "this", "them", "those", "previous", "earlier", "before"} for w in words):
            return True
            
        return False

    def _looks_like_math(self, text: str) -> bool:
        """Check if text appears to be a math expression."""
        text = text.strip()
        has_operator = any(op in text for op in ["+", "-", "*", "/", "^", "**"])
        has_digit = any(c.isdigit() for c in text)
        is_short = len(text) < 100
        space_ratio = text.count(" ") / max(len(text), 1)
        return has_operator and has_digit and is_short and space_ratio < 0.3

    def _extract_math(self, text: str) -> str:
        text = text.replace("^", "**").replace("×", "*").replace("÷", "/")
        return text.strip()

    def _extract_tool_params(self, tool_name: str, message: str) -> dict:
        """Extract tool parameters from text."""
        if tool_name == "calculator":
            for prefix in ["calculate", "compute", "what is", "how much is", "evaluate"]:
                if message.lower().startswith(prefix):
                    expr = message[len(prefix):].strip().rstrip("?. ")
                    return {"expression": expr.replace("^", "**")}
            return {"expression": message.strip().rstrip("?. ")}

        elif tool_name == "file_reader":
            words = message.split()
            for word in words:
                if "/" in word or "." in word.split("/")[-1]:
                    return {"path": word.strip("\"'`")}
            return {"path": ""}

        elif tool_name == "system_info":
            msg_lower = message.lower()
            if "cpu" in msg_lower:
                return {"category": "cpu"}
            elif "memory" in msg_lower or "ram" in msg_lower:
                return {"category": "memory"}
            elif "disk" in msg_lower:
                return {"category": "disk"}
            elif "os" in msg_lower:
                return {"category": "os"}
            return {"category": "all"}

        elif tool_name == "code_runner":
            # Defaults to python
            lang = "javascript" if ("javascript" in message.lower() or " node" in message.lower()) else "python"
            # Find python code or javascript code (we can extract simple code blocks or send empty to runner)
            code = ""
            if "```" in message:
                parts = message.split("```")
                if len(parts) >= 3:
                    # Extracts content of code block
                    block_content = parts[1]
                    if block_content.startswith("python") or block_content.startswith("py"):
                        code = block_content[6:] if block_content.startswith("python") else block_content[2:]
                    elif block_content.startswith("javascript") or block_content.startswith("js"):
                        code = block_content[10:] if block_content.startswith("javascript") else block_content[2:]
                    else:
                        code = block_content
            return {"language": lang, "code": code.strip(), "retries": 1}

        elif tool_name == "knowledge_retrieval":
            # Strip common knowledge base prefixes
            lower = message.lower()
            prefixes = [
                "search knowledge base for", "search in knowledge base for",
                "search uploaded files for", "search documents for",
                "query knowledge base for", "search my documents for",
                "find in documents", "find in pdf", "search my pdf for",
                "ask knowledge base about", "search about"
            ]
            query = message
            for p in prefixes:
                if lower.startswith(p):
                    query = message[len(p):].strip()
                    break
            return {"query": query.rstrip("?.! ").strip()}
 
        return {}


# Global instance
router_engine = RouterEngine()
