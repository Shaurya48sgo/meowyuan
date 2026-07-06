import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("MEOW_YUAN_TOKEN")
if not TOKEN:
    TOKEN = os.environ.get("MEOW_YUAN_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", 0))
