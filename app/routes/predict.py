from fastapi import APIRouter
from pydantic import BaseModel
from app.services.model_service import predict_news

router = APIRouter(
    prefix="/predict",
    tags=["Prediction"]
)

class NewsInput(BaseModel):
    text: str


@router.post("/")
def predict(data: NewsInput):

    result = predict_news(data.text)


    return {
        "label": result["label"],
        "fake_confidence": result["fake_confidence"],
        "real_confidence": result["real_confidence"]
    }