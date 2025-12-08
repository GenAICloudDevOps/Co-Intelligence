from typing import Dict
import numpy as np
import xgboost as xgb
from .base_algorithm import BaseAlgorithm
import time

class XGBoostClassifier(BaseAlgorithm):
    def __init__(self):
        super().__init__("xgboost", "classification")
        self.model = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric='logloss')

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)

class XGBoostRegressor(BaseAlgorithm):
    def __init__(self):
        super().__init__("xgboost_regressor", "regression")
        self.model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)
