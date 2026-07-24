from fastapi import FastAPI


app = FastAPI(title="Mini-CICD FastAPI Demo")


@app.get("/")
def root():
    return {
        "application": "mini-cicd-fastapi-demo",
        "status": "healthy",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
