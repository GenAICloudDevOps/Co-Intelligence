from typing import Dict
import numpy as np
import lightgbm as lgb
from .base_algorithm import BaseAlgorithm
import time

class LightGBMClassifier(BaseAlgorithm):
    def __init__(self):
        super().__init__("lightgbm", "classification")
        self.model = lgb.LGBMClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, verbose=-1)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)

class LightGBMRegressor(BaseAlgorithm):
    def __init__(self):
        super().__init__("lightgbm_regressor", "regression")
        self.model = lgb.LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, verbose=-1)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)
