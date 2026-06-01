from fastapi import FastAPI

app = FastAPI(title="Pardha Kernel")

@app.get("/")
def health():
    return {
        "name": "Pardha",
        "status": "alive"
    }