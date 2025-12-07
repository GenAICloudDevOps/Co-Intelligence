from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import numpy as np

def safe_json_serialize(data):
    """Safely serialize data for JSON, handling numpy types and other non-serializable objects"""
    def default_handler(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int32, np.int64, np.float32, np.float64)):
            return float(obj) if 'float' in str(type(obj)) else int(obj)
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, 'item'):
            return obj.item()
        else:
            return str(obj)
    
    return json.dumps(data, default=default_handler)
import numpy as np

def safe_json_serialize(data):
    """Safely serialize data for JSON, handling numpy types and other non-serializable objects"""
    def default_handler(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int32, np.int64, np.float32, np.float64)):
            return float(obj) if 'float' in str(type(obj)) else int(obj)
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, 'item'):
            return obj.item()
        else:
            return str(obj)
    
    return json.dumps(data, default=default_handler)
from auth.utils import get_current_user
from auth.models import User
from apps.ml_predictor.models import Dataset, MLProject, ModelResult, TrainingRun
from apps.ml_predictor.agents.coordinator import MLPredictorCoordinator
from apps.ml_predictor.data_processor import DataProcessor
from apps.ml_predictor.algorithm_registry import algorithm_registry
import os
import uuid

router = APIRouter()
data_processor = DataProcessor()

class PredictRequest(BaseModel):
    dataset_id: int
    problem_description: str
    model: Optional[str] = "gemini-2.5-flash-lite"

class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rows: int
    columns: int
    is_sample: bool

class PasteRequest(BaseModel):
    text: str
    name: str

