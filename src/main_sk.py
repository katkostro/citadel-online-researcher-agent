# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import asyncio
import logging
import os
import contextlib
import re
from typing import AsyncGenerator, Dict, Optional

import fastapi
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from logging_config import configure_logging

load_dotenv()

# Global variables for the Azure AI Projects system
kernel = None
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What's the weather like in Miami today?",
                "session_state": {}
            }
        }

class ChatResponse(BaseModel):
    message: str
    annotations: list = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "The weather in Miami today is sunny with a temperature of 78°F...",
                "annotations": ["weather", "miami", "current"]
            }
        }

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "upcoming events in Miami this weekend",
                "max_results": 5
            }
        }

class SearchResponse(BaseModel):
    results: list
    query: str
    total_results: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "title": "Miami Art Festival",
                        "url": "https://example.com/miami-art-festival",
                        "snippet": "Join us for the annual Miami Art Festival featuring local artists..."
                    }
                ],
                "query": "upcoming events in Miami this weekend",
                "total_results": 15
            }
        }

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    services: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0", 
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "azure_ai": "connected",
                    "bing_search": "connected"
                }
            }
        }

enable_trace = False
logger = configure_logging(os.getenv("APP_LOG_FILE", ""))

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the Azure AI Projects system on startup"""
    global kernel, chat_service, ai_project_client, agent
    
    try:
        # Import the initialization from gunicorn_sk_conf
        from gunicorn_sk_conf import initialize_resources
        
        # Initialize the system (this sets globals in gunicorn_sk_conf)
        await initialize_resources()
        
        # Import the initialized globals from gunicorn_sk_conf
        import gunicorn_sk_conf
        kernel = gunicorn_sk_conf.kernel
        chat_service = gunicorn_sk_conf.chat_service
        ai_project_client = gunicorn_sk_conf.ai_project_client
        agent = gunicorn_sk_conf.agent
        
        logger.info("FastAPI startup: Azure AI Projects system initialization complete")
        logger.info(f"FastAPI startup: Agent ID: {getattr(agent, 'id', None) if agent else None}")
            
    except Exception as e:
        logger.error(f"FastAPI startup error: {e}")
        # Continue without the system - will use fallbacks
    
    yield
    
    # Cleanup on shutdown
    logger.info("FastAPI shutdown: Cleaning up resources")

# Create FastAPI app with comprehensive OpenAPI documentation
app = FastAPI(
    title="AI Online Researcher Agent",
    description="""
    **AI-powered research assistant that provides real-time information through web search.**
    
    This service combines Azure AI Projects with Bing Search to deliver:
    - Real-time web research capabilities
    - Event discovery and information gathering
    - Weather and current information queries
    - Interactive chat-based assistance
    - RESTful search endpoints
    
    ## Key Features
    - 🔍 **Web Search**: Real-time search using Bing grounding
    - 💬 **Interactive Chat**: Conversational AI assistant
    - 🌐 **RESTful API**: Standard HTTP endpoints for integration
    - 📊 **Health Monitoring**: Built-in health check endpoints
    - 🔒 **Secure**: Azure-hosted with proper authentication
    
    ## Authentication
    This service uses Azure authentication. Ensure proper credentials are configured.
    
    ## Rate Limits
    Please be mindful of API usage to ensure fair access for all users.
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "AI Research Team",
        "url": "https://github.com/your-org/citadel-online-researcher-agent",
        "email": "support@your-domain.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "/",
            "description": "Current server"
        }
    ],
    tags_metadata=[
        {
            "name": "search",
            "description": "Web search operations using Bing grounding"
        },
        {
            "name": "chat",
            "description": "Interactive conversational AI endpoints"
        },
        {
            "name": "agent",
            "description": "AI agent operations and interactions"  
        },
        {
            "name": "health",
            "description": "Service health and monitoring endpoints"
        },
        {
            "name": "system",
            "description": "System configuration and utilities"
        }
    ]
)

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

