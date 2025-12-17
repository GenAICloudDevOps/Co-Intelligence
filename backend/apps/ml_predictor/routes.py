from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
from auth.utils import get_current_user
from auth.models import User
from apps.ml_predictor.models import Dataset, MLProject, ModelResult, TrainingRun
from apps.ml_predictor.agents.coordinator import MLPredictorCoordinator
from apps.ml_predictor.agents.algorithm_agent import AlgorithmAgent
from apps.ml_predictor.data_processor import DataProcessor
from apps.ml_predictor.algorithm_registry import algorithm_registry
from apps.ml_predictor.model_cache import model_cache, CachedModel
from apps.ml_predictor.model_store import PersistedModel, download_model_bundle, upload_model_bundle
from services.file_service import validate_file, save_temp_file, cleanup_file, TEMP_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from services.streaming import safe_serialize, sse_event, create_sse_response
from services.object_store import object_store

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
    name: str = Form("Uploaded Dataset"),
    current_user: User = Depends(get_current_user)
):
    """Upload a new dataset (CSV, JSON, Excel, PDF, Word)"""
    file_path = None
    try:
        # Validate file
        ext = os.path.splitext(file.filename)[1].lower() or ".csv"
        content = await file.read()
        
        valid, error = validate_file(file.filename, len(content))
        if not valid:
            raise HTTPException(status_code=400, detail=error)
        
        # Save file using central service
        file_path = await save_temp_file(content, ext)
        
        try:
            df = data_processor.load_dataset(file_path)
        except Exception as e:
            cleanup_file(file_path)
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to parse {ext} file. Error: {str(e)}"
            )

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
        cleanup_file(file_path)
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

