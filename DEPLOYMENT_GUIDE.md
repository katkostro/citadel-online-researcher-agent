# Deployment Guide: Chat App with AI Agent Backend

This guide provides step-by-step instructions for deploying both the frontend (chat app) and backend (AI agent) components to Azure.

## Prerequisites

- Azure CLI installed and configured
- Azure Developer CLI (azd) installed
- Node.js and npm installed
- Git installed
- Active Azure subscription with sufficient permissions

## Architecture Overview

```
┌─────────────────────┐    HTTPS/API calls    ┌──────────────────────────┐
│                     │ ────────────────────► │                          │
│   Frontend (SWA)    │                       │   Backend (Container    │
│   React TypeScript  │                       │   App + AI Services)    │
│                     │ ◄──────────────────── │                          │
└─────────────────────┘      Responses        └──────────────────────────┘
```

## Part 1: Deploy Backend (AI Agent)

### 1.1 Clone and Setup Backend Repository

```bash
# Clone the backend repository
git clone https://github.com/katkostro/citadel-online-researcher-agent.git
cd citadel-online-researcher-agent

# Login to Azure
az login
azd auth login
```

### 1.2 Initialize Azure Developer CLI

```bash
# Initialize the project with azd
azd init

# Set your environment name (replace with your preferred name)
azd env set AZURE_ENV_NAME "citadel-agent-prod"

# Set your preferred location
azd env set AZURE_LOCATION "eastus2"
```

### 1.3 Deploy Backend Infrastructure and Application

```bash
# Deploy all backend resources (this takes 5-10 minutes)
azd up

# Note: This creates:
# - Azure AI Foundry Project
# - Azure OpenAI Service with gpt-4o-mini model
# - Azure Container Apps for hosting the API
# - Azure Container Registry
# - Storage Account
# - Application Insights (optional)
# - Log Analytics Workspace
```

### 1.4 Get Backend URL

After deployment, note the backend URL from the output:

```bash
# Get the backend API URL
azd env get-values | findstr SERVICE_API_URI

# Example output:
# SERVICE_API_URI="https://ca-api-xyz123.region.azurecontainerapps.io"
```

**Important**: Save this URL - you'll need it for the frontend configuration.

## Part 2: Deploy Frontend (Chat App)

### 2.1 Clone and Setup Frontend Repository

```bash
# Clone the frontend repository (in a separate directory)
cd ..
git clone https://github.com/katkostro/chat-app.git
cd chat-app

# Install dependencies
npm install
```

### 2.2 Configure Frontend to Point to Backend

Create or update the `.env` file in the root of the chat-app directory:

```bash
# Create .env file with backend URL
echo "VITE_API_BASE_URL=https://ca-api-xyz123.region.azurecontainerapps.io" > .env
```

**Replace `https://ca-api-xyz123.region.azurecontainerapps.io` with your actual backend URL from Step 1.4**

### 2.3 Initialize and Deploy Frontend

```bash
# Initialize azd for frontend
azd init

# Set environment name (can be different from backend)
azd env set AZURE_ENV_NAME "citadel-chat-frontend"

# Set location (should match backend for best performance)
azd env set AZURE_LOCATION "eastus2"

# Set the backend URL as environment variable for build process
$env:VITE_API_BASE_URL = "https://your-backend-url-here.azurecontainerapps.io"

# Build the application with the environment variable
npm run build

# Deploy to Azure Static Web Apps
azd up
```

### 2.4 Get Frontend URL

After deployment, note the frontend URL:

```bash
# Get the frontend URL
azd env get-values | findstr CHAT_APP_URL

# Example output:
# CHAT_APP_URL="https://delightful-smoke-xyz.1.azurestaticapps.net"
```

## Part 3: Verify Deployment

### 3.1 Test Backend Endpoints

Test that your backend is responding:

```bash
# Test health endpoint
curl https://your-backend-url.azurecontainerapps.io/health

# Test agent endpoint
curl https://your-backend-url.azurecontainerapps.io/agent
```

### 3.2 Test Frontend-Backend Connection

1. Open your frontend URL in a browser: `https://your-frontend-url.azurestaticapps.net`
2. Open browser developer tools (F12)
3. Check the Network tab - API calls should go to your backend URL, not localhost
4. Try sending a message to verify the chat functionality works

## Part 4: Environment Configuration Details

### Backend Environment Variables (Automatic)

The `azd up` command automatically configures these environment variables in the Container App:

- `AZURE_CLIENT_ID` - Managed identity for authentication
- `AZURE_EXISTING_AIPROJECT_RESOURCE_ID` - AI Foundry project resource ID
- `AZURE_AI_AGENT_DEPLOYMENT_NAME` - OpenAI model deployment name
- `AZURE_TENANT_ID` - Azure tenant ID
- `RUNNING_IN_PRODUCTION` - Set to "true" for production environment