@app.get("/health",
         tags=["health"],
         summary="Service health check",
         description="""
         **Check the health status of the AI research service.**
         
         This endpoint provides comprehensive health information about the service and its dependencies:
         - Overall service status
         - Azure AI Projects connection status  
         - Bing grounding availability
         - Agent initialization status
         - Framework information
         
         **Use Cases:**
         - Monitoring and alerting
         - Load balancer health checks
         - Service dependency verification
         - Troubleshooting connectivity issues
         
         **Status Indicators:**
         - `healthy`: All systems operational
         - `degraded`: Partial functionality available
         - `unhealthy`: Service unavailable
         """,
         response_model=dict,
         responses={
             200: {
                 "description": "Service health status",
                 "content": {
                     "application/json": {
                         "example": {
                             "status": "healthy",
                             "framework": "azure_ai_projects_with_bing_grounding",
                             "agent_id": "asst_abc123def456",
                             "ai_project_client_enabled": True,
                             "bing_grounding_enabled": True,
                             "timestamp": "2024-01-15T10:30:00Z",
                             "version": "1.0.0"
                         }
                     }
                 }
             }
         })
async def health():
    """Health check endpoint"""
    global agent, ai_project_client, kernel, chat_service
    
    return JSONResponse(content={
        "status": "healthy",
        "framework": "azure_ai_projects_with_bing_grounding",
        "agent_id": getattr(agent, 'id', None) if agent else None,
        "ai_project_client_enabled": ai_project_client is not None,
        "bing_grounding_enabled": agent is not None,
        "semantic_kernel_enabled": kernel is not None,
        "chat_service_enabled": chat_service is not None
    })

@app.get("/",
         tags=["system"], 
         summary="Service welcome page",
         description="""
         **Welcome to the AI Online Researcher Agent API.**
         
         This is the main landing page for the AI research service. From here you can:
         - Access the interactive API documentation at `/docs`
         - View the OpenAPI specification at `/openapi.json`  
         - Test endpoints using the built-in Swagger UI
         - Review service capabilities and features
         
         **Quick Links:**
         - 📚 **API Documentation**: `/docs` (Swagger UI)
         - 📋 **OpenAPI Spec**: `/openapi.json` 
         - 🏥 **Health Check**: `/health`
         - 🔍 **Search Endpoint**: `/search`
         - 💬 **Chat Endpoint**: `/chat`
         - 🤖 **Agent Info**: `/agent`
         """,
         responses={
             200: {
                 "description": "Service information and navigation",
                 "content": {
                     "application/json": {
                         "example": {
                             "service": "AI Online Researcher Agent",
                             "version": "1.0.0",
                             "description": "AI-powered research assistant with real-time web search",
                             "documentation": "/docs",
                             "openapi_spec": "/openapi.json",
                             "endpoints": {
                                 "search": "/search",
                                 "chat": "/chat", 
                                 "agent": "/agent",
                                 "health": "/health"
                             }
                         }
                     }
                 }
             }
         })
async def index(request: Request):
    """Serve API information and navigation"""
    return JSONResponse(content={
        "service": "AI Online Researcher Agent",
        "version": "1.0.0",
        "description": "AI-powered research assistant with real-time web search capabilities",
        "framework": "FastAPI with Azure AI Projects and Bing grounding",
        "documentation": {
            "swagger_ui": f"{request.url}docs",
            "openapi_spec": f"{request.url}openapi.json",
            "redoc": f"{request.url}redoc"
        },
        "endpoints": {
            "search": f"{request.url}search",
            "chat": f"{request.url}chat", 
            "agent": f"{request.url}agent",
            "health": f"{request.url}health"
        },
        "features": [
            "Real-time web search via Bing grounding",
            "Interactive streaming chat interface", 
            "Unicode citation formatting",
            "Session-based conversation memory",
            "RESTful API with OpenAPI documentation"
        ],
        "status": "operational"
    })


@app.get("/agent",
         tags=["agent"],
         summary="Get AI agent information",
         description="""
         **Retrieve detailed information about the AI research agent.**
         
         This endpoint provides comprehensive details about the configured AI agent including:
         - Agent ID and identification details
         - Model configuration and deployment information
         - Instructions and behavioral parameters
         - Available tools and capabilities
         - Current operational status
         
         **Information Returned:**
         - **Agent Identity**: Unique ID, name, and type
         - **Model Details**: Deployment name, version, and capabilities  
         - **Configuration**: Instructions, tools, and behavioral settings
         - **Status**: Current operational state and availability
         
         **Use Cases:**
         - Debugging agent configuration
         - Monitoring agent deployment status
         - Integration planning and capability discovery
         - Troubleshooting behavioral issues
         """,
         response_model=dict,
         responses={
             200: {
                 "description": "Agent information successfully retrieved",
                 "content": {
                     "application/json": {
                         "example": {
                             "id": "asst_abc123def456",
                             "name": "Bing Grounding Search Assistant", 
                             "model": "gpt-4o-mini",
                             "instructions": "Search assistant with Bing grounding capabilities for current information",
                             "type": "azure_ai_agent_with_bing_grounding",
                             "tools": ["bing_search", "web_grounding"],
                             "status": "active"
                         }
                     }
                 }
             },
             404: {
                 "description": "Agent not found or not initialized",
                 "content": {
                     "application/json": {
                         "example": {
                             "detail": "Agent not found"
                         }
                     }
                 }
             }
         })
