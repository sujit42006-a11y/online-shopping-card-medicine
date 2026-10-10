import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY=os.getenv("SECRET_KEY","dev-secret-change-me")
    DB_HOST=os.getenv("DB_HOST","localhost")
    DB_USER=os.getenv("DB_USER","root")
    DB_PASSWORD=os.getenv("DB_PASSWORD","")
    DB_NAME=os.getenv("DB_NAME","medikart")
    MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH",5*1024*1024))
    UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__),"uploads","prescriptions")
    ALLOWED_EXTENSIONS={"jpg","jpeg","png","pdf"}
