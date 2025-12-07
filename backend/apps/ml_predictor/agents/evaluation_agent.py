from typing import Dict, List, Any
import numpy as np

class EvaluationAgent:
    """Agent that compares algorithm results and selects the best model"""
    
    def __init__(self):
        pass
    
    async def evaluate_and_rank(self, algorithm_results: Dict[str, Dict[str, Any]], problem_type: str) -> Dict[str, Any]:
        """
        Compare all algorithm results and select the best model.
        Returns ranking, best model, and comparison report.
        """
        
        if not algorithm_results:
            return {
                "best_model": None,
                "best_metrics": {},
                "ranking": [],
                "comparison_report": {},
                "error": "No algorithm results to evaluate"
            }
        
        # Filter successful results
        successful_results = {
            name: result for name, result in algorithm_results.items()
            if result.get("success", False)
        }
        
        if not successful_results:
            return {
                "best_model": None,
                "best_metrics": {},
                "ranking": [],
                "comparison_report": {},
                "error": "No successful algorithm results"
            }
        
        # Rank algorithms based on primary metric
        ranking = self._rank_algorithms(successful_results, problem_type)
        
        # Get best model
        best_model_name = ranking[0]["algorithm_name"] if ranking else None
        best_metrics = ranking[0]["metrics"] if ranking else {}
        
        # Generate comparison report
        comparison_report = self._generate_comparison_report(ranking, problem_type)
        
        return {
            "best_model": best_model_name,
            "best_metrics": best_metrics,
            "ranking": ranking,
            "comparison_report": comparison_report,
            "success": True
        }
    
    def _rank_algorithms(self, results: Dict[str, Dict[str, Any]], problem_type: str) -> List[Dict[str, Any]]:
        """Rank algorithms by performance"""
        
        ranking = []
        
        for algo_name, result in results.items():
            metrics = result.get("metrics", {})
            
            # Determine primary metric based on problem type
            if problem_type == "classification":
                primary_metric = metrics.get("f1", metrics.get("accuracy", 0))
                metric_name = "F1 Score"
            else:
                primary_metric = metrics.get("r2", 1 - metrics.get("rmse", float('inf')))
                metric_name = "R² Score"
            
            ranking.append({
                "algorithm_name": algo_name,
                "metrics": metrics,
                "primary_metric": primary_metric,
                "primary_metric_name": metric_name,
                "training_time": result.get("training_time", 0),
                "feature_importance": result.get("feature_importance", {})
            })
        
        # Sort by primary metric (descending)
        ranking.sort(key=lambda x: x["primary_metric"], reverse=True)
        
        return ranking
    
    def _generate_comparison_report(self, ranking: List[Dict[str, Any]], problem_type: str) -> Dict[str, Any]:
        """Generate detailed comparison report"""
        
        if not ranking:
            return {}
        
        best = ranking[0]
        
        report = {
            "winner": best["algorithm_name"],
            "winner_metrics": best["metrics"],
            "winner_training_time": best["training_time"],
            "total_algorithms_evaluated": len(ranking),
            "all_rankings": [
                {
                    "rank": i + 1,
                    "algorithm": r["algorithm_name"],
                    "metrics": r["metrics"],
                    "training_time": r["training_time"]
                }
                for i, r in enumerate(ranking)
            ],
            "insights": self._generate_insights(ranking, problem_type)
        }
        
        return report
    
    def _generate_insights(self, ranking: List[Dict[str, Any]], problem_type: str) -> List[str]:
        """Generate insights about the results"""
        
        insights = []
        
        if not ranking:
            return insights
        
        best = ranking[0]
        
        # Insight 1: Winner
        insights.append(f"🏆 {best['algorithm_name']} is the best performer with {best['primary_metric_name']}: {best['primary_metric']:.4f}")
        
        # Insight 2: Training time
        if best['training_time'] < 0.1:
            insights.append(f"⚡ Very fast training time: {best['training_time']:.4f}s")
        elif best['training_time'] > 10:
            insights.append(f"⏱️ Longer training time: {best['training_time']:.2f}s")
        
        # Insight 3: Comparison with second best
        if len(ranking) > 1:
            second = ranking[1]
            diff = best['primary_metric'] - second['primary_metric']
            if diff > 0.1:
                insights.append(f"📈 Significant improvement over {second['algorithm_name']} ({diff:.4f} better)")
            else:
                insights.append(f"📊 Close competition with {second['algorithm_name']} ({diff:.4f} difference)")
        
        # Insight 4: Feature importance
        if best['feature_importance']:
            top_features = sorted(best['feature_importance'].items(), key=lambda x: x[1], reverse=True)[:3]
            if top_features:
                insights.append(f"🔍 Top features: {', '.join([f[0] for f in top_features])}")
        
        return insights
