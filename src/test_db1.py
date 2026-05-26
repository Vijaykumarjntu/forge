import httpx

# Test directly before using libsql_client
async with httpx.AsyncClient() as http:
    resp = await http.post(
        "https://forge-vijaykumar.aws-ap-south-1.turso.io/v2/pipeline",
        headers={"Authorization": f"Bearer {turso_auth_token}"},
        json={
            "requests": [
                {"type": "execute", "stmt": {"sql": request.sql}},
                {"type": "close"}
            ]
        }
    )
    print("RAW TURSO RESPONSE:", resp.status_code, resp.json())