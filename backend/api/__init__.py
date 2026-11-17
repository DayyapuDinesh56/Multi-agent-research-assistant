from fastapi import APIRouter
from backend.api.research import router as research_router
from backend.api.documents import router as documents_router
from backend.api.briefings import router as briefings_router

router = APIRouter()

# Include sub-routers
router.include_router(research_router)
router.include_router(documents_router)
router.include_router(briefings_router)

def custom_openapi(app):
    from fastapi.openapi.utils import get_openapi
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    for component in openapi_schema.get("components", {}).get("schemas", {}).values():
        for prop in component.get("properties", {}).values():
            if prop.get("contentMediaType") == "application/octet-stream":
                prop["format"] = "binary"
                del prop["contentMediaType"]
            elif prop.get("type") == "array" and prop.get("items", {}).get("contentMediaType") == "application/octet-stream":
                items = prop["items"]
                items["format"] = "binary"
                del items["contentMediaType"]
    app.openapi_schema = openapi_schema
    return app.openapi_schema
