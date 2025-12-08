from typing import Dict, Any
from services.ai_service import ai_service
from apps.ml_predictor.algorithm_registry import algorithm_registry
from apps.ml_predictor.data_processor import DataProcessor
import json
import logging

logger = logging.getLogger(__name__)

class MasterAgent:
    """Master agent for problem analysis and algorithm selection"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.data_processor = DataProcessor()
    
    async def analyze_problem(self, problem_description: str, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze problem and determine:
        1. Problem type (classification or regression)
        2. Target variable
        3. Best algorithms for this problem
        """
        
        # Prepare analysis prompt
        dataset_info = json.dumps({
            "rows": dataset.get("rows", 0),
            "columns": dataset.get("columns", 0),
            "column_names": dataset.get("column_names", []),
            "numeric_columns": dataset.get("numeric_columns", []),
            "categorical_columns": dataset.get("categorical_columns", [])
        }, indent=2)
        
        prompt = f"""You are an ML expert. Analyze this problem and dataset:

Problem Description: {problem_description}

Dataset Info:
{dataset_info}

IMPORTANT RULES:
- If predicting a continuous value (price, salary, amount, cost, age, score), it's REGRESSION
- If predicting a category/class (yes/no, species, type, survived), it's CLASSIFICATION  
- Only use CLUSTERING if explicitly asked to group/segment/cluster data without a target
- The target variable is usually the column being predicted (often the last column)

Based on the problem description and dataset, determine:
1. Is this a CLASSIFICATION or REGRESSION problem?
2. What is the TARGET VARIABLE (column name to predict)?
3. Provide brief reasoning.

Respond ONLY in JSON format:
{{
    "problem_type": "classification" or "regression",
    "target_variable": "exact_column_name_from_dataset",
    "reasoning": "brief explanation"
}}"""
        
        try:
            response = await ai_service.generate_response(prompt, self.model_name)
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)
            
            logger.info(f"Problem Analysis: {result}")
            return result
        except Exception as e:
            logger.error(f"Problem analysis failed: {str(e)}")
            return {
                "problem_type": "classification",
                "target_variable": None,
                "reasoning": f"Analysis failed: {str(e)}"
            }
    
    def select_algorithms(self, problem_type: str, dataset_size: int, feature_count: int) -> Dict[str, Any]:
        """Select best algorithms for the problem"""
        selected = algorithm_registry.get_algorithms_for_problem(problem_type, dataset_size, feature_count)
        
        algo_names = []
        algo_details = []
        for algo_name in selected:
            algo_meta = algorithm_registry.get_algorithm(algo_name)
            if algo_meta:
                algo_names.append(algo_name)
                algo_details.append({
                    "name": algo_name,
                    "display_name": algo_meta.display_name,
                    "description": algo_meta.description
                })
        
        reasoning = f"Selected {len(algo_names)} algorithms for {problem_type} problem with {dataset_size} samples and {feature_count} features"
        logger.info(f"Algorithm Selection: {reasoning} - {algo_names}")
        
        return {
            "selected_algorithms": algo_names,
            "algorithm_details": algo_details,
            "reasoning": reasoning
        }
