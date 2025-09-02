# API Documentation with Swagger UI

The AI Online Researcher Agent now includes comprehensive OpenAPI documentation with an interactive Swagger UI interface.

## Accessing the Documentation

Once deployed, you can access the interactive API documentation at these URLs:

### Swagger UI (Interactive)
- **URL**: `https://your-app-url.com/docs`
- **Description**: Interactive interface to explore and test all API endpoints
- **Features**: 
  - Try out API calls directly from the browser
  - View request/response schemas
  - See example requests and responses
  - Authentication testing

### ReDoc (Alternative Documentation)
- **URL**: `https://your-app-url.com/redoc`
- **Description**: Alternative documentation interface with different styling
- **Features**: 
  - Clean, readable documentation format
  - Detailed endpoint descriptions
  - Schema visualization

### OpenAPI Specification (JSON)
- **URL**: `https://your-app-url.com/openapi.json`
- **Description**: Raw OpenAPI specification in JSON format
- **Use Cases**: 
  - Import into other API tools (Postman, Insomnia)
  - Generate client libraries
  - Integration with API management platforms

## Enhanced Documentation Features

The API documentation now includes:

### 📚 **Comprehensive Endpoint Documentation**
- Detailed descriptions for all 12+ endpoints
- Input/output schemas with examples
- Error response documentation
- Tag-based organization (search, chat, agent, health, system)

### 🎯 **Tagged Endpoints**
- **search**: Web search operations using Bing grounding
- **chat**: Interactive conversational AI endpoints  
- **agent**: AI agent operations and information
- **health**: Service health and monitoring
- **system**: System configuration and utilities

### 📋 **Rich Metadata**
- Service description and capabilities
- Version information
- Contact and license details
- Server configuration
- Authentication requirements

### 🔍 **Request/Response Examples**
Each endpoint includes:
- Realistic example requests
- Expected response formats
- Error scenarios and status codes
- Parameter descriptions and constraints

## Key Endpoints Documented

### `/search` - Web Search with AI Analysis
- **Method**: POST
- **Purpose**: Real-time web search with AI analysis and Unicode citations
- **Features**: Bing grounding, structured responses, citation formatting

### `/chat` - Interactive Streaming Chat
- **Method**: POST  
- **Purpose**: Conversational AI with streaming responses
- **Features**: Session memory, real-time streaming, web access

### `/agent` - Agent Information
- **Method**: GET
- **Purpose**: Retrieve AI agent configuration and status
- **Features**: Model info, capabilities, operational status

### `/health` - Service Health Check
- **Method**: GET
- **Purpose**: Monitor service and dependency status
- **Features**: Comprehensive health reporting, dependency checks

### `/` - Service Information
- **Method**: GET
- **Purpose**: API overview and navigation
- **Features**: Endpoint directory, documentation links, feature list

## Usage Examples

### Accessing Swagger UI
1. Deploy your application using `azd up`
2. Navigate to `https://your-app-url.com/docs`
3. Explore the interactive documentation
4. Test endpoints directly from the interface

### Example API Call from Documentation
The Swagger UI allows you to:
1. Select an endpoint (e.g., `/search`)
2. Click "Try it out"
3. Enter your request data:
   ```json
   {
     "message": "What's happening in Miami this weekend?",
     "session_state": {}
   }
   ```
4. Click "Execute" to see the live response

### Integration with Other Tools
- **Postman**: Import from `https://your-app-url.com/openapi.json`
- **Insomnia**: Use the OpenAPI specification URL
- **Client Libraries**: Generate using OpenAPI generators

## Benefits of the New Documentation

1. **Developer Experience**: Easy API discovery and testing
2. **Integration Support**: Standard OpenAPI format for tooling
3. **Maintenance**: Self-updating documentation from code
4. **Collaboration**: Shareable, accessible API reference
5. **Quality**: Consistent, comprehensive endpoint documentation

## Next Steps

1. **Deploy**: Use `azd up` to deploy the enhanced version
2. **Test**: Access `/docs` to explore the interactive documentation
3. **Share**: Use the documentation URLs for team collaboration
4. **Integrate**: Import the OpenAPI spec into your preferred tools

The Swagger documentation makes the AI Online Researcher Agent much more accessible and easier to integrate with other applications and workflows.
