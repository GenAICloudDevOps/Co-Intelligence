from typing import Dict
import numpy as np
from sklearn.neural_network import MLPClassifier, MLPRegressor
from .base_algorithm import BaseAlgorithm
import time

class NeuralNetworkClassifier(BaseAlgorithm):
    def __init__(self):
        super().__init__("neural_network", "classification")
        self.model = MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)

class NeuralNetworkRegressor(BaseAlgorithm):
    def __init__(self):
        super().__init__("neural_network_regressor", "regression")
        self.model = MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        start_time = time.time()
        self.model.fit(X_train, y_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)
