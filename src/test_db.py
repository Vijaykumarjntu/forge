import libsql_client
import json

# Paste your values from step 1
CONNECTION_STRING = "libsql://forge-vijaykumar.aws-ap-south-1.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3Nzk2OTk0OTMsImlkIjoiMDE5ZTVlNWEtNWIwMS03NmIyLTg4MjQtYWVkMzE0NzI4OTAwIiwicmlkIjoiZWU4OTgwYTUtYTVlYi00YTA5LWEyYWYtNjNiYWE2YTk1MWM0In0.50cPiqgRgNnC7SyxG-DcwHmgOM3XaNLAqrQzUfbbvqVWYc_dvXyTiVBtI2m52EVcw5aErvUCEEvJXBDhhIFSCw"
TABLE_NAME = "agent_data_24608a5a"

async def main():
    # Connect to Turso
    import httpx

    # Test directly before using libsql_client
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "https://forge-vijaykumar.aws-ap-south-1.turso.io/v2/pipeline",
            headers={"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"},
            json={
                "requests": [
                    {"type": "execute", "stmt": {"sql": request.sql}},
                    {"type": "close"}
                ]
            }
        )

    print("RAW TURSO RESPONSE:", resp.status_code, resp.json())

    async with libsql_client.create_client(
        url=CONNECTION_STRING,
        auth_token=TURSO_AUTH_TOKEN
    ) as client:
        
        # Create table
        await client.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"✅ Table '{TABLE_NAME}' created")
        
        # INSERT data
        await client.execute(
            f"INSERT INTO {TABLE_NAME} (key, value) VALUES (?, ?)",
            ("name", "InsForge Agent")
        )
        await client.execute(
            f"INSERT INTO {TABLE_NAME} (key, value) VALUES (?, ?)",
            ("purpose", "Build cool stuff")
        )
        print("✅ Data inserted")
        
        # READ data
        result = await client.execute(f"SELECT * FROM {TABLE_NAME}")
        
        print("\n📋 All data:")
        for row in result.rows:
            print(f"  ID: {row['id']}, Key: {row['key']}, Value: {row['value']}, Created: {row['created_at']}")
        
        # READ specific key
        result = await client.execute(
            f"SELECT value FROM {TABLE_NAME} WHERE key = ?",
            ("name",)
        )
        
        if result.rows:
            print(f"\n🔍 Value for 'name': {result.rows[0]['value']}")

# Run it
import asyncio
asyncio.run(main())