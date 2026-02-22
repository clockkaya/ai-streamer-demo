"""
app.schemas
~~~~~~~~~~~
Pydantic schemas and models for the API.
"""
from app.schemas.api_response import ApiResponse
from app.schemas.live_interactions import (
    ChatMessageData,
    DanmakuRequest,
    DanmakuResponseData,
    HistoryResponseData,
    RoomInfoData,
)

# Call model_rebuild to resolve forward references in generic Pydantic models.
ApiResponse.model_rebuild()
