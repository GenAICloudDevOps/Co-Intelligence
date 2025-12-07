from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np
import time
from .base_algorithm import BaseAlgorithm

class LinearRegressionAlgorithm(BaseAlgorithm):
    def __init__(self):
        super().__init__("linear_regression", "regression")
        self.model = LinearRegression()
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time
    
    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)
    
    def get_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        mse = mean_squared_error(y_true, y_pred)
        return {
            "rmse": float(np.sqrt(mse)),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "r2": float(r2_score(y_true, y_pred)),
            "mse": float(mse)
        }
