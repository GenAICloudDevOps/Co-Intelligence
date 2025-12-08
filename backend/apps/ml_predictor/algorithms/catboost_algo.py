from typing import Dict
import numpy as np
from catboost import CatBoostClassifier as CatBoostCls, CatBoostRegressor as CatBoostReg
from .base_algorithm import BaseAlgorithm
import time

class CatBoostClassifier(BaseAlgorithm):
    def __init__(self):
        super().__init__("catboost", "classification")
        self.model = CatBoostCls(iterations=100, depth=6, learning_rate=0.1, random_state=42, verbose=0)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)

class CatBoostRegressor(BaseAlgorithm):
    def __init__(self):
        super().__init__("catboost_regressor", "regression")
        self.model = CatBoostReg(iterations=100, depth=6, learning_rate=0.1, random_state=42, verbose=0)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)
