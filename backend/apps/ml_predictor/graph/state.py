from typing import Dict, List, Any, TypedDict

class MLPredictorState(TypedDict, total=False):
    """State for ML Predictor LangGraph workflow"""
    
    # Input
    dataset: Dict[str, Any]
    problem_description: str
    dataset_id: int
    
    # Analysis
    problem_type: str  # "classification" or "regression"
    target_variable: str
    dataset_size: int
    feature_count: int
    
    # Algorithm Selection
    selected_algorithms: List[str]
    
    # Training Results
    algorithm_results: Dict[str, Dict[str, Any]]
    
    # Evaluation
    best_model: str
    best_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    
    # Predictions
    predictions: List[Any]
    
    # Metadata
    reasoning: str
    comparison_report: Dict[str, Any]
    error: str
