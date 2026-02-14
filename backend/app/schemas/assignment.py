import uuid
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class AssignmentItem(BaseModel):
    line_item_id: uuid.UUID
    user_ids: list[uuid.UUID]


class BulkAssignRequest(BaseModel):
    assignments: list[AssignmentItem]
    version: int  # receipt version for optimistic locking


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    line_item_id: uuid.UUID
    user_id: uuid.UUID
    share_amount: Decimal
