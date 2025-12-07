from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import numpy as np
import time
from .base_algorithm import BaseAlgorithm

class LogisticRegressionAlgorithm(BaseAlgorithm):
    def __init__(self):
        super().__init__("logistic_regression", "classification")
        self.model = LogisticRegression(max_iter=1000, random_state=42)
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time
    
    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)
    
    def get_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
        }
