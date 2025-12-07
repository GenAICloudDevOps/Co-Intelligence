from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from apps.ml_predictor.graph.state import MLPredictorState
from apps.ml_predictor.agents.master_agent import MasterAgent
from apps.ml_predictor.agents.algorithm_agent import AlgorithmAgent
from apps.ml_predictor.agents.evaluation_agent import EvaluationAgent
from apps.ml_predictor.data_processor import DataProcessor
import asyncio

class MLPredictorCoordinator:
    """Orchestrates the ML Predictor workflow using LangGraph"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.master_agent = MasterAgent(model_name)
        self.evaluation_agent = EvaluationAgent()
        self.data_processor = DataProcessor()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(MLPredictorState)
        
        # Add nodes
        workflow.add_node("master_agent", self._master_agent_node)
        workflow.add_node("train_algorithms", self._train_algorithms_node)
        workflow.add_node("evaluation_agent", self._evaluation_agent_node)
        
        # Add edges
        workflow.add_edge(START, "master_agent")
        workflow.add_edge("master_agent", "train_algorithms")
        workflow.add_edge("train_algorithms", "evaluation_agent")
        workflow.add_edge("evaluation_agent", END)
        
        return workflow.compile()
    
    async def _master_agent_node(self, state: MLPredictorState) -> Dict[str, Any]:
        """Master agent node: analyze problem and select algorithms"""
        try:
            # Analyze problem
            analysis = await self.master_agent.analyze_problem(
                state.get("problem_description", ""),
                state.get("dataset", {})
            )
            
            dataset = state.get("dataset", {})
            
            # Determine problem type
            problem_type = analysis.get("problem_type", "classification")
            target_variable = analysis.get("target_variable")
            
            # If explicit clustering request or no target found, switch to clustering
            desc = state.get("problem_description", "").lower()
            if "cluster" in desc or "group" in desc or "segment" in desc or not target_variable:
                problem_type = "clustering"
                target_variable = None
            elif not target_variable:
                 # Fallback if analysis failed to find target but didn't explicitly say clustering
                 cols = dataset.get("column_names", [])
                 if cols:
                     target_variable = cols[-1]
            
            # Select algorithms
            selection = self.master_agent.select_algorithms(
                problem_type,
                state.get("dataset_size", 0),
                state.get("feature_count", 0)
            )
            
            return {
                "problem_type": problem_type,
                "target_variable": target_variable,
                "selected_algorithms": selection["selected_algorithms"],
                "reasoning": f"{analysis.get('reasoning', '')} | {selection['reasoning']}"
            }
        except Exception as e:
            return {
                "error": f"Master agent error: {str(e)}",
                "problem_type": "classification",
                "selected_algorithms": ["decision_tree", "random_forest", "gradient_boosting"]
            }
    
    async def _train_algorithms_node(self, state: MLPredictorState) -> Dict[str, Any]:
        """Train all selected algorithms in parallel"""
        try:
            # Prepare data
            dataset = state.get("dataset", {})
            df = self.data_processor.load_dataset(dataset.get("file_path", ""))
            X, y = self.data_processor.preprocess_data(df, state.get("target_variable", "target"))
            X_train, X_test, y_train, y_test = self.data_processor.split_data(X, y)
            
            # Train algorithms in parallel
            tasks = []
            for algo_name in state.get("selected_algorithms", []):
                agent = AlgorithmAgent(algo_name)
                tasks.append(agent.train_and_predict(X_train, X_test, y_train, y_test))
            
            results = await asyncio.gather(*tasks)
            
            # Aggregate results
            algorithm_results = {}
            for result in results:
                algo_name = result.get("algorithm_name")
                algorithm_results[algo_name] = result
            
            return {
                "algorithm_results": algorithm_results
            }
        except Exception as e:
            return {
                "error": f"Training error: {str(e)}",
                "algorithm_results": {}
            }
    
    async def _evaluation_agent_node(self, state: MLPredictorState) -> Dict[str, Any]:
        """Evaluation agent node: compare and select best model"""
        try:
            evaluation = await self.evaluation_agent.evaluate_and_rank(
                state.get("algorithm_results", {}),
                state.get("problem_type", "classification")
            )
            
            ranking = evaluation.get("ranking", [{}])
            return {
                "best_model": evaluation.get("best_model"),
                "best_metrics": evaluation.get("best_metrics", {}),
                "feature_importance": ranking[0].get("feature_importance", {}) if ranking else {},
                "comparison_report": evaluation.get("comparison_report", {})
            }
        except Exception as e:
            return {
                "error": f"Evaluation error: {str(e)}"
            }
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete workflow"""
        result = await self.graph.ainvoke(state)
        return result

    async def process_stream(self, state: Dict[str, Any]):
        """Execute workflow and yield status updates"""
        yield {
            "status": "started",
            "step": "init",
            "message": "Initializing workflow..."
        }
        
        async for event in self.graph.astream(state):
            for node, data in event.items():
                if node == "master_agent":
                    state.update(data)  # Update local state tracking
                    yield {
                        "status": "analyzing",
                        "step": "analysis",
                        "message": "Problem analysis completed. Algorithms selected.",
                        "data": {
                            "problem_type": data.get("problem_type"),
                            "algorithms": data.get("selected_algorithms")
                        }
                    }
                elif node == "train_algorithms":
                    state.update(data)
                    yield {
                        "status": "training",
                        "step": "training",
                        "message": "Model training completed.",
                        "data": {
                            "algorithm_count": len(data.get("algorithm_results", {}))
                        }
                    }
                elif node == "evaluation_agent":
                    state.update(data)
                    yield {
                        "status": "evaluating",
                        "step": "evaluation",
                        "message": "Evaluation completed. Best model selected.",
                        "data": {
                            "best_model": data.get("best_model")
                        }
                    }
        
        # Yield final result based on accumulated state
        yield {
            "status": "completed",
            "step": "finish",
            "message": "Workflow completed successfully.",
            "result": state
        }
