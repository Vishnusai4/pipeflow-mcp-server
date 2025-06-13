from fastapi import FastAPI
from typing import Dict

import uvicorn


app = FastAPI()

@app.get("/")
def sample() -> dict:
    print("Hello app!")
    return {"message": "Hello app"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)