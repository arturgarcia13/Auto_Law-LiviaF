import os

from dotenv import load_dotenv

load_dotenv()

SUBDOMAIN = os.getenv("SUBDOMAIN")
API_KEY = os.getenv("API_KEY")