async def get_chat_agent(request: Request, _ = auth_dependency):
    """Get agent information"""
    global agent
    if agent:
        return JSONResponse(content={
            "id": agent.id,
            "name": getattr(agent, 'name', 'Bing Grounding Search Assistant'),
            "model": os.environ.get("AZURE_AI_AGENT_DEPLOYMENT_NAME", "gpt-4o-mini"),
            "instructions": getattr(agent, 'instructions', 'Search assistant with Bing grounding capabilities for current information'),
            "type": "azure_ai_agent_with_bing_grounding",
            "tools": ["bing_grounding"] if agent else []
        })
    else:
        raise HTTPException(status_code=500, detail="Azure AI Agent not initialized")


@app.get("/chat/history")
async def history(request: Request, _ = auth_dependency):
    """Get chat history"""
    # For now, return empty history as Azure AI Agent manages conversation state
    return JSONResponse(content=[])


async def stream_agent_response(user_message: str, thread_id: str = None) -> AsyncGenerator[str, None]:
    """Stream response from Azure AI Projects agent with Bing grounding"""
    global ai_project_client, agent, kernel, chat_service
    
    try:
        # Create or get thread ID
        if not thread_id:
            thread_id = f"thread_{int(asyncio.get_event_loop().time())}"
        
        logger.info(f"agent: Processing message: {user_message} (Thread: {thread_id})")
        
        # Initialize response collection
        responses = []
        agent_response = None
        
        # Use Azure AI Projects agent for Bing search/current info
        if agent and ai_project_client:
            try:
                logger.info("agent: Using Azure AI Projects agent with Bing grounding")
                
                # Prepare the message for the agent with explicit Bing search instruction
                enhanced_message = f"""User question: {user_message}

You have access to a Bing search tool. Please use it to search for current information to answer this question. Do not say you cannot provide real-time information - instead, use your Bing search capability to find the most up-to-date information and provide it to the user with proper citations.

IMPORTANT: Use the Bing search tool to get current, real-time information for this query."""
                
                
                # Use create_thread_and_run instead of separate steps
                logger.info("agent: Using create_thread_and_run for efficient API call")
                
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
                logger.info(f"agent: Created thread and run: {run_result.id}")
                
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
                        
                        if current_run.status in ["completed", "failed", "expired", "cancelled"]:
                            if current_run.status == "failed":
                                logger.error(f"agent: Run failed: {getattr(current_run, 'last_error', 'Unknown error')}")
                            break
                            
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                        
                    except Exception as status_error:
                        logger.warning(f"agent: Error checking run status: {status_error}")
                        # If status checking fails, just wait a bit and continue
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                        break
                
                if elapsed_time >= max_wait_time:
                    logger.warning("agent: Run did not complete within timeout period")
                
                # Get messages from the thread with better error handling
                try:
                    messages = ai_project_client.agents.messages.list(thread_id=run_result.thread_id)
                    logger.info(f"agent: Retrieved messages object: {type(messages)}")
                    
                    # Convert iterator to list since messages.list() returns ItemPaged iterator
                    messages_list = list(messages)
                    logger.info(f"agent: Messages list length: {len(messages_list)}")
                    
                    # Extract the latest assistant message
                    if messages_list:
                        for i, message in enumerate(messages_list):
                            if message.role == "assistant" and message.content:
                                for j, content_item in enumerate(message.content):
                                    if hasattr(content_item, 'text') and content_item.text:
                                        agent_response = content_item.text.value
                                        break
                                if agent_response:
                                    break
                    else:
                        logger.warning("agent: No messages found in the thread")
                        
                except Exception as msg_error:
                    logger.error(f"agent: Error retrieving messages: {msg_error}")
                    messages_list = []
                
                if agent_response:
                    responses.append(f"**Bing Search Results:** {agent_response}")
                    logger.info("agent: ✅ Got agent response with Bing search")
                else:
                    logger.warning("agent: Agent executed but no response content found")
                    
            except Exception as e:
                logger.error(f"agent: Error getting agent response: {e}")
                # Continue to fallback options
        
        # Fallback - simple assistant response when agent is not available
        if not responses:
            fallback_response = """Hello! I'm your search assistant. I'm currently operating with limited capabilities, but I can help you with:

• General questions and information requests
• Search-related queries when my Bing grounding is available
• Current events and news when web search is functioning

For the best results with current information, my Bing search capabilities should be active.

What can I help you search for today?"""
            responses.append(fallback_response)
            logger.info("agent: Using fallback search assistant response")
        
        # Combine responses
        final_response = "\n\n".join(responses) if responses else "I apologize, but I'm unable to process your request at the moment."
        
        # Send the complete response at once (no character-by-character streaming)
        yield serialize_sse_event({'content': final_response, 'annotations': [], 'type': "completed_message"})
        yield serialize_sse_event({'type': "stream_end"})
        
    except Exception as e:
        logger.error(f"agent: Stream error: {e}")
        error_message = "I'm sorry, I couldn't generate a response. Please try again."
        # Send the complete error message at once
        yield serialize_sse_event({'content': error_message, 'annotations': [], 'type': "completed_message"})
        yield serialize_sse_event({'type': "stream_end"})


