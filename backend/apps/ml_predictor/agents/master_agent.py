from typing import Dict, Any
from services.ai_service import ai_service
from apps.ml_predictor.algorithm_registry import algorithm_registry
from apps.ml_predictor.data_processor import DataProcessor
import json

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

Based on the problem description and dataset, determine:
1. Is this a CLASSIFICATION or REGRESSION problem?
2. What is the likely TARGET VARIABLE (column name)?
3. Provide brief reasoning.

Respond in JSON format:
{{
    "problem_type": "classification" or "regression",
    "target_variable": "column_name",
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
            
            return result
        except Exception as e:
            # Fallback: use heuristics
            return self._fallback_analysis(problem_description, dataset)
    
    def _fallback_analysis(self, problem_description: str, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis using heuristics"""
        
        # Determine problem type from description
        problem_lower = problem_description.lower()
        if any(word in problem_lower for word in ['classify', 'predict class', 'category', 'spam', 'survived', 'species']):
            problem_type = "classification"
        else:
            problem_type = "regression"
        
        # Detect target variable
        target = self.data_processor.detect_target_variable(
            None, problem_description
        ) if hasattr(self.data_processor, 'detect_target_variable') else dataset.get("column_names", ["target"])[-1]
        
        return {
            "problem_type": problem_type,
            "target_variable": target,
            "reasoning": "Determined using heuristics"
        }
    
    def select_algorithms(self, problem_type: str, dataset_size: int, feature_count: int) -> Dict[str, Any]:
        """Select best algorithms for the problem"""
        
        selected = algorithm_registry.get_algorithms_for_problem(
            problem_type, dataset_size, feature_count
        )
        
        return {
            "selected_algorithms": selected,
            "reasoning": f"Selected {len(selected)} best algorithms for {problem_type} problem with {dataset_size} samples and {feature_count} features"
        }