@router.post("/upload-text")
async def upload_text(
    request: PasteRequest,
    current_user: User = Depends(get_current_user)
):
    """Upload dataset from raw text"""
    file_path = None
    try:
        # Validate text size
        if len(request.text) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Text too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        df = data_processor.load_data_from_text(request.text)
        
        # Save to file
        file_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.csv")
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
    except HTTPException:
        raise
    except Exception as e:
        cleanup_file(file_path)
        raise HTTPException(status_code=400, detail=f"Text upload failed: {str(e)}")
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
            status="pending",
            current_step="initializing",
            progress=0,
            step_logs=[]
        )
        
        try:
            df = data_processor.load_dataset(dataset.file_path)
        except Exception as e:
            await MLProject.filter(id=project.id).update(status="failed", error_message=f"Failed to load dataset: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to load dataset: {str(e)}")
        
        try:
            analysis = data_processor.get_dataset_summary(df)
            analysis["file_path"] = dataset.file_path
        except Exception as e:
            await MLProject.filter(id=project.id).update(status="failed", error_message=f"Failed to analyze dataset: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to analyze dataset: {str(e)}")
        
        # Initialize state as dict
        state = {
            "dataset": analysis,
            "problem_description": request.problem_description,
            "dataset_id": request.dataset_id,
            "dataset_size": analysis.get("total_rows", 0),
            "feature_count": analysis.get("total_columns", 1) - 1
        }
        
        coordinator = MLPredictorCoordinator(request.model)
        result = await coordinator.process(state, project_id=project.id)
        
        if result.get("error"):
            await MLProject.filter(id=project.id).update(status="failed", error_message=result["error"])
            raise HTTPException(status_code=500, detail=result["error"])
        
        try:
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
            
            await MLProject.filter(id=project.id).update(
                status="completed",
                problem_type=result.get("problem_type", "classification"),
                target_variable=result.get("target_variable", "")
            )

            # Persist best model bundle (shared across pods) - best-effort
            try:
                best_model_name = result.get("best_model", "")
                target_var = result.get("target_variable", "") or ""
                problem_type = result.get("problem_type", "classification")
                if best_model_name and target_var:
                    trainer = DataProcessor()
                    X_full, y_full = trainer.preprocess_data(df, target_var)
                    agent = AlgorithmAgent(best_model_name)
                    agent.algorithm.train(X_full, y_full)
                    bundle = PersistedModel(
                        model_name=best_model_name,
                        problem_type=problem_type,
                        target_variable=target_var,
                        feature_names=trainer.feature_names,
                        label_encoders=trainer.label_encoders,
                        model=agent.algorithm.model,
                    )
                    location = upload_model_bundle(project.id, bundle)
                    if location:
                        bucket, key = location
                        await TrainingRun.filter(project_id=project.id).update(
                            model_artifact_bucket=bucket,
                            model_artifact_key=key,
                        )
            except Exception:
                pass
        except Exception as e:
            await MLProject.filter(id=project.id).update(status="failed", error_message=f"Failed to save results: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save results: {str(e)}")
        
        return {
            "project_id": project.id,
            "best_model": result.get("best_model"),
            "best_metrics": result.get("best_metrics", {}),
            "feature_importance": result.get("feature_importance", {}),
            "comparison_report": result.get("comparison_report", {}),
            "reasoning": result.get("reasoning", "")
        }
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
                yield safe_serialize({"status": "started", "project_id": project.id}) + "\n"
                
                final_result = None
                
                async for update in coordinator.process_stream(state):
                    print(f"DEBUG: Stream update: {update.get('status')}")
                    yield safe_serialize(update) + "\n"
                    if update.get("status") == "completed":
                        final_result = update.get("result")
                
                if final_result:
                    if final_result.get("error"):
                        print(f"ERROR: Result contains error: {final_result['error']}")
                        await MLProject.filter(id=project.id).update(status="failed", error_message=final_result["error"])
                        yield safe_serialize({"status": "error", "message": final_result["error"]}) + "\n"
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
                    await MLProject.filter(id=project.id).update(
                        status="completed",
                        problem_type=problem_type,
                        target_variable=target_var
                    )

                    # Persist best model bundle (shared across pods) - best-effort
                    try:
                        if best_model and target_var:
                            trainer = DataProcessor()
                            X_full, y_full = trainer.preprocess_data(df, target_var)
                            agent = AlgorithmAgent(best_model)
                            agent.algorithm.train(X_full, y_full)
                            bundle = PersistedModel(
                                model_name=best_model,
                                problem_type=problem_type,
                                target_variable=target_var,
                                feature_names=trainer.feature_names,
                                label_encoders=trainer.label_encoders,
                                model=agent.algorithm.model,
                            )
                            location = upload_model_bundle(project.id, bundle)
                            if location:
                                bucket, key = location
                                await TrainingRun.filter(project_id=project.id).update(
                                    model_artifact_bucket=bucket,
                                    model_artifact_key=key,
                                )
                    except Exception:
                        pass
                    
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
                    feature_names_clean = [c for c in analysis["column_names"] if c != target_var]
                    # Normalize feature importance for response
                    fi = final_result.get("feature_importance", {}) or {}
                    if fi:
                        total_fi = sum(abs(v) for v in fi.values()) or 1.0
                        fi = {k: float(abs(v)) / total_fi for k, v in fi.items()}
                    
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
                            "features": max(len(feature_names_clean), 0),
                            "feature_names": feature_names_clean,
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
                        "feature_importance": fi,
                        "insights": [
                            f"The best model was {winner_res.get('display_name')}.",
                            f"Training was performed on {train_rows} samples.",
                            f"Evaluated {len(all_results_list)} different algorithms."
                        ]
                    }
                    print("DEBUG: Yielding final saved data")
                    yield safe_serialize({"status": "saved", "data": response_data}) + "\n"
                    
            except Exception as e:
                print(f"ERROR in event_generator: {str(e)}")
                import traceback
                traceback.print_exc()
                await MLProject.filter(id=project.id).update(status="failed", error_message=str(e))
                yield safe_serialize({"status": "error", "message": str(e)}) + "\n"

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

