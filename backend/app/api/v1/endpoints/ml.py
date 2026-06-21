"""ML Platform API — revenue prediction, explanation, training."""
from fastapi import APIRouter

from backend.app.schemas.ml import (
    PredictRequest, PredictResponse, ExplainRequest,
    TrainRequest, TrainResponse, GenericResult,
)
from backend.app.ml.feature_pipeline import build_dataset, raw_to_array
from backend.app.ml.training import train, save_model
from backend.app.ml.inference import predict_from_raw, set_model
from backend.app.ml.explainability import explain

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    return predict_from_raw(req.raw)


@router.post("/explain", response_model=GenericResult)
async def explain_prediction(req: ExplainRequest):
    _, features = raw_to_array(req.raw)
    return {"result": explain(features, top_k=req.top_k)}


@router.post("/train", response_model=TrainResponse)
async def train_model(req: TrainRequest):
    X, y = build_dataset(req.rows, req.targets)
    model = train(X, y)
    set_model(model)
    path = save_model(model) if req.save else None
    return {"backend": model.backend, "n_rows": len(X), "saved_path": path}
