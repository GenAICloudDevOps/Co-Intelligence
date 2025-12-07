from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class AlgorithmMetadata:
    name: str
    display_name: str
    algorithm_type: str  # "classification" or "regression" or "both"
    best_for: List[str] = field(default_factory=list)
    not_good_for: List[str] = field(default_factory=list)
    description: str = ""
    parameters: Dict = field(default_factory=dict)
    relevance_score: float = 0.5

class AlgorithmRegistry:
    def __init__(self):
        self.algorithms: Dict[str, AlgorithmMetadata] = {}
        self._register_default_algorithms()
    
    def _register_default_algorithms(self):
        """Register all default algorithms"""
        
        # Classification Algorithms
        self.register(AlgorithmMetadata(
            name="decision_tree",
            display_name="Decision Tree",
            algorithm_type="classification",
            best_for=["small_datasets", "interpretability", "non_linear"],
            not_good_for=["very_large_datasets"],
            description="Tree-based model for classification with high interpretability",
            parameters={"max_depth": 10, "min_samples_split": 2}
        ))
        
        self.register(AlgorithmMetadata(
            name="random_forest",
            display_name="Random Forest",
            algorithm_type="classification",
            best_for=["medium_large_datasets", "non_linear", "feature_importance"],
            not_good_for=["very_small_datasets"],
            description="Ensemble of decision trees for robust classification",
            parameters={"n_estimators": 100, "max_depth": 10}
        ))
        
        self.register(AlgorithmMetadata(
            name="gradient_boosting",
            display_name="Gradient Boosting",
            algorithm_type="classification",
            best_for=["complex_patterns", "high_accuracy", "medium_large_datasets"],
            not_good_for=["very_small_datasets"],
            description="Sequential ensemble method for high accuracy classification",
            parameters={"n_estimators": 100, "learning_rate": 0.1}
        ))
        
        self.register(AlgorithmMetadata(
            name="svm",
            display_name="Support Vector Machine",
            algorithm_type="classification",
            best_for=["high_dimensional", "small_medium_datasets", "binary_classification"],
            not_good_for=["very_large_datasets"],
            description="Powerful classifier for high-dimensional data",
            parameters={"kernel": "rbf", "C": 1.0}
        ))
        
        self.register(AlgorithmMetadata(
            name="logistic_regression",
            display_name="Logistic Regression",
            algorithm_type="classification",
            best_for=["linear_separable", "interpretability", "fast_training"],
            not_good_for=["highly_non_linear"],
            description="Linear model for binary/multiclass classification",
            parameters={"max_iter": 1000}
        ))
        
        self.register(AlgorithmMetadata(
            name="knn",
            display_name="K-Nearest Neighbors",
            algorithm_type="classification",
            best_for=["small_datasets", "non_linear", "local_patterns"],
            not_good_for=["very_large_datasets", "high_dimensional"],
            description="Instance-based learning for classification",
            parameters={"n_neighbors": 5}
        ))
        
        # Regression Algorithms
        self.register(AlgorithmMetadata(
            name="linear_regression",
            display_name="Linear Regression",
            algorithm_type="regression",
            best_for=["linear_relationships", "interpretability", "fast_training"],
            not_good_for=["highly_non_linear"],
            description="Simple linear model for regression",
            parameters={"fit_intercept": True}
        ))
        
        self.register(AlgorithmMetadata(
            name="ridge_lasso",
            display_name="Ridge/Lasso Regression",
            algorithm_type="regression",
            best_for=["regularization", "feature_selection", "multicollinearity"],
            not_good_for=["highly_non_linear"],
            description="Regularized linear regression for better generalization",
            parameters={"alpha": 1.0}
        ))
        
        self.register(AlgorithmMetadata(
            name="svr",
            display_name="Support Vector Regression",
            algorithm_type="regression",
            best_for=["non_linear", "small_medium_datasets", "outliers"],
            not_good_for=["very_large_datasets"],
            description="Non-linear regression using support vectors",
            parameters={"kernel": "rbf", "C": 1.0}
        ))
        
        self.register(AlgorithmMetadata(
            name="random_forest_regressor",
            display_name="Random Forest Regressor",
            algorithm_type="regression",
            best_for=["complex_patterns", "medium_large_datasets", "feature_importance"],
            not_good_for=["very_small_datasets"],
            description="Ensemble of decision trees for regression",
            parameters={"n_estimators": 100, "max_depth": 10}
        ))
        
        self.register(AlgorithmMetadata(
            name="gradient_boosting_regressor",
            display_name="Gradient Boosting Regressor",
            algorithm_type="regression",
            best_for=["high_accuracy", "complex_patterns", "medium_large_datasets"],
            not_good_for=["very_small_datasets"],
            description="Sequential ensemble for high accuracy regression",
            parameters={"n_estimators": 100, "learning_rate": 0.1}
        ))

        # Clustering Algorithms
        self.register(AlgorithmMetadata(
            name="kmeans",
            display_name="K-Means Clustering",
            algorithm_type="clustering",
            best_for=["general_clustering", "flat_geometry", "even_cluster_size"],
            not_good_for=["irregular_shapes", "many_outliers"],
            description="Partitioning n observations into k clusters",
            parameters={"n_clusters": 3}
        ))

        self.register(AlgorithmMetadata(
            name="dbscan",
            display_name="DBSCAN",
            algorithm_type="clustering",
            best_for=["irregular_shapes", "outliers", "unknown_k"],
            not_good_for=["varying_density"],
            description="Density-based spatial clustering",
            parameters={"eps": 0.5, "min_samples": 5}
        ))

        self.register(AlgorithmMetadata(
            name="hierarchical",
            display_name="Hierarchical Clustering",
            algorithm_type="clustering",
            best_for=["hierarchy", "small_datasets"],
            not_good_for=["large_datasets"],
            description="Agglomerative clustering building a hierarchy",
            parameters={"n_clusters": 3}
        ))
    
    def register(self, metadata: AlgorithmMetadata):
        """Register a new algorithm"""
        self.algorithms[metadata.name] = metadata
    
    def get_algorithm(self, name: str) -> Optional[AlgorithmMetadata]:
        """Get algorithm by name"""
        return self.algorithms.get(name)
    
    def get_all_algorithms(self) -> List[AlgorithmMetadata]:
        """Get all registered algorithms"""
        return list(self.algorithms.values())
    
    def get_algorithms_for_problem(self, problem_type: str, dataset_size: int, feature_count: int) -> List[str]:
        """
        Get best algorithms for a given problem type and dataset characteristics.
        Returns list of algorithm names ranked by relevance.
        """
        candidates = []
        
        # Filter by problem type
        for algo in self.algorithms.values():
            if algo.algorithm_type == problem_type or algo.algorithm_type == "both":
                score = self._calculate_relevance_score(algo, dataset_size, feature_count)
                candidates.append((algo.name, score))
        
        # Sort by relevance score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 3 algorithm names
        return [name for name, _ in candidates[:3]]
    
    def _calculate_relevance_score(self, algo: AlgorithmMetadata, dataset_size: int, feature_count: int) -> float:
        """Calculate relevance score based on dataset characteristics"""
        score = 0.5
        
        # Dataset size scoring
        if dataset_size < 1000:
            if "small_datasets" in algo.best_for:
                score += 0.2
            if "very_large_datasets" in algo.not_good_for:
                score -= 0.1
        elif dataset_size < 100000:
            if "medium_large_datasets" in algo.best_for:
                score += 0.2
        else:
            if "very_large_datasets" in algo.not_good_for:
                score -= 0.2
        
        # Feature count scoring
        if feature_count > 100:
            if "high_dimensional" in algo.best_for:
                score += 0.2
            if "high_dimensional" in algo.not_good_for:
                score -= 0.2
        
        # Clamp score between 0 and 1
        return max(0.0, min(1.0, score))
    
    def get_algorithm_info(self, name: str) -> Dict:
        """Get detailed info about an algorithm"""
        algo = self.get_algorithm(name)
        if not algo:
            return {}
        
        return {
            "name": algo.name,
            "display_name": algo.display_name,
            "type": algo.algorithm_type,
            "description": algo.description,
            "best_for": algo.best_for,
            "not_good_for": algo.not_good_for,
            "parameters": algo.parameters
        }

# Global registry instance
algorithm_registry = AlgorithmRegistry()