### Frontend Environment Variables (Manual)

You must configure this environment variable for the frontend:

```bash
# In chat-app/.env file:
VITE_API_BASE_URL=https://your-backend-url.azurecontainerapps.io
```

This variable is used in `src/config/api.ts`:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

## Part 5: Troubleshooting

### Frontend Shows "Error occurs while loading chat history!"

**Cause**: Frontend is calling localhost instead of the deployed backend.

**Solution**:
1. Verify the `.env` file contains the correct `VITE_API_BASE_URL`
2. Set the environment variable before building:
   ```bash
   $env:VITE_API_BASE_URL = "https://your-backend-url.azurecontainerapps.io"
   npm run build
   azd deploy
   ```

### 404 Errors for `/agent` or `/chat/history`

**Cause**: Frontend is making relative API calls instead of using the configured base URL.

**Solution**: The API configuration in `src/config/api.ts` should automatically handle this if `VITE_API_BASE_URL` is set correctly.

### CORS Errors

**Cause**: Backend not configured to accept requests from frontend domain.

**Solution**: The backend includes CORS middleware that allows all origins. If issues persist, check the Container App logs.

### Robot Avatar 404 Error

**Cause**: Missing avatar image file.

**Solution**: The frontend repository includes the avatar files in `public/static/assets/template-images/`.

## Part 6: Resource Management

### View Deployed Resources

**Backend Resources**:
```bash
cd citadel-online-researcher-agent
az resource list --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --output table
```

**Frontend Resources**:
```bash
cd chat-app
az resource list --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --output table
```

### Clean Up Resources

To avoid ongoing charges, delete the resource groups when done:

```bash
# Delete backend resources
cd citadel-online-researcher-agent
azd down --force --purge

# Delete frontend resources
cd ../chat-app
azd down --force --purge
```

## Part 7: Development vs Production

### Development Setup
- Frontend calls `http://localhost:8000` (uses vite.config.ts proxy)
- Backend runs locally with `python -m uvicorn "api.main:create_app" --factory --reload`
- Environment variables loaded from `.env` file

### Production Setup
- Frontend calls deployed backend URL via `VITE_API_BASE_URL`
- Backend deployed to Azure Container Apps
- Environment variables configured in Container App settings
- CORS middleware handles cross-origin requests

## Part 8: Production Security Configuration

### CORS Origins Restriction

⚠️ **IMPORTANT**: For production deployments, you should restrict CORS origins to specific frontend URLs for security.

**Current Development Configuration** (in both `src/main_sk.py` and `src/api/main.py`):
```python
allow_origins=["*"],  # Allow all origins - NOT SECURE for production
```

**Recommended Production Configuration**:
```python
allow_origins=[
    "https://your-frontend-domain.azurestaticapps.net",  # Your actual frontend URL
    "https://your-custom-domain.com",  # Any custom domain
    # Add localhost only if needed for local development
    "http://localhost:3000",
    "http://localhost:5173",
],
```

**Steps to Secure CORS for Production:**

1. **Get your frontend URL** after deployment:
   ```bash
   cd chat-app
   azd env get-value SERVICE_WEB_URI
   ```

2. **Update backend CORS configuration**:
   ```bash
   cd ../citadel-online-researcher-agent
   ```
   
   Edit both files:
   - `src/main_sk.py` (lines ~87-89)
   - `src/api/main.py` (lines ~123-125)
   
   Replace:
   ```python
   allow_origins=["*"],
   ```
   
   With:
   ```python
   allow_origins=[
       "https://your-actual-frontend-url.azurestaticapps.net",
       # Add any custom domains here
   ],
   ```

3. **Redeploy backend**:
   ```bash
   azd up
   ```

**Why This Matters:**
- `allow_origins=["*"]` allows ANY website to call your backend API
- Restricting origins prevents unauthorized websites from using your API
- Reduces risk of CSRF attacks and unauthorized access

## Summary

1. **Deploy Backend**: Run `azd up` in `citadel-online-researcher-agent` directory
2. **Get Backend URL**: Note the `SERVICE_API_URI` from deployment output
3. **Configure Frontend**: Set `VITE_API_BASE_URL` in chat-app `.env` file
4. **Deploy Frontend**: Set environment variable, build, and run `azd up` in `chat-app` directory
5. **Test**: Verify frontend can communicate with backend via browser developer tools
6. **Secure CORS**: Replace `allow_origins=["*"]` with specific frontend URLs for production

The key to success is ensuring the frontend's `VITE_API_BASE_URL` environment variable points to the correct deployed backend URL, and that this variable is set during the build process.
