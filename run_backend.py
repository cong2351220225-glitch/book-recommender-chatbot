import os
import sys
import uvicorn

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info")