@router.post("/upload-dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = "Uploaded Dataset",
    current_user: User = Depends(get_current_user)
):
    """Upload a new dataset (CSV, JSON, Excel, PDF, Word)"""
    try:
        # Determine extension
        ext = os.path.splitext(file.filename)[1].lower()
        if not ext:
            ext = ".csv" # Default to csv if no extension
            
        file_path = f"/tmp/{uuid.uuid4()}{ext}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            df = data_processor.load_dataset(file_path)
        except Exception as e:
             # Clean up
             if os.path.exists(file_path):
                 os.remove(file_path)
             raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

        analysis = data_processor.analyze_dataset(df)
        
        dataset = await Dataset.create(
            user_id=current_user.id,
            name=name,
            file_path=file_path,
            rows=analysis["rows"],
            columns=analysis["columns"],
            column_names=analysis["column_names"],
            data_types=analysis["data_types"],
            is_sample=False
        )
        
        return {
            "id": dataset.id,
            "name": dataset.name,
            "rows": dataset.rows,
            "columns": dataset.columns,
            "column_names": dataset.column_names,
            "preview": df.head(5).to_dict(orient="records")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload-text")
async def upload_text(
    request: PasteRequest,
    current_user: User = Depends(get_current_user)
):
    """Upload dataset from raw text"""
    try:
        file_path = f"/tmp/{uuid.uuid4()}.csv"
        df = data_processor.load_data_from_text(request.text)
        
        # Save to file
        df.to_csv(file_path, index=False)
        
        analysis = data_processor.analyze_dataset(df)
        
        dataset = await Dataset.create(
            user_id=current_user.id,
            name=request.name,
            file_path=file_path,
            rows=analysis["rows"],
            columns=analysis["columns"],
            column_names=analysis["column_names"],
            data_types=analysis["data_types"],
            is_sample=False
        )
        
        return {
            "id": dataset.id,
            "name": dataset.name,
            "rows": dataset.rows,
            "columns": dataset.columns,
            "column_names": dataset.column_names,
            "preview": df.head(5).to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sample-datasets")
async def get_sample_datasets(current_user: User = Depends(get_current_user)):
    """Get available sample datasets"""
    try:
        datasets = await Dataset.filter(is_sample=True).all()
        return {
            "datasets": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "rows": d.rows,
                    "columns": d.columns,
                    "column_names": d.column_names
                }
                for d in datasets
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/datasets")
async def get_user_datasets(current_user: User = Depends(get_current_user)):
    """Get user's uploaded datasets"""
    try:
        datasets = await Dataset.filter(user_id=current_user.id, is_sample=False).all()
        return {
            "datasets": [
                {
                    "id": d.id,
                    "name": d.name,
                    "rows": d.rows,
                    "columns": d.columns,
                    "created_at": d.created_at.isoformat()
                }
                for d in datasets
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict")
async def predict(
    request: PredictRequest,
    current_user: User = Depends(get_current_user)
):
    """Run ML prediction on dataset"""
    try:
        dataset = await Dataset.get_or_none(id=request.dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        project = await MLProject.create(
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            name=f"Project {uuid.uuid4().hex[:8]}",
            problem_description=request.problem_description,
            problem_type="classification",
            target_variable="",
            status="processing"
        )
        
        df = data_processor.load_dataset(dataset.file_path)
        analysis = data_processor.get_dataset_summary(df)
        analysis["file_path"] = dataset.file_path
        
        # Initialize state as dict
        state = {
            "dataset": analysis,
            "problem_description": request.problem_description,
            "dataset_id": request.dataset_id,
            "dataset_size": analysis["total_rows"],
            "feature_count": analysis["total_columns"] - 1
        }
        
        coordinator = MLPredictorCoordinator(request.model)
        result = await coordinator.process(state)
        
        if result.get("error"):
            await project.update(status="failed", error_message=result["error"])
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Save model results
        algorithm_results = result.get("algorithm_results", {})
        for algo_name, algo_result in algorithm_results.items():
            if algo_result.get("success"):
                algo_meta = algorithm_registry.get_algorithm(algo_name)
                await ModelResult.create(
                    project_id=project.id,
                    algorithm_name=algo_name,
                    algorithm_display_name=algo_meta.display_name if algo_meta else algo_name,
                    metrics=algo_result.get("metrics", {}),
                    predictions=algo_result.get("predictions", []),
                    feature_importance=algo_result.get("feature_importance", {}),
                    training_time=algo_result.get("training_time", 0)
                )
        
        await TrainingRun.create(
            project_id=project.id,
            algorithms_used=result.get("selected_algorithms", []),
            best_model=result.get("best_model", ""),
            best_metrics=result.get("best_metrics", {}),
            comparison_report=result.get("comparison_report", {})
        )
        
        await project.update(
            status="completed",
            problem_type=result.get("problem_type", "classification"),
            target_variable=result.get("target_variable", "")
        )
        
        return {
            "project_id": project.id,
            "best_model": result.get("best_model"),
            "best_metrics": result.get("best_metrics", {}),
            "feature_importance": result.get("feature_importance", {}),
            "comparison_report": result.get("comparison_report", {}),
            "reasoning": result.get("reasoning", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/stream")
async def predict_stream(
    request: PredictRequest,
    current_user: User = Depends(get_current_user)
):
    """Run ML prediction with streaming status updates"""
    try:
        dataset = await Dataset.get_or_none(id=request.dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        project = await MLProject.create(
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            name=f"Project {uuid.uuid4().hex[:8]}",
            problem_description=request.problem_description,
            problem_type="classification",
            target_variable="",
            status="processing"
        )
        
        df = data_processor.load_dataset(dataset.file_path)
        analysis = data_processor.get_dataset_summary(df)
        analysis["file_path"] = dataset.file_path
        
        # Initialize state as dict
        state = {
            "dataset": analysis,
            "problem_description": request.problem_description,
            "dataset_id": request.dataset_id,
            "dataset_size": analysis["total_rows"],
            "feature_count": analysis["total_columns"] - 1
        }
        
        coordinator = MLPredictorCoordinator(request.model)
        
        async def event_generator():
            try:
                print(f"DEBUG: Starting prediction stream for project {project.id}")
                yield safe_json_serialize({"status": "started", "project_id": project.id}) + "\n"
                
                final_result = None
                
                async for update in coordinator.process_stream(state):
                    print(f"DEBUG: Stream update: {update.get('status')}")
                    yield safe_json_serialize(update) + "\n"
                    if update.get("status") == "completed":
                        final_result = update.get("result")
                
                if final_result:
                    if final_result.get("error"):
                        print(f"ERROR: Result contains error: {final_result['error']}")
                        await project.update(status="failed", error_message=final_result["error"])
                        yield safe_json_serialize({"status": "error", "message": final_result["error"]}) + "\n"
                        return

                    # Save results
                    print("DEBUG: Saving results...")
                    algorithm_results = final_result.get("algorithm_results", {})
                    
                    # Prepare all_results list for response
                    all_results_list = []
                    for algo_name, algo_result in algorithm_results.items():
                        if algo_result.get("success"):
                            algo_meta = algorithm_registry.get_algorithm(algo_name)
                            display_name = algo_meta.display_name if algo_meta else algo_name
                            
                            # Save to DB
                            await ModelResult.create(
                                project_id=project.id,
                                algorithm_name=algo_name,
                                algorithm_display_name=display_name,
                                metrics=algo_result.get("metrics", {}),
                                predictions=algo_result.get("predictions", []),
                                feature_importance=algo_result.get("feature_importance", {}),
                                training_time=algo_result.get("training_time", 0)
                            )
                            
                            all_results_list.append({
                                "algorithm": algo_name,
                                "display_name": display_name,
                                "metrics": algo_result.get("metrics", {}),
                                "training_time": f"{algo_result.get('training_time', 0):.4f}s",
                                "rank": 0 # To be filled
                            })
                    
                    # Sort results to determine rank
                    # For classification: accuracy (desc), f1 (desc)
                    # For regression: rmse (asc), r2 (desc)
                    # For clustering: silhouette (desc)
                    problem_type = final_result.get("problem_type", "classification")
                    
                    def sort_key(item):
                        metrics = item["metrics"]
                        if problem_type == "classification":
                            return metrics.get("accuracy", 0)
                        elif problem_type == "regression":
                            return -metrics.get("rmse", 1000) # Negative for descending sort
                        else: # clustering
                            return metrics.get("silhouette", -1)

                    all_results_list.sort(key=sort_key, reverse=True)
                    
                    # Assign ranks
                    for i, res in enumerate(all_results_list):
                        res["rank"] = i + 1

                    best_model = final_result.get("best_model", "")
                    best_metrics = final_result.get("best_metrics", {})

                    await TrainingRun.create(
                        project_id=project.id,
                        algorithms_used=final_result.get("selected_algorithms", []),
                        best_model=best_model,
                        best_metrics=best_metrics,
                        comparison_report=final_result.get("comparison_report", {})
                    )
                    
                    target_var = final_result.get("target_variable", "")
                    await project.update(
                        status="completed",
                        problem_type=problem_type,
                        target_variable=target_var
                    )
                    
                    # Construct winner details
                    winner_res = all_results_list[0] if all_results_list else {}
                    winner_algo = winner_res.get("algorithm", "")
                    winner_metrics = winner_res.get("metrics", {})
                    
                    runner_up_metrics = all_results_list[1].get("metrics", {}) if len(all_results_list) > 1 else None
                    
                    margin_msg = "Distinct winner"
                    if runner_up_metrics:
                        if problem_type == "classification":
                            diff = winner_metrics.get("accuracy", 0) - runner_up_metrics.get("accuracy", 0)
                            margin_msg = f"{(diff*100):.1f}% better accuracy than runner-up"
                        elif problem_type == "clustering":
                            diff = winner_metrics.get("silhouette", 0) - runner_up_metrics.get("silhouette", 0)
                            margin_msg = f"{diff:.2f} higher silhouette score"
                    
                    # Dataset split info (approximate 80/20)
                    total_rows = analysis["total_rows"]
                    train_rows = int(total_rows * 0.8)
                    test_rows = total_rows - train_rows
                    
                    response_data = {
                        "project_id": project.id,
                        "analysis": {
                            "problem_type": problem_type,
                            "target_variable": target_var or "None (Unsupervised)",
                            "reasoning": final_result.get("reasoning", ""),
                            "analysis_method": "Automated Feature Analysis"
                        },
                        "dataset_info": {
                            "name": dataset.name,
                            "total_rows": total_rows,
                            "train_rows": train_rows,
                            "test_rows": test_rows,
                            "train_percentage": 80,
                            "test_percentage": 20,
                            "features": analysis["total_columns"] - 1,
                            "feature_names": analysis["column_names"],
                            "target_column": target_var
                        },
                        "algorithm_selection": {
                            "selected_algorithms": final_result.get("selected_algorithms", []),
                            "reasoning": "Selected based on dataset characteristics.",
                            "selection_criteria": ["Problem Type Compatibility", "Dataset Size", "Feature Count"]
                        },
                        "all_results": all_results_list,
                        "winner": {
                            "algorithm": winner_algo,
                            "display_name": winner_res.get("display_name", ""),
                            "metrics": winner_metrics,
                            "training_time": winner_res.get("training_time", "0s"),
                            "reason": "Best overall performance metrics",
                            "margin": margin_msg
                        },
                        "feature_importance": final_result.get("feature_importance", {}),
                        "insights": [
                            f"The best model was {winner_res.get('display_name')}.",
                            f"Training was performed on {train_rows} samples.",
                            f"Evaluated {len(all_results_list)} different algorithms."
                        ]
                    }
                    print("DEBUG: Yielding final saved data")
                    yield safe_json_serialize({"status": "saved", "data": response_data}) + "\n"
                    
            except Exception as e:
                print(f"ERROR in event_generator: {str(e)}")
                import traceback
                traceback.print_exc()
                await project.update(status="failed", error_message=str(e))
                yield safe_json_serialize({"status": "error", "message": str(e)}) + "\n"

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects")
async def get_projects(current_user: User = Depends(get_current_user)):
    """Get user's projects"""
    try:
        projects = await MLProject.filter(user_id=current_user.id).all()
        return {
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "problem_description": p.problem_description,
                    "status": p.status,
                    "created_at": p.created_at.isoformat()
                }
                for p in projects
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get project details"""
    try:
        project = await MLProject.get_or_none(id=project_id, user_id=current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        results = await ModelResult.filter(project_id=project_id).all()
        training_run = await TrainingRun.get_or_none(project_id=project_id)
        
        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "problem_description": project.problem_description,
                "problem_type": project.problem_type,
                "target_variable": project.target_variable,
                "status": project.status,
                "created_at": project.created_at.isoformat()
            },
            "model_results": [
                {
                    "algorithm_name": r.algorithm_name,
                    "algorithm_display_name": r.algorithm_display_name,
                    "metrics": r.metrics,
                    "training_time": r.training_time,
                    "feature_importance": r.feature_importance
                }
                for r in results
            ],
            "training_run": {
                "best_model": training_run.best_model if training_run else None,
                "best_metrics": training_run.best_metrics if training_run else {},
                "comparison_report": training_run.comparison_report if training_run else {}
            } if training_run else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/algorithms")
async def get_algorithms():
    """Get all available algorithms"""
    try:
        algorithms = algorithm_registry.get_all_algorithms()
        return {
            "algorithms": [
                {
                    "name": a.name,
                    "display_name": a.display_name,
                    "type": a.algorithm_type,
                    "description": a.description,
                    "best_for": a.best_for,
                    "not_good_for": a.not_good_for
                }
                for a in algorithms
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/algorithms/{algorithm_name}")
async def get_algorithm(algorithm_name: str):
    """Get algorithm details"""
    try:
        info = algorithm_registry.get_algorithm_info(algorithm_name)
        if not info:
            raise HTTPException(status_code=404, detail="Algorithm not found")
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
