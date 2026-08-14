import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB=os.getenv("DB","postgresql+psycopg://avnadmin:AVNS_gZR0OqN1cYI7PajU3sX@pg-8ad667a-murugan001ac-ad40.f.aivencloud.com:19573/exam?sslmode=require")



