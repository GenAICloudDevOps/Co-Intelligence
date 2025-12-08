from typing import Dict
import numpy as np
from sklearn.linear_model import ElasticNet
from .base_algorithm import BaseAlgorithm
import time

class ElasticNetRegressor(BaseAlgorithm):
    def __init__(self):
        super().__init__("elasticnet", "regression")
        self.model = ElasticNet(alpha=1.0, l1_ratio=0.5, random_state=42)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)
