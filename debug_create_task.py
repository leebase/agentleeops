import os
import json
import urllib.request
import base64
from dotenv import load_dotenv

def debug_kanboard():
    load_dotenv()
    url = os.getenv('KANBOARD_URL')
    token = os.getenv('KANBOARD_TOKEN')
    user = os.getenv('KANBOARD_USER', 'jsonrpc')
    
    print(f"URL: {url}")
    print(f"User: {user}")
    
    def call(method, **params):
        auth_str = f"{user}:{token}"
        auth_header = base64.b64encode(auth_str.encode()).decode()
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": params
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode(), 
            headers={
                'Authorization': f'Basic {auth_header}', 
                'Content-Type': 'application/json'
            }
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            return {"error": str(e)}

    print("\n--- Test 1: getVersion ---")
    print(call("getVersion"))

    print("\n--- Test 2: getProjectById(1) ---")
    print(call("getProjectById", project_id=1))

    print("\n--- Test 3: createTask (Minimal) ---")
    # Try with project_id as int
    res = call("createTask", project_id=1, title="Debug Task Minimal")
    print(res)

    if res.get("result") is False:
        print("\n--- Test 4: createTask (with creator_id=1) ---")
        print(call("createTask", project_id=1, title="Debug Task Creator", creator_id=1))

    print("\n--- Test 5: getAllColumns(1) ---")
    cols = call("getColumns", project_id=1)
    print(cols)

    if isinstance(cols.get("result"), list) and len(cols["result"]) > 0:
        first_col_id = cols["result"][0]["id"]
        print(f"\n--- Test 6: createTask (with column_id={first_col_id}) ---")
        print(call("createTask", project_id=1, title="Debug Task Column", column_id=int(first_col_id)))

if __name__ == "__main__":
    debug_kanboard()
