import torch
from transformers import BertTokenizer, BertForSequenceClassification
from pathlib import Path

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "truthlens_fake_news_model"

model = BertForSequenceClassification.from_pretrained(str(MODEL_PATH))
tokenizer = BertTokenizer.from_pretrained(str(MODEL_PATH))

model.to(device)
model.eval()


def predict_news(text: str):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=160
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)

    fake_prob = probs[0][0].item()
    real_prob = probs[0][1].item()

    label = "Real" if real_prob > fake_prob else "Fake"

    return {
        "label": label,
        "fake_confidence": round(fake_prob * 100, 2),
        "real_confidence": round(real_prob * 100, 2)
    }