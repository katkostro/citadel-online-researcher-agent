# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import asyncio
import logging
import os
import contextlib
from typing import AsyncGenerator, Dict, Optional

import fastapi
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from logging_config import configure_logging

load_dotenv()

# Global variables for the hybrid system - import from gunicorn_sk_conf
# (Will be imported after initialization)
kernel = None
internal_plugin = None
chat_service = None
ai_project_client = None
agent = None

# Thread tracking for agent conversations
chat_threads: Dict[str, str] = {}

def serialize_sse_event(data: Dict) -> str:
    """Serialize data as Server-Sent Event"""
    import json
    return f"data: {json.dumps(data)}\n\n"

# Models for request/response
class Message(BaseModel):
    message: str
    session_state: dict = {}

class ChatResponse(BaseModel):
    message: str
    annotations: list = []

enable_trace = False
logger = configure_logging(os.getenv("APP_LOG_FILE", ""))

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the hybrid system on startup"""
    global kernel, internal_plugin, chat_service, ai_project_client, agent
    
    try:
        # Import the hybrid initialization from gunicorn_sk_conf
        from gunicorn_sk_conf import initialize_resources
        
        # Initialize the hybrid system (this sets globals in gunicorn_sk_conf)
        await initialize_resources()
        
        # Import the initialized globals from gunicorn_sk_conf
        import gunicorn_sk_conf
        kernel = gunicorn_sk_conf.kernel
        internal_plugin = gunicorn_sk_conf.internal_plugin
        chat_service = gunicorn_sk_conf.chat_service
        ai_project_client = gunicorn_sk_conf.ai_project_client
        agent = gunicorn_sk_conf.agent
        
        logger.info("FastAPI startup: Hybrid system initialization complete")
        logger.info(f"FastAPI startup: Agent ID: {getattr(agent, 'id', None) if agent else None}")
            
    except Exception as e:
        logger.error(f"FastAPI startup error: {e}")
        # Continue without hybrid system - will use fallbacks
    
    yield
    
    # Cleanup on shutdown
    logger.info("FastAPI shutdown: Cleaning up resources")

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow frontend to communicate with backend
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now - should be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication dependency placeholder 
auth_dependency = None

# Mount static files
app.mount("/static", StaticFiles(directory="api/static", html=True), name="static")

@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint to prevent 404 errors"""
    from fastapi.responses import Response
    # Return empty response to prevent 404 errors in browser
    return Response(content="", media_type="image/x-icon")

@app.get("/health")
async def health():
    """Health check endpoint"""
    global agent, ai_project_client, kernel, internal_plugin, chat_service
    
    return JSONResponse(content={
        "status": "healthy",
        "framework": "hybrid_sk_plus_azure_ai_projects",
        "agent_id": getattr(agent, 'id', None) if agent else None,
        "ai_project_client_enabled": ai_project_client is not None,
        "bing_grounding_enabled": agent is not None,
        "internal_knowledge_enabled": internal_plugin is not None,
        "semantic_kernel_enabled": kernel is not None,
        "chat_service_enabled": chat_service is not None
    })

@app.get("/internal-knowledge")  
async def internal_knowledge(request: Request, _ = auth_dependency):
    """Internal knowledge endpoint"""
    global internal_plugin
    
    if not internal_plugin:
        raise HTTPException(status_code=503, detail="Internal knowledge plugin not available")
    
    return JSONResponse(content={
        "status": "available",
        "plugin_name": "internal_knowledge",
        "description": "Access to banking policies, procedures, and product information"
    })

@app.get("/")
async def index(request: Request):
    """Serve the main page"""
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="api/templates")
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}
    )


@app.get("/agent")
async def get_chat_agent(request: Request, _ = auth_dependency):
    """Get agent information"""
    global agent, internal_plugin
    if agent:
        return JSONResponse(content={
            "id": agent.id,
            "name": getattr(agent, 'name', 'Hybrid Outdoor Gear Assistant'),
            "model": os.environ.get("AZURE_AI_AGENT_DEPLOYMENT_NAME", "gpt-4o-mini"),
            "instructions": getattr(agent, 'instructions', 'Outdoor gear and camping assistant with web search and internal product knowledge capabilities'),
            "type": "hybrid_azure_ai_agent",
            "tools": ["bing_grounding", "internal_knowledge"] if agent and internal_plugin else ["bing_grounding"] if agent else []
        })
    else:
        raise HTTPException(status_code=500, detail="Hybrid Azure AI Agent not initialized")


@app.get("/chat/history")
async def history(request: Request, _ = auth_dependency):
    """Get chat history"""
    # For now, return empty history as Azure AI Agent manages conversation state
    return JSONResponse(content=[])


async def stream_agent_response(user_message: str, thread_id: str = None) -> AsyncGenerator[str, None]:
    """Stream response from hybrid system (SK plugins + Azure AI Projects agents)"""
    global ai_project_client, agent, kernel, internal_plugin, chat_service
    
    try:
        # Create or get thread ID
        if not thread_id:
            thread_id = f"thread_{int(asyncio.get_event_loop().time())}"
        
        logger.info(f"sk: Processing hybrid message: {user_message} (Thread: {thread_id})")
        
        # Initialize response collection
        responses = []
        internal_response = None
        agent_response = None
        
        # Step 1: Try internal knowledge plugin first (if available)
        if internal_plugin and kernel:
            try:
                # Only search internal knowledge for relevant queries (not weather/news/current events)
                external_info_keywords = ["weather", "temperature", "forecast", "news", "current", "today", "now", "latest", "recent", "stock", "price", "market"]
                is_external_query = any(keyword in user_message.lower() for keyword in external_info_keywords)
                
                logger.info(f"sk: Query analysis - External keywords found: {[k for k in external_info_keywords if k in user_message.lower()]}")
                logger.info(f"sk: Is external query: {is_external_query}")
                
                if not is_external_query:
                    # Use semantic kernel for internal knowledge 
                    logger.info("sk: Searching internal knowledge for product/policy query")
                    internal_context = internal_plugin.search_internal_knowledge(user_message)
                    if internal_context and "not found" not in internal_context.lower():
                        internal_response = internal_context
                        logger.info("sk: ✅ Got internal knowledge response")
                else:
                    logger.info("sk: Skipping internal knowledge for external info query")
            except Exception as e:
                logger.warning(f"sk: Internal knowledge error: {e}")
        
        # Step 2: Try Azure AI Projects agent for web search/current info or when internal knowledge didn't help
        needs_web_search = any(keyword in user_message.lower() for keyword in 
                              ["weather", "current", "today", "now", "latest", "recent", "news", "stock", "price", "forecast", "temperature"])
        
        if agent and ai_project_client and (needs_web_search or not internal_response):
            try:
                logger.info("sk: Attempting to use Azure AI Projects agent")
                
                # Prepare the message for the agent
                enhanced_message = user_message
                if internal_response and "not found" not in internal_response.lower():
                    enhanced_message = f"""User question: {user_message}

I have relevant internal outdoor gear information:
{internal_response}

Please provide a comprehensive answer. If you need current web information, use your Bing search capability and include citations. Combine both internal and web information appropriately."""
                else:
                    # For external queries like weather, be very explicit about using Bing search
                    enhanced_message = f"""User question: {user_message}

You have access to a Bing search tool. Please use it to search for current information to answer this question. Do not say you cannot provide real-time information - instead, use your Bing search capability to find the most up-to-date information and provide it to the user with proper citations.

IMPORTANT: Use the Bing search tool to get current, real-time information for this query."""
                
                
                # Use create_thread_and_run instead of separate steps
                logger.info("sk: Using create_thread_and_run for simpler API call")
                
                run_result = ai_project_client.agents.create_thread_and_run(
                    agent_id=agent.id,
                    thread={
                        "messages": [
                            {
                                "role": "user", 
                                "content": enhanced_message
                            }
                        ]
                    }
                )
                logger.info(f"sk: Created thread and run: {run_result.id}")
                
                # Wait for completion properly by checking run status
                import time
                max_wait_time = 30  # 30 seconds max wait for Bing search
                wait_interval = 2   # Check every 2 seconds
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    try:
                        # Check run status using the correct API call
                        current_run = ai_project_client.agents.runs.get(
                            thread_id=run_result.thread_id, 
                            run_id=run_result.id
                        )
                        logger.info(f"sk: Run status: {current_run.status}")
                        
                        if current_run.status in ["completed", "failed", "expired", "cancelled"]:
                            logger.info(f"sk: Run finished with status: {current_run.status}")
                            break
                            
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                        
                    except Exception as status_error:
                        logger.warning(f"sk: Error checking run status: {status_error}")
                        # If status checking fails, just wait a bit and continue
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                        break
                
                if elapsed_time >= max_wait_time:
                    logger.warning("sk: Run did not complete within timeout period")
                
                # Get messages from the thread with better error handling
                try:
                    messages = ai_project_client.agents.messages.list(thread_id=run_result.thread_id)
                    logger.info(f"sk: Retrieved messages object: {type(messages)}")
                    
                    # Convert iterator to list since messages.list() returns ItemPaged iterator
                    messages_list = list(messages)
                    logger.info(f"sk: Messages list length: {len(messages_list)}")
                    
                    # Extract the latest assistant message
                    if messages_list:
                        logger.info(f"sk: Processing {len(messages_list)} messages")
                        for i, message in enumerate(messages_list):
                            logger.info(f"sk: Message {i}: role={getattr(message, 'role', 'unknown')}")
                            if message.role == "assistant" and message.content:
                                logger.info(f"sk: Found assistant message with {len(message.content)} content items")
                                for j, content_item in enumerate(message.content):
                                    logger.info(f"sk: Content item {j}: type={type(content_item)}")
                                    if hasattr(content_item, 'text') and content_item.text:
                                        agent_response = content_item.text.value
                                        logger.info(f"sk: Extracted response: {len(agent_response)} chars")
                                        break
                                if agent_response:
                                    break
                    else:
                        logger.warning("sk: No messages found in the thread")
                        
                except Exception as msg_error:
                    logger.error(f"sk: Error retrieving messages: {msg_error}")
                    messages_list = []
                
                if agent_response:
                    responses.append(f"**AI Assistant with Bing:** {agent_response}")
                    logger.info("sk: ✅ Got agent response with Bing search")
                else:
                    logger.warning("sk: Agent executed but no response content found")
                    
            except Exception as e:
                logger.error(f"sk: Error getting agent response: {e}")
                # Continue to fallback options
        
        # Step 3: If we have internal knowledge response, use it
        if internal_response and not responses:
            responses.append(f"**Internal Knowledge:** {internal_response}")
            logger.info("sk: ✅ Using internal knowledge response")
        
        # Step 4: Fallback to Semantic Kernel chat if available
        if not responses and chat_service and kernel:
            try:
                logger.info("sk: Using SK chat service for response")
                # Note: This would normally use SK's chat completion
                # For now, we'll skip since we don't have working Azure OpenAI auth
                pass
                    
            except Exception as e:
                logger.error(f"sk: SK chat service failed: {e}")
        
        # Step 5: Final fallback - helpful outdoor gear assistant response
        if not responses:
            fallback_response = """Hello! I'm your outdoor gear assistant. I'm currently operating with limited capabilities, but I can still help you with:

• Information about camping equipment and outdoor gear
• Product details about tents, backpacks, hiking boots, and camping supplies
• General outdoor activity guidance and tips
• Equipment recommendations based on your needs

For weather information, current news, or other external information, I may need my web search capabilities to be working properly.

What outdoor gear or camping questions can I help you with?"""
            responses.append(fallback_response)
            logger.info("sk: Using fallback outdoor gear response")
        
        # Combine responses
        final_response = "\n\n".join(responses) if responses else "I apologize, but I'm unable to process your request at the moment."
        
        # Send the complete response at once (no character-by-character streaming)
        logger.info(f"sk: Sending complete response: {len(final_response)} characters")
        yield serialize_sse_event({'content': final_response, 'annotations': [], 'type': "completed_message"})
        logger.info("sk: Sending stream_end event")
        yield serialize_sse_event({'type': "stream_end"})
        
    except Exception as e:
        logger.error(f"sk: Stream error: {e}")
        error_message = "I'm sorry, I couldn't generate a response. Please try again."
        # Send the complete error message at once
        yield serialize_sse_event({'content': error_message, 'annotations': [], 'type': "completed_message"})
        yield serialize_sse_event({'type': "stream_end"})


