import torch
from transformers import BertTokenizer, BertForSequenceClassification
from huggingface_hub import snapshot_download
from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager
import os

MODEL_REPO = "manvendra2004/truthlens-fake-news-model"
LOCAL_PATH = Path(__file__).resolve().parent.parent.parent / "truthlens_fake_news_model"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Global variables — loaded via lifespan
tokenizer = None
model = None

def _load_model():
    if not LOCAL_PATH.exists():
        print("[model_service] Downloading model from Hugging Face Hub...")
        snapshot_download(
            repo_id=MODEL_REPO,
            local_dir=str(LOCAL_PATH),
            token=os.getenv("HF_TOKEN")
        )
        print("[model_service] Model downloaded successfully.")
    else:
        print("[model_service] Using local model.")

    _tokenizer = BertTokenizer.from_pretrained(str(LOCAL_PATH))
    _model = BertForSequenceClassification.from_pretrained(str(LOCAL_PATH))
    _model.to(device)
    _model.eval()
    return _tokenizer, _model

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer, model
    tokenizer, model = _load_model()
    yield
    # cleanup on shutdown
    tokenizer = None
    model = None

def predict_news(text: str):
    if tokenizer is None or model is None:
        raise RuntimeError("Model not loaded yet.")

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=160,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)

    fake_prob = probs[0][0].item()
    real_prob = probs[0][1].item()
    label = "Real" if real_prob > fake_prob else "Fake"

    return {
        "label":           label,
        "fake_confidence": round(fake_prob * 100, 2),
        "real_confidence": round(real_prob * 100, 2),
    }