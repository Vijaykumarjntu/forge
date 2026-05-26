import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
# from src.main import verify_api_key
from typing import Optional, List, Any
import libsql_client

router = APIRouter()
# router = APIRouter()

# Request model for queries
class QueryRequest(BaseModel):
    sql: str
    params: Optional[List[Any]] = []


@router.post("/v1/dbs")
# async def create_ephemeral_db(api_key_hash: str = Depends(verify_api_key)):
async def create_ephemeral_db():
    # Get Turso credentials from .env
    turso_db_url = os.getenv("TURSO_DB_URL")
    turso_auth_token = os.getenv("TURSO_AUTH_TOKEN")
    
    if not turso_db_url or not turso_auth_token:
        raise HTTPException(
            status_code=500, 
            detail="TURSO_DB_URL and TURSO_AUTH_TOKEN must be set in .env"
        )
    
    # Generate unique table name for this agent request
    table_name = f"agent_data_{uuid.uuid4().hex[:8]}"
    
    return {
        "connection_string": turso_db_url,
        "auth_token": turso_auth_token,
        "table_name": table_name,
        "create_table_sql": f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "type": "turso",
        "usage_example": {
            "insert": f"INSERT INTO {table_name} (key, value) VALUES ('my_key', 'my_value')",
            "query": f"SELECT * FROM {table_name} WHERE key = 'my_key'",
            "delete": f"DROP TABLE {table_name}"
        }
    }

# @router.post("/v1/query")
# # async def run_query(request: QueryRequest, api_key_hash: str = Depends(verify_api_key)):
# async def run_query(request: QueryRequest):
#     """Run SQL query on the pre-configured Turso database"""
#     print("we are inside the run query")
#     turso_db_url = os.getenv("TURSO_DB_URL")
#     turso_auth_token = os.getenv("TURSO_AUTH_TOKEN")
    
#     if not turso_db_url or not turso_auth_token:
#         raise HTTPException(
#             status_code=500, 
#             detail="TURSO_DB_URL and TURSO_AUTH_TOKEN not configured"
#         )
#     try:

#         import httpx

#         # Test directly before using libsql_client
#         async with httpx.AsyncClient() as http:
#             resp = await http.post(
#                 "https://forge-vijaykumar.aws-ap-south-1.turso.io/v2/pipeline",
#                 headers={"Authorization": f"Bearer {turso_auth_token}"},
#                 json={
#                     "requests": [
#                         {"type": "execute", "stmt": {"sql": request.sql}},
#                         {"type": "close"}
#                     ]
#                 }
#             )
    
#         print("RAW TURSO RESPONSE:", resp.status_code, resp.json())

#         async with libsql_client.create_client(
#             # url=turso_db_url,
#             url="https://forge-vijaykumar.aws-ap-south-1.turso.io",
#             auth_token=turso_auth_token
#         ) as client:
#             print("we are inside the try block")
#             # Execute the query
#             print(request)
#             print(request.sql)
#             print(client)
#             result = "abcd"
#             if request.params:
#                 print("we are inside the if")
#                 result = await client.execute(request.sql, request.params)
#             else:
#                 print("else block working")
#                 result = await client.execute(request.sql)
#             print("we are after client execute")
#             # Format response
#             if result.rows:
#                 # SELECT query - return data
#                 return {
#                     "success": True,
#                     "rows": [dict(row) for row in result.rows],
#                     "row_count": len(result.rows),
#                     "columns": list(result.rows[0].keys()) if result.rows else []
#                 }
#             else:
#                 # INSERT/UPDATE/DELETE - return affected rows
#                 return {
#                     "success": True,
#                     "affected_rows": result.rows_affected if hasattr(result, 'rows_affected') else 0,
#                     "message": "Query executed successfully"}
#     except Exception as e:
#         print(f"Full error: {e}")
#         print(f"Error type: {type(e)}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=400, detail=str(e))
import httpx

@router.post("/v1/query")
async def run_query(request: QueryRequest):
    turso_db_url = os.getenv("TURSO_DB_URL", "").replace("libsql://", "https://")
    turso_auth_token = os.getenv("TURSO_AUTH_TOKEN")

    if not turso_db_url or not turso_auth_token:
        raise HTTPException(status_code=500, detail="TURSO_DB_URL and TURSO_AUTH_TOKEN not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{turso_db_url}/v2/pipeline",
                headers={"Authorization": f"Bearer {turso_auth_token}"},
                json={
                    "requests": [
                        {"type": "execute", "stmt": {"sql": request.sql, "args": request.params or []}},
                        {"type": "close"}
                    ]
                }
            )
            data = response.json()
            result = data["results"][0]

            if result["type"] == "error":
                raise HTTPException(status_code=400, detail=result["error"]["message"])

            res = result["response"]["result"]
            cols = [c["name"] for c in res["cols"]]
            rows = [dict(zip(cols, [v["value"] for v in row])) for row in res["rows"]]

            if rows:
                return {"success": True, "rows": rows, "row_count": len(rows), "columns": cols}
            else:
                return {"success": True, "affected_rows": res["affected_row_count"], "message": "Query executed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))