@app.post("/chat")
async def chat_stream(request: Message, _ = auth_dependency):
    """Stream chat responses from the hybrid system"""
    
    # Log the incoming request
    logger.info(f"sk: Received chat request: {request.message}")
    
    try:
        # Stream the response
        return StreamingResponse(
            stream_agent_response(request.message, request.session_state.get("thread_id")),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive", 
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"sk: Chat endpoint error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process chat request"}
        )

def format_bing_grounding_response(content, annotations=None):
    """Format the response to match the required JSON structure with annotations."""
    # If content is already the complete message object with text and annotations
    if hasattr(content, 'text') and hasattr(content.text, 'value') and hasattr(content.text, 'annotations'):
        return {
            "response": {
                "type": "text", 
                "text": {
                    "value": content.text.value,
                    "annotations": [
                        {
                            "type": annotation.type if hasattr(annotation, 'type') else "url_citation",
                            "text": annotation.text if hasattr(annotation, 'text') else "",
                            "start_index": annotation.start_index if hasattr(annotation, 'start_index') else 0,
                            "end_index": annotation.end_index if hasattr(annotation, 'end_index') else 0,
                            "url_citation": {
                                "url": annotation.url_citation.url if hasattr(annotation, 'url_citation') and hasattr(annotation.url_citation, 'url') else "",
                                "title": annotation.url_citation.title if hasattr(annotation, 'url_citation') and hasattr(annotation.url_citation, 'title') else ""
                            } if hasattr(annotation, 'url_citation') else {}
                        } for annotation in content.text.annotations
                    ]
                }
            }
        }
    
    # Handle the case where content and annotations are passed separately
    if annotations is not None:
        formatted_annotations = []
        for annotation in annotations:
            # Handle different annotation formats
            if isinstance(annotation, dict):
                formatted_annotations.append({
                    "type": annotation.get("type", "url_citation"),
                    "text": annotation.get("text", ""),
                    "start_index": annotation.get("start_index", 0),
                    "end_index": annotation.get("end_index", 0),
                    "url_citation": annotation.get("url_citation", {})
                })
            else:
                # Handle object-based annotations
                formatted_annotations.append({
                    "type": getattr(annotation, 'type', "url_citation"),
                    "text": getattr(annotation, 'text', ""),
                    "start_index": getattr(annotation, 'start_index', 0),
                    "end_index": getattr(annotation, 'end_index', 0),
                    "url_citation": {
                        "url": getattr(getattr(annotation, 'url_citation', None), 'url', "") if hasattr(annotation, 'url_citation') else "",
                        "title": getattr(getattr(annotation, 'url_citation', None), 'title', "") if hasattr(annotation, 'url_citation') else ""
                    } if hasattr(annotation, 'url_citation') else {}
                })
        
        return {
            "response": {
                "type": "text",
                "text": {
                    "value": str(content),
                    "annotations": formatted_annotations
                }
            }
        }
    
    # Fallback for simple content
    if hasattr(content, 'value'):
        text_value = content.value
    else:
        text_value = str(content)
    
    return {
        "response": {
            "type": "text",
            "text": {
                "value": text_value,
                "annotations": []
            }
        }
    }

