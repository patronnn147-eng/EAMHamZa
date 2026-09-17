from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ruleid: fastapi-cors-wildcard-with-credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

app2 = FastAPI()

# ok: fastapi-cors-wildcard-with-credentials
app2.add_middleware(
    CORSMiddleware,
    allow_origins=["https://eamsagemcom.com"],
    allow_credentials=True,
    allow_methods=["*"],
)