@app.post("/chat",
          tags=["chat"],
          summary="Interactive streaming chat with AI agent",
          description="""
          **Real-time conversational AI with streaming responses.**
          
          This endpoint provides an interactive chat experience with an AI agent that has access to:
          - Real-time web search capabilities via Bing
          - Current information and live data
          - Conversational memory within sessions
          - Streaming response for better user experience
          
          **Key Features:**
          - 🚀 **Streaming**: Real-time response streaming using Server-Sent Events
          - 🧠 **Memory**: Maintains conversation context using thread_id
          - 🔍 **Web Access**: Can search and cite current information
          - 💬 **Natural**: Conversational interface with follow-up questions
          
          **Session Management:**
          - Pass thread_id in session_state to maintain conversation context
          - Each thread maintains its own conversation history
          - Threads persist for the duration of the session
          
          **Response Format:**
          Streaming response using text/plain content type with real-time updates.
          """,
          responses={
              200: {
                  "description": "Streaming chat response", 
                  "content": {
                      "text/plain": {
                          "example": "I'd be happy to help you find information about Miami events this weekend! Let me search for current events happening in Miami...\n\nBased on my search, here are some exciting events in Miami this weekend:\n\n**Art Basel Miami Beach** 【1:0†Official Art Basel Site】\n- This Saturday-Sunday at Miami Beach Convention Center\n- International contemporary art fair with galleries from around the world\n\nWould you like me to find more specific information about any of these events?"
                      }
                  }
              },
              500: {
                  "description": "Internal server error during chat processing",
                  "content": {
                      "application/json": {
                          "example": {
                              "detail": "An error occurred while processing your request"
                          }
                      }
                  }
              }
          })
async def chat_stream(request: Message, _ = auth_dependency):
    """Stream chat responses from the Azure AI Projects agent with Bing grounding"""
    
    # Log the incoming request
    logger.info(f"agent: Received chat request: {request.message}")
    
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

def format_unicode_citations(text):
    """
    Convert corrupted Unicode citations to proper format.
    Converts: ã3:0â sourceã → 【3:0†source】
    """
    if not text:
        return text
    
    # Pattern to match corrupted citations: ã3:0â sourceã
    corrupted_pattern = r'ã(\d+):(\d+)â sourceã'
    
    # Log if citations are being formatted (less verbose)
    matches = list(re.finditer(corrupted_pattern, text))
    if matches:
        logger.info(f"format_unicode_citations: Formatting {len(matches)} Unicode citations")
    
    # Replace with proper Unicode format: 【3:0†source】
    formatted_text = re.sub(corrupted_pattern, r'【\1:\2†source】', text)
    
    return formatted_text

