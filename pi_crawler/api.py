from fastapi import FastAPI, HTTPException
from .config import load_university_config
from .storage import save_profiles
from .cli import run_crawl

app = FastAPI()

@app.post("/crawl/{university_id}")
def crawl(university_id: str):
    try:
         run_crawl(university_id)
         return {"status": "success"}
    except FileNotFoundError as e:
         raise HTTPException(status_code=404, detail="Unknown University id.")

# @app.get("/universities/{university_id}/profiles")
# def list_profiles(university_id: str):
#     return save_profiles(university_id)
