from typing import Dict, Any
import numpy as np
from apps.ml_predictor.algorithms import (
    DecisionTreeAlgorithm,
    RandomForestAlgorithm,
    GradientBoostingAlgorithm,
    SVMAlgorithm,
    LogisticRegressionAlgorithm,
    KNNAlgorithm,
    LinearRegressionAlgorithm,
    RidgeLassoAlgorithm,
    SVRAlgorithm,
    RandomForestRegressorAlgorithm,
    GradientBoostingRegressorAlgorithm,
    NaiveBayesClassifier,
    NeuralNetworkClassifier,
    NeuralNetworkRegressor,
    ElasticNetRegressor
)
from apps.ml_predictor.algorithms.clustering import KMeansAlgorithm, DBSCANAlgorithm, HierarchicalAlgorithm

class AlgorithmAgent:
    """Agent that trains and evaluates a specific algorithm"""
    
    ALGORITHM_MAP = {
        "decision_tree": DecisionTreeAlgorithm,
        "random_forest": RandomForestAlgorithm,
        "gradient_boosting": GradientBoostingAlgorithm,
        "svm": SVMAlgorithm,
        "logistic_regression": LogisticRegressionAlgorithm,
        "knn": KNNAlgorithm,
        "linear_regression": LinearRegressionAlgorithm,
        "ridge_lasso": RidgeLassoAlgorithm,
        "svr": SVRAlgorithm,
        "random_forest_regressor": RandomForestRegressorAlgorithm,
        "gradient_boosting_regressor": GradientBoostingRegressorAlgorithm,
        "kmeans": KMeansAlgorithm,
        "dbscan": DBSCANAlgorithm,
        "hierarchical": HierarchicalAlgorithm,
        "naive_bayes": NaiveBayesClassifier,
        "neural_network": NeuralNetworkClassifier,
        "neural_network_regressor": NeuralNetworkRegressor,
        "elasticnet": ElasticNetRegressor
    }
    
    def __init__(self, algorithm_name: str):
        self.algorithm_name = algorithm_name
        if algorithm_name not in self.ALGORITHM_MAP:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")
        self.algorithm = self.ALGORITHM_MAP[algorithm_name]()
    
    async def train_and_predict(self, X_train: np.ndarray, X_test: np.ndarray, y_train: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Train algorithm and return predictions with metrics"""
        
        try:
            # Train
            self.algorithm.train(X_train, y_train)
            
            # Predict
            predictions = self.algorithm.predict(X_test)
            
            # Calculate metrics
            if self.algorithm.algorithm_type == "clustering":
                # For clustering, we evaluate based on the data structure (X_test) and the labels (predictions)
                metrics = self.algorithm.get_metrics(X_test, predictions)
            else:
                metrics = self.algorithm.get_metrics(y_test, predictions)
            
            # Get feature importance if available
            feature_importance = self.algorithm.get_feature_importance()
            
            # Get model info
            model_info = self.algorithm.get_model_info()
            
            return {
                "algorithm_name": self.algorithm_name,
                "predictions": predictions.tolist() if isinstance(predictions, np.ndarray) else predictions,
                "metrics": metrics,
                "feature_importance": feature_importance,
                "training_time": model_info["training_time"],
                "success": True
            }
        except Exception as e:
            return {
                "algorithm_name": self.algorithm_name,
                "success": False,
                "error": str(e)
            }