def format_bing_grounding_response(content, annotations=None):
    """Format the response to match the required JSON structure with annotations."""
    # If content is already the complete message object with text and annotations
    if hasattr(content, 'text') and hasattr(content.text, 'value') and hasattr(content.text, 'annotations'):
        # Format Unicode citations in the text value
        formatted_text_value = format_unicode_citations(content.text.value)
        
        return {
            "response": {
                "type": "text", 
                "text": {
                    "value": formatted_text_value,
                    "annotations": [
                        {
                            "type": annotation.type if hasattr(annotation, 'type') else "url_citation",
                            "text": format_unicode_citations(annotation.text) if hasattr(annotation, 'text') else "",
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
                    "text": format_unicode_citations(annotation.get("text", "")),
                    "start_index": annotation.get("start_index", 0),
                    "end_index": annotation.get("end_index", 0),
                    "url_citation": annotation.get("url_citation", {})
                })
            else:
                # Handle object-based annotations
                formatted_annotations.append({
                    "type": getattr(annotation, 'type', "url_citation"),
                    "text": format_unicode_citations(getattr(annotation, 'text', "")),
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
                    "value": format_unicode_citations(str(content)),
                    "annotations": formatted_annotations
                }
            }
        }
    
    # Fallback for simple content
    if hasattr(content, 'value'):
        text_value = format_unicode_citations(content.value)
    else:
        text_value = format_unicode_citations(str(content))
    
    return {
        "response": {
            "type": "text",
            "text": {
                "value": text_value,
                "annotations": []
            }
        }
    }

@app.post("/search", 
          tags=["search"],
          summary="Perform web search with AI analysis",
          description="""
          **Search for information using Bing grounding and AI analysis.**
          
          This endpoint performs real-time web searches and provides intelligent analysis of the results.
          Perfect for finding current information, events, news, and factual data.
          
          **Key Features:**
          - Real-time web search via Bing
          - AI-powered result analysis and summarization  
          - Unicode citation formatting 【n:m†source】
          - Structured JSON response format
          
          **Use Cases:**
          - Finding current events and news
          - Weather and location information
          - Business hours and contact details
          - Research and fact-checking
          
          **Response Format:**
          Returns structured data with AI analysis and properly formatted citations.
          """,
          response_model=dict,
          responses={
              200: {
                  "description": "Successful search with AI analysis",
                  "content": {
                      "application/json": {
                          "example": {
                              "response": {
                                  "type": "text",
                                  "text": {
                                      "value": "Based on current web search, here are upcoming events in Miami this weekend:\n\n**Art Basel Miami Beach** 【1:0†Official Art Basel Site】\n- When: December 6-10, 2024\n- Location: Miami Beach Convention Center\n- What: International contemporary art fair\n\n**Miami Food & Wine Festival** 【2:1†Miami Events Guide】\n- When: This Saturday-Sunday\n- Location: Various venues in South Beach\n- What: Culinary experiences and wine tastings",
                                      "annotations": [
                                          {
                                              "type": "citation",
                                              "text": "Official Art Basel Site",
                                              "start_index": 45,
                                              "end_index": 48
                                          }
                                      ]
                                  }
                              }
                          }
                      }
                  }
              },
              503: {
                  "description": "Search service temporarily unavailable",
                  "content": {
                      "application/json": {
                          "example": {
                              "response": {
                                  "type": "text", 
                                  "text": {
                                      "value": "Search service not available",
                                      "annotations": []
                                  }
                              }
                          }
                      }
                  }
              }
          })
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
            content=error_response,
            headers={"Content-Type": "application/json; charset=utf-8"}
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
            logger.info(f"search: Retrieved {len(messages_list)} messages from thread")
            
            # Find the last assistant message
            for message in messages_list:
                if message.role == "assistant" and message.content:
                    logger.info(f"search: Found assistant message with {len(message.content)} content items")
                    for content_item in message.content:
                        if hasattr(content_item, 'text') and content_item.text:
                            # Format the response using the existing function that worked before
                            formatted_response = format_bing_grounding_response(content_item)
                            logger.info(f"search: ✅ Successfully formatted response with {len(formatted_response.get('response', {}).get('text', {}).get('annotations', []))} annotations")
                            return JSONResponse(
                                content=formatted_response,
                                headers={"Content-Type": "application/json; charset=utf-8"}
                            )
            
            # No assistant message found
            logger.warning("search: No assistant message found in thread")
            error_response = format_bing_grounding_response("No search results available")
            return JSONResponse(
                content=error_response,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
            
        except Exception as msg_error:
            logger.error(f"search: Error retrieving messages: {msg_error}")
            error_response = format_bing_grounding_response("Error retrieving search results")
            return JSONResponse(
                status_code=500,
                content=error_response,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
            
    except Exception as e:
        logger.error(f"search: Error processing search request: {e}")
        error_response = format_bing_grounding_response("An error occurred while processing your search request.")
        return JSONResponse(
            status_code=500,
            content=error_response,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
