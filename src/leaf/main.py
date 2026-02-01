"""LEAF - Local Event-Driven Automation Framework.

FastAPI application entry point.
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from leaf.api.app_routes import router as app_router
from leaf.api.debug_routes import router as debug_router
from leaf.api.execution_routes import router as execution_router
from leaf.api.mcp_routes import router as mcp_router
from leaf.api.project_routes import router as project_router
from leaf.api.websocket import chat_websocket_endpoint, websocket_endpoint
from leaf.core.config import get_app_config
from leaf.watcher import stop_all_watches

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Sets up resources on startup and cleans up on shutdown.
    """
    # Startup
    # Ensure app config directory exists and load config
    _ = get_app_config()

    yield

    # Shutdown
    from leaf.mcp import disconnect_mcp_servers

    await disconnect_mcp_servers()
    await stop_all_watches()


# Create FastAPI application
app = FastAPI(
    title="LEAF",
    description="Local Event-Driven Automation Framework",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Tauri app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(app_router)
app.include_router(project_router)
app.include_router(execution_router)
app.include_router(mcp_router)
app.include_router(debug_router)

# Register WebSocket endpoints
app.websocket("/ws")(websocket_endpoint)
app.websocket("/ws/chat")(chat_websocket_endpoint)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": "LEAF",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def main():
    """Run the application with uvicorn."""
    import uvicorn

    port = int(os.environ.get("LEAF_PORT", 8000))
    uvicorn.run(
        "leaf.main:app",
        host="127.0.0.1",
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
