from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from apps.ml_predictor.graph.state import MLPredictorState
from apps.ml_predictor.agents.master_agent import MasterAgent
from apps.ml_predictor.agents.algorithm_agent import AlgorithmAgent
from apps.ml_predictor.agents.evaluation_agent import EvaluationAgent
from apps.ml_predictor.data_processor import DataProcessor
from apps.ml_predictor.models import MLProject
import asyncio
import logging

logger = logging.getLogger(__name__)

class MLPredictorCoordinator:
    """Orchestrates the ML Predictor workflow using LangGraph"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.master_agent = MasterAgent(model_name)
        self.evaluation_agent = EvaluationAgent()
        self.data_processor = DataProcessor()
        self.graph = self._build_graph()
        self.project_id = None
    
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
    
    async def _log_step(self, step: str, message: str, status: str = "info"):
        """Log step and update project"""
        log_entry = {"step": step, "message": message, "status": status}
        logger.info(f"[{step}] {message}")
        
        if self.project_id:
            try:
                project = await MLProject.get(id=self.project_id)
                logs = project.step_logs or []
                logs.append(log_entry)
                await MLProject.filter(id=self.project_id).update(step_logs=logs)
            except Exception as e:
                logger.error(f"Failed to update project logs: {str(e)}")
    
    async def _update_project_status(self, status: str, current_step: str = None, progress: int = None):
        """Update project status"""
        if self.project_id:
            try:
                update_data = {"status": status}
                if current_step:
                    update_data["current_step"] = current_step
                if progress is not None:
                    update_data["progress"] = progress
                await MLProject.filter(id=self.project_id).update(**update_data)
            except Exception as e:
                logger.error(f"Failed to update project status: {str(e)}")
    
    async def _master_agent_node(self, state: MLPredictorState) -> Dict[str, Any]:
        """Master agent node: analyze problem and select algorithms"""
        try:
            await self._update_project_status("analyzing", "analyzing_problem", 10)
            await self._log_step("master_agent", "Starting problem analysis")
            
            # Analyze problem
            analysis = await self.master_agent.analyze_problem(
                state.get("problem_description", ""),
                state.get("dataset", {})
            )
            
            await self._log_step("master_agent", f"Problem type: {analysis.get('problem_type')}, Target: {analysis.get('target_variable')}")
            
            dataset = state.get("dataset", {})
            desc = state.get("problem_description", "").lower()
            
            # Determine problem type
            problem_type = analysis.get("problem_type", "classification")
            target_variable = analysis.get("target_variable")
            
            # Only use clustering if EXPLICITLY requested
            if "cluster" in desc or "segment" in desc or "group customers" in desc or "group users" in desc:
                problem_type = "clustering"
                target_variable = None
            else:
                # For regression/classification, ensure we have a target
                if not target_variable:
                    cols = dataset.get("column_names", [])
                    if cols:
                        # Use last column as target (common convention)
                        target_variable = cols[-1]
                
                # Detect regression keywords
                if any(word in desc for word in ["price", "predict", "forecast", "estimate", "value", "cost", "salary", "amount"]):
                    if problem_type == "clustering":
                        problem_type = "regression"
            
            # Select algorithms
            selection = self.master_agent.select_algorithms(
                problem_type,
                state.get("dataset_size", 0),
                state.get("feature_count", 0)
            )
            
            await self._log_step("master_agent", f"Selected algorithms: {', '.join(selection['selected_algorithms'])}")
            
            return {
                "problem_type": problem_type,
                "target_variable": target_variable,
                "selected_algorithms": selection["selected_algorithms"],
                "reasoning": f"{analysis.get('reasoning', '')} | {selection['reasoning']}"
            }
        except Exception as e:
            error_msg = f"Master agent error: {str(e)}"
            await self._log_step("master_agent", error_msg, "error")
            await self._update_project_status("failed", "analyzing_problem")
            return {
                "error": error_msg,
                "problem_type": "classification",
                "selected_algorithms": ["decision_tree", "random_forest", "gradient_boosting"]
            }
    
    async def _train_algorithms_node(self, state: MLPredictorState) -> Dict[str, Any]:
        """Train all selected algorithms in parallel"""
        try:
            await self._update_project_status("training", "training_algorithms", 40)
            await self._log_step("train_algorithms", f"Starting training of {len(state.get('selected_algorithms', []))} algorithms")
            
            # Prepare data
            dataset = state.get("dataset", {})
            df = self.data_processor.load_dataset(dataset.get("file_path", ""))
            X, y = self.data_processor.preprocess_data(df, state.get("target_variable", "target"))
            X_train, X_test, y_train, y_test = self.data_processor.split_data(X, y)
            feature_names = list(X.columns) if hasattr(X, "columns") else list(range(X.shape[1]))
            
            await self._log_step("train_algorithms", f"Data prepared: {X_train.shape[0]} training samples, {X_test.shape[0]} test samples")
            
            # Train algorithms in parallel
            tasks = []
            for algo_name in state.get("selected_algorithms", []):
                agent = AlgorithmAgent(algo_name)
                tasks.append(agent.train_and_predict(X_train, X_test, y_train, y_test))
            
            results = await asyncio.gather(*tasks)
            
            # Log results
            successful = sum(1 for r in results if r.get("success"))
            await self._log_step("train_algorithms", f"Training complete: {successful}/{len(results)} algorithms succeeded")
            
            # Aggregate results
            algorithm_results = {}
            for result in results:
                algo_name = result.get("algorithm_name")
                # Remap and normalize feature importance to real feature names
                fi = result.get("feature_importance") or {}
                if fi:
                    normalized = {}
                    total = sum(abs(v) for v in fi.values()) or 1.0
                    for idx, name in enumerate(feature_names):
                        val = fi.get(f"feature_{idx}", 0.0)
                        normalized[name] = float(abs(val)) / total
                    result["feature_importance"] = normalized
                algorithm_results[algo_name] = result
            
            return {
                "algorithm_results": algorithm_results
            }
        except Exception as e:
            error_msg = f"Training error: {str(e)}"
            await self._log_step("train_algorithms", error_msg, "error")
            await self._update_project_status("failed", "training_algorithms")
            return {
                "error": error_msg,
                "algorithm_results": {}
            }
    
    async def _evaluation_agent_node(self, state: MLPredictorState) -> Dict[str, Any]:
        """Evaluation agent node: compare and select best model"""
        try:
            await self._update_project_status("evaluating", "evaluating_models", 80)
            await self._log_step("evaluation_agent", "Starting model evaluation and ranking")
            
            evaluation = await self.evaluation_agent.evaluate_and_rank(
                state.get("algorithm_results", {}),
                state.get("problem_type", "classification")
            )
            
            best_model = evaluation.get("best_model")
            await self._log_step("evaluation_agent", f"Best model: {best_model}")
            
            ranking = evaluation.get("ranking", [{}])
            return {
                "best_model": evaluation.get("best_model"),
                "best_metrics": evaluation.get("best_metrics", {}),
                "feature_importance": ranking[0].get("feature_importance", {}) if ranking else {},
                "comparison_report": evaluation.get("comparison_report", {})
            }
        except Exception as e:
            error_msg = f"Evaluation error: {str(e)}"
            await self._log_step("evaluation_agent", error_msg, "error")
            await self._update_project_status("failed", "evaluating_models")
            return {
                "error": error_msg
            }
    
    async def process(self, state: Dict[str, Any], project_id: int = None) -> Dict[str, Any]:
        """Execute the complete workflow"""
        self.project_id = project_id
        try:
            result = await self.graph.ainvoke(state)
            await self._update_project_status("completed", "completed", 100)
            await self._log_step("coordinator", "Pipeline completed successfully")
            return result
        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            await self._log_step("coordinator", error_msg, "error")
            await self._update_project_status("failed", "error")
            return {"error": error_msg}

    async def process_stream(self, state: Dict[str, Any]):
        """Execute workflow and yield status updates"""
        yield {
            "status": "started",
            "step": "init",
            "message": "Initializing workflow..."
        }
        
        async for event in self.graph.astream(state):
            if event is None:
                continue
            
            for node, data in event.items():
                if data is None:
                    continue
                    
                if node == "master_agent":
                    state.update(data)
                    yield {
                        "status": "analyzing",
                        "step": "analysis",
                        "message": "Problem analysis completed. Algorithms selected.",
                            "data": {
                                "problem_type": data.get("problem_type"),
                                "algorithms": data.get("selected_algorithms")
                            }
                        }
                    if data.get("selected_algorithms"):
                        yield {
                            "status": "training_start",
                            "step": "training",
                            "message": f"Starting training for {len(data.get('selected_algorithms', []))} algorithms",
                            "data": {
                                "algorithms": data.get("selected_algorithms")
                            }
                        }
                elif node == "train_algorithms":
                    state.update(data)
                    algo_results = data.get("algorithm_results", {})
                    durations = {
                        name: f"{res.get('training_time', 0):.2f}s"
                        for name, res in algo_results.items()
                        if isinstance(res, dict)
                    }
                    yield {
                        "status": "training",
                        "step": "training",
                        "message": "Model training completed.",
                        "data": {
                            "algorithm_count": len(algo_results),
                            "durations": durations
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