@router.get("/projects/{project_id}/status")
async def get_project_status(
    project_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get project processing status and logs"""
    try:
        project = await MLProject.get_or_none(id=project_id, user_id=current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "id": project.id,
            "status": project.status,
            "current_step": project.current_step,
            "progress": project.progress,
            "error_message": project.error_message,
            "step_logs": project.step_logs or [],
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/results")
async def get_project_results(
    project_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get complete project results with all details"""
    try:
        project = await MLProject.get_or_none(id=project_id, user_id=current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all model results
        model_results = await ModelResult.filter(project_id=project_id).all()
        
        # Get training run
        training_run = await TrainingRun.get_or_none(project_id=project_id)
        
        # Format results
        results_list = []
        for result in model_results:
            results_list.append({
                "algorithm_name": result.algorithm_name,
                "algorithm_display_name": result.algorithm_display_name,
                "metrics": result.metrics,
                "training_time": result.training_time,
                "feature_importance": result.feature_importance
            })
        
        return {
            "project_id": project.id,
            "status": project.status,
            "problem_type": project.problem_type,
            "target_variable": project.target_variable,
            "problem_description": project.problem_description,
            "step_logs": project.step_logs or [],
            "models_trained": results_list,
            "best_model": training_run.best_model if training_run else None,
            "best_metrics": training_run.best_metrics if training_run else {},
            "comparison_report": training_run.comparison_report if training_run else {},
            "error_message": project.error_message,
            "created_at": project.created_at.isoformat(),
            "completed_at": project.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Dataset Preview & Statistics
# ============================================

@router.get("/datasets/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: int,
    rows: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Get dataset preview with sample rows and statistics"""
    try:
        dataset = await Dataset.get_or_none(id=dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        df = data_processor.load_dataset(dataset.file_path)
        
        # Get statistics
        stats = {}
        for col in df.columns:
            col_stats = {"dtype": str(df[col].dtype), "missing": int(df[col].isnull().sum())}
            if df[col].dtype in ['int64', 'float64']:
                col_stats.update({
                    "min": float(df[col].min()) if not df[col].isnull().all() else None,
                    "max": float(df[col].max()) if not df[col].isnull().all() else None,
                    "mean": float(df[col].mean()) if not df[col].isnull().all() else None
                })
            else:
                col_stats["unique"] = int(df[col].nunique())
                col_stats["sample_values"] = df[col].dropna().unique()[:5].tolist()
            stats[col] = col_stats
        
        return {
            "id": dataset.id,
            "name": dataset.name,
            "rows": dataset.rows,
            "columns": dataset.columns,
            "column_names": dataset.column_names,
            "data_types": dataset.data_types,
            "preview": df.head(rows).to_dict(orient="records"),
            "statistics": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/datasets/{dataset_id}/visualization")
async def get_dataset_visualization(
    dataset_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get data for visualization (distributions, correlations)"""
    try:
        dataset = await Dataset.get_or_none(id=dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        df = data_processor.load_dataset(dataset.file_path)
        
        # Numeric columns for correlation
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        
        # Correlation matrix
        correlation = {}
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            correlation = corr_matrix.to_dict()
        
        # Distribution data for numeric columns
        distributions = {}
        for col in numeric_cols[:5]:  # Limit to 5 columns
            distributions[col] = {
                "histogram": df[col].dropna().tolist()[:1000],  # Limit data points
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "std": float(df[col].std())
            }
        
        # Categorical distributions
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        categorical_distributions = {}
        for col in categorical_cols[:5]:
            value_counts = df[col].value_counts().head(10).to_dict()
            categorical_distributions[col] = value_counts
        
        return {
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "correlation": correlation,
            "distributions": distributions,
            "categorical_distributions": categorical_distributions
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Single Prediction
# ============================================

class SinglePredictRequest(BaseModel):
    project_id: int
    features: dict  # {"column_name": value, ...}

@router.post("/predict/single")
async def predict_single(
    request: SinglePredictRequest,
    current_user: User = Depends(get_current_user)
):
    """Make a single prediction using the best trained model"""
    try:
        project = await MLProject.get_or_none(id=request.project_id, user_id=current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.status != "completed":
            raise HTTPException(status_code=400, detail="Project training not completed")
        
        # Get best model result
        training_run = await TrainingRun.get_or_none(project_id=project.id)
        if not training_run:
            raise HTTPException(status_code=400, detail="No trained models found")
        
        best_model_name = training_run.best_model

        # Prefer persisted model artifact (shared across pods); fallback to training on-the-fly
        bundle = None
        if training_run.model_artifact_bucket and training_run.model_artifact_key:
            try:
                cache_key = object_store.build_uri(training_run.model_artifact_bucket, training_run.model_artifact_key)
                cached = model_cache.get(project.id, best_model_name, cache_key)
                if cached:
                    bundle = cached.model
                else:
                    bundle = download_model_bundle(training_run.model_artifact_bucket, training_run.model_artifact_key)
                    model_cache.set(
                        CachedModel(
                            project_id=project.id,
                            model_name=best_model_name,
                            model=bundle,
                            feature_names=bundle.feature_names,
                            target_variable=bundle.target_variable,
                            dataset_path=cache_key,
                            dataset_mtime=0.0,
                        )
                    )
            except Exception:
                bundle = None

        if bundle is None:
            dataset = await Dataset.get_or_none(id=project.dataset_id)
            if not dataset or not dataset.file_path:
                raise HTTPException(status_code=400, detail="Dataset unavailable and no persisted model found")
            df = data_processor.load_dataset(dataset.file_path)
            trainer = DataProcessor()
            X_full, y_full = trainer.preprocess_data(df, project.target_variable)
            agent = AlgorithmAgent(best_model_name)
            agent.algorithm.train(X_full, y_full)
            bundle = PersistedModel(
                model_name=best_model_name,
                problem_type=project.problem_type,
                target_variable=project.target_variable,
                feature_names=trainer.feature_names,
                label_encoders=trainer.label_encoders,
                model=agent.algorithm.model,
            )

        # Prepare input features
        import pandas as pd
        input_df = pd.DataFrame([request.features])
        
        # Ensure columns match training data
        for col in bundle.feature_names:
            if col not in input_df.columns:
                input_df[col] = 0

        # Encode categoricals using saved encoders
        for col, encoder in (bundle.label_encoders or {}).items():
            if col == "target" or col not in input_df.columns:
                continue
            try:
                input_df[col] = input_df[col].apply(lambda x: x if x in encoder.classes_ else encoder.classes_[0])
                input_df[col] = encoder.transform(input_df[col].astype(str))
            except Exception:
                pass

        input_df = input_df[bundle.feature_names]
        
        # Make prediction
        prediction = bundle.model.predict(input_df.values)
        
        result = {
            "prediction": prediction[0] if len(prediction) == 1 else prediction.tolist(),
            "model_used": best_model_name,
            "problem_type": project.problem_type
        }
        
        # Add probability for classification
        if project.problem_type == "classification" and hasattr(bundle.model, 'predict_proba'):
            try:
                proba = bundle.model.predict_proba(input_df.values)
                result["probabilities"] = proba[0].tolist()
                result["confidence"] = float(max(proba[0])) * 100
            except:
                pass
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Batch Prediction
# ============================================

@router.post("/predict/batch")
async def predict_batch(
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Make predictions on a batch of data"""
    try:
        project = await MLProject.get_or_none(id=project_id, user_id=current_user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.status != "completed":
            raise HTTPException(status_code=400, detail="Project training not completed")
        
        # Get best model
        training_run = await TrainingRun.get_or_none(project_id=project.id)
        if not training_run:
            raise HTTPException(status_code=400, detail="No trained models found")
        
        best_model_name = training_run.best_model
        
        # Load original dataset and train model
        dataset = await Dataset.get_or_none(id=project.dataset_id)
        df_train = data_processor.load_dataset(dataset.file_path)
        X_train, y_train = data_processor.preprocess_data(df_train, project.target_variable)
        
        from apps.ml_predictor.agents.algorithm_agent import AlgorithmAgent
        agent = AlgorithmAgent(best_model_name)
        agent.algorithm.train(X_train, y_train)
        
        # Load new data
        content = await file.read()
        ext = os.path.splitext(file.filename)[1].lower() or ".csv"
        temp_path = await save_temp_file(content, ext)
        
        try:
            df_new = data_processor.load_dataset(temp_path)
            
            # Prepare features (exclude target if present)
            if project.target_variable and project.target_variable in df_new.columns:
                X_new = df_new.drop(columns=[project.target_variable])
            else:
                X_new = df_new
            
            # Encode categorical variables same as training
            X_new_processed = data_processor.preprocess_features(X_new)
            
            # Make predictions
            predictions = agent.algorithm.predict(X_new_processed)
            
            # Add predictions to dataframe
            df_new['prediction'] = predictions
            
            return {
                "total_rows": len(df_new),
                "predictions": df_new.to_dict(orient="records"),
                "model_used": best_model_name
            }
        finally:
            cleanup_file(temp_path)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
