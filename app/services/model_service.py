import torch
from transformers import BertTokenizer, BertForSequenceClassification
from huggingface_hub import snapshot_download
from pathlib import Path
import os

MODEL_REPO = "manvendra2004/truthlens-fake-news-model"
LOCAL_PATH = Path(__file__).resolve().parent.parent.parent / "truthlens_fake_news_model"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

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

    tokenizer = BertTokenizer.from_pretrained(str(LOCAL_PATH))
    model     = BertForSequenceClassification.from_pretrained(str(LOCAL_PATH))
    model.to(device)
    model.eval()
    return tokenizer, model

tokenizer, model = _load_model()

def predict_news(text: str):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=160,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs   = torch.softmax(outputs.logits, dim=1)

    fake_prob = probs[0][0].item()
    real_prob = probs[0][1].item()
    label     = "Real" if real_prob > fake_prob else "Fake"

    return {
        "label":           label,
        "fake_confidence": round(fake_prob * 100, 2),
        "real_confidence": round(real_prob * 100, 2),
    }