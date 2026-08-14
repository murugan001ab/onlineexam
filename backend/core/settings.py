import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB=os.getenv("DB","")