@app.post("/search")
async def search_endpoint(request: Message, _ = auth_dependency):
    """
    Search endpoint that returns Bing grounding responses in standardized JSON format.
    """
    global agent, ai_project_client
    
    logger.info(f"search: Received search request: {request.message}")
    
    if not agent or not ai_project_client:
        logger.error("search: Agent or AI project client not available")
        error_response = format_bing_grounding_response("Search service not available")
        return JSONResponse(
            status_code=503,
            content=error_response
        )
    
    try:
        # Use direct Azure AI Projects API like the reference implementation
        logger.info("search: Creating thread and run for search request")
        
        # Create thread and run in one step
        run_result = ai_project_client.agents.create_thread_and_run(
            agent_id=agent.id,
            thread={
                "messages": [
                    {
                        "role": "user", 
                        "content": f"""Please search for: {request.message}

Use your Bing search tool to find current information and provide a comprehensive answer with proper citations."""
                    }
                ]
            }
        )
        
        # Wait for completion
        import time
        max_wait_time = 30
        wait_interval = 1
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                current_run = ai_project_client.agents.runs.get(
                    thread_id=run_result.thread_id, 
                    run_id=run_result.id
                )
                logger.info(f"search: Run status: {current_run.status}")
                
                if current_run.status in ["completed", "failed", "expired", "cancelled"]:
                    if current_run.status == "failed":
                        logger.error(f"search: Run failed: {getattr(current_run, 'last_error', 'Unknown error')}")
                    break
                    
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                
            except Exception as status_error:
                logger.warning(f"search: Error checking run status: {status_error}")
                break
        
        # Get the complete message with annotations
        try:
            messages = ai_project_client.agents.messages.list(thread_id=run_result.thread_id)
            messages_list = list(messages)
            
            # Find the last assistant message
            for message in messages_list:
                if message.role == "assistant" and message.content:
                    for content_item in message.content:
                        if hasattr(content_item, 'text') and content_item.text:
                            # Debug logging to understand the structure
                            logger.info(f"search: Content item type: {type(content_item)}")
                            logger.info(f"search: Text type: {type(content_item.text)}")
                            logger.info(f"search: Has annotations: {hasattr(content_item.text, 'annotations')}")
                            if hasattr(content_item.text, 'annotations'):
                                logger.info(f"search: Annotations count: {len(content_item.text.annotations)}")
                                logger.info(f"search: Annotations: {content_item.text.annotations}")
                            
                            # Try to convert to dict to see the full structure
                            try:
                                if hasattr(content_item, 'model_dump'):
                                    content_dict = content_item.model_dump()
                                    logger.info(f"search: Content dict: {content_dict}")
                                elif hasattr(content_item, '__dict__'):
                                    logger.info(f"search: Content dict: {content_item.__dict__}")
                            except Exception as dict_error:
                                logger.info(f"search: Could not convert to dict: {dict_error}")
                            
                            # Return the complete message object to preserve annotations
                            logger.info(f"search: Found message with {len(getattr(content_item.text, 'annotations', []))} annotations")
                            return JSONResponse(content={"response": content_item})
            
            # No assistant message found
            error_response = format_bing_grounding_response("No search results available")
            return JSONResponse(content=error_response)
            
        except Exception as msg_error:
            logger.error(f"search: Error retrieving messages: {msg_error}")
            error_response = format_bing_grounding_response("Error retrieving search results")
            return JSONResponse(
                status_code=500,
                content=error_response
            )
            
    except Exception as e:
        logger.error(f"search: Error processing search request: {e}")
        error_response = format_bing_grounding_response("An error occurred while processing your search request.")
        return JSONResponse(
            status_code=500,
            content=error_response
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
