from fastapi import FastAPI
from typing import Dict

import uvicorn


app = FastAPI()

@app.get("/")
def sample() -> dict:
    print("Hello app!")
    return {"message": "Hello app"}


@app.get("/apps")
async def get_filtered_apps(request: Request, authentication: str = Depends(require_authentication)):
    try:
        # Get token from cookies
        access_token = request.cookies.get("access_token")
        
        # Debug: Print token details
        print(f"Token from cookies: {access_token}")
        print(f"Token length: {len(access_token) if access_token else 0}")
        print(f"Token starts with: {access_token[:10] if access_token else 'None'}")
        print(f"Token ends with: {access_token[-10:] if access_token else 'None'}")
        
        # Prepare request
        base_url = "https://api.pipedream.com/v1/apps"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-PD-Environment": "development"
        }
        
        # Debug: Print full headers (without the token for security)
        print(f"Request headers: { {k: v if k != 'Authorization' else 'Bearer [REDACTED]' for k, v in headers.items()}}")
        
        # Make the request
        response = requests.get(base_url, headers=headers)
        
        # Debug: Print response details
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response text: {response.text[:500]}...")  # First 500 chars of response
        
        # Rest of your code...


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)