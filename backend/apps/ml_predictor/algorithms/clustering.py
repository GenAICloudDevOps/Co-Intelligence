from typing import Dict, Any
import numpy as np
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import time
from .base_algorithm import BaseAlgorithm

class ClusteringAlgorithm(BaseAlgorithm):
    def __init__(self, name: str):
        super().__init__(name, "clustering")

    def get_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calculate clustering metrics. 
        y_true is expected to be X (data) for unsupervised metrics.
        y_pred are the cluster labels.
        """
        # Note: In the coordinator/agent flow, we might need to adjust what is passed as y_true.
        # Ideally, for clustering, we need X to calculate silhouette score.
        # If y_true is passed as X (which we will arrange), we use it.
        
        try:
            X = y_true # In our modified flow, we'll pass X as y_true for clustering evaluation
            if len(np.unique(y_pred)) < 2:
                return {"silhouette": -1.0, "calinski": 0.0, "davies": 0.0}
            
            return {
                "silhouette": float(silhouette_score(X, y_pred)),
                "calinski": float(calinski_harabasz_score(X, y_pred)),
                "davies": float(davies_bouldin_score(X, y_pred))
            }
        except Exception:
            return {"silhouette": 0.0, "calinski": 0.0, "davies": 0.0}

class KMeansAlgorithm(ClusteringAlgorithm):
    def __init__(self):
        super().__init__("kmeans")
        self.model = KMeans(n_clusters=3, random_state=42)

    def train(self, X_train: np.ndarray, y_train: np.ndarray = None) -> None:
        start_time = time.time()
        self.model.fit(X_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)

class DBSCANAlgorithm(ClusteringAlgorithm):
    def __init__(self):
        super().__init__("dbscan")
        self.model = DBSCAN(eps=0.5, min_samples=5)

    def train(self, X_train: np.ndarray, y_train: np.ndarray = None) -> None:
        start_time = time.time()
        self.model.fit(X_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        # DBSCAN cannot predict on new data in sklearn implementation
        # We return a placeholder or fit_predict on X_test if we treat it as transductive
        # For simplicity in this app, we might just return -1s or try to assign nearest core point
        # But properly, we should just return the labels_ from fit if X_test is X_train
        return self.model.fit_predict(X_test)

class HierarchicalAlgorithm(ClusteringAlgorithm):
    def __init__(self):
        super().__init__("hierarchical")
        self.model = AgglomerativeClustering(n_clusters=3)

    def train(self, X_train: np.ndarray, y_train: np.ndarray = None) -> None:
        start_time = time.time()
        self.model.fit(X_train)
        self.training_time = time.time() - start_time

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        # Agglomerative also doesn't predict. 
        return self.model.fit_predict(X_test)
