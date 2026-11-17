from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import router, custom_openapi

app = FastAPI(title="Multi-Agent Research Assistant API - Gemini")

# Override default OpenAPI parser to support Swagger file selection fields
app.openapi = lambda: custom_openapi(app)

# Allow requests from Streamlit UI origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints router
app.include_router(router)
