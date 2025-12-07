from abc import ABC, abstractmethod
from typing import Dict, Any, List
import numpy as np
import time

class BaseAlgorithm(ABC):
    """Base class for all ML algorithms"""
    
    def __init__(self, name: str, algorithm_type: str):
        self.name = name
        self.algorithm_type = algorithm_type  # "classification" or "regression"
        self.model = None
        self.training_time = 0.0
    
    @abstractmethod
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """Train the model"""
        pass
    
    @abstractmethod
    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """Make predictions"""
        pass
    
    @abstractmethod
    def get_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate performance metrics"""
        pass
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance if available"""
        if hasattr(self.model, 'feature_importances_'):
            return {f"feature_{i}": float(imp) for i, imp in enumerate(self.model.feature_importances_)}
        elif hasattr(self.model, 'coef_'):
            return {f"feature_{i}": float(abs(coef)) for i, coef in enumerate(self.model.coef_[0] if len(self.model.coef_.shape) > 1 else self.model.coef_)}
        return {}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": self.name,
            "type": self.algorithm_type,
            "training_time": self.training_time,
            "model_params": self.model.get_params() if hasattr(self.model, 'get_params') else {}
        }
