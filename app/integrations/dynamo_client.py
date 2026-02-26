"""DynamoDB client for session and user management."""
import time
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from app.config import AWS_REGION, SESSIONS_TABLE, USERS_TABLE, SESSION_TTL_SECONDS, USER_TTL_SECONDS
from app.models.schemas import Session, CitizenProfile

# Initialize DynamoDB (reused for Lambda warm starts)
_dynamodb = None


def get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return _dynamodb


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _convert_floats(obj):
    """Convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj


def get_session(session_id: str) -> Session:
    """Get session from DynamoDB, or create a new one."""
    table = get_dynamodb().Table(SESSIONS_TABLE)

    try:
        response = table.get_item(Key={"session_id": session_id})
        if "Item" in response:
            item = json.loads(json.dumps(response["Item"], cls=DecimalEncoder))
            return Session.from_dict(item)
    except Exception:
        pass

    # Create new session
    return Session(session_id=session_id)


def save_session(session: Session):
    """Save session to DynamoDB with TTL."""
    table = get_dynamodb().Table(SESSIONS_TABLE)
    item = session.to_dict()
    item["ttl"] = int(time.time()) + SESSION_TTL_SECONDS

    # Convert floats to Decimal
    item = _convert_floats(item)

    table.put_item(Item=item)


def delete_session(session_id: str):
    """Delete a session (right to erasure)."""
    table = get_dynamodb().Table(SESSIONS_TABLE)
    table.delete_item(Key={"session_id": session_id})
