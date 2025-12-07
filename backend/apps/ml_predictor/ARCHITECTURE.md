# ML Predictor - Multi-Agent Architecture

## Overview

ML Predictor is a LangGraph-based multi-agent system that analyzes datasets and automatically determines whether a problem is classification or regression, then deploys multiple specialized agents using different algorithms to solve it.

## Agent Flow Diagram

```
                    USER INPUT
            (Dataset + Problem Description)
                         │
                         ▼
            ┌────────────────────────────┐
            │   MASTER AGENT             │
            │ - Analyze problem          │
            │ - Determine: Class/Regress │
            │ - Select algorithms        │
            └────────────┬───────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │AGENT 1 │      │AGENT 2 │      │AGENT 3 │
    │Algo A  │      │Algo B  │      │Algo C  │
    └────┬───┘      └────┬───┘      └────┬───┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
            ┌────────────────────────────┐
            │  EVALUATION AGENT          │
            │ - Compare metrics          │
            │ - Select best model        │
            │ - Generate report          │
            └────────────┬───────────────┘
                         │
                         ▼
            ┌────────────────────────────┐
            │   RESPONSE TO USER         │
            │ - Best model               │
            │ - Predictions              │
            │ - Metrics & Report         │
            └────────────────────────────┘
```

## Components

### 1. Algorithm Registry (`algorithm_registry.py`)
- Manages all available algorithms
- Provides algorithm metadata (name, type, best_for, not_good_for)
- Intelligently selects best algorithms based on dataset characteristics
- Extensible: easy to add new algorithms

**Key Methods:**
- `register()` - Register new algorithm
- `get_algorithms_for_problem()` - Get best algorithms for problem type
- `get_all_algorithms()` - List all algorithms
- `_calculate_relevance_score()` - Score algorithms based on dataset

### 2. Data Processor (`data_processor.py`)
- Loads datasets (CSV, JSON)
- Analyzes dataset structure and statistics
- Detects target variable
- Preprocesses data (handles missing values, encodes categorical)
- Splits data into train/test (80-20)
- Scales features

**Key Methods:**
- `load_dataset()` - Load from file
- `analyze_dataset()` - Get statistics
- `detect_target_variable()` - Find target column
- `preprocess_data()` - Clean and encode
- `split_data()` - Train-test split with scaling

### 3. Algorithms (`algorithms/`)
- 11 algorithms: 6 classification, 5 regression
- Each implements BaseAlgorithm interface
- Returns predictions, metrics, feature importance

**Classification:**
- Decision Tree
- Random Forest
- Gradient Boosting
- SVM
- Logistic Regression
- KNN

**Regression:**
- Linear Regression
- Ridge/Lasso
- SVR
- Random Forest Regressor
- Gradient Boosting Regressor

### 4. Agents (`agents/`)

#### Master Agent (`master_agent.py`)
- Analyzes problem description using AI
- Determines problem type (classification/regression)
- Detects target variable
- Selects best 3 algorithms using registry

#### Algorithm Agents (`algorithm_agent.py`)
- Trains specific algorithm
- Makes predictions
- Calculates metrics
- Extracts feature importance
- Runs in parallel

#### Evaluation Agent (`evaluation_agent.py`)
- Compares all algorithm results
- Ranks by performance
- Selects best model
- Generates insights and comparison report

#### Coordinator (`coordinator.py`)
- Orchestrates LangGraph workflow
- Manages state transitions
- Handles parallel execution
- Aggregates results

### 5. LangGraph Workflow (`graph/state.py`)
- Defines MLPredictorState
- Tracks: dataset, problem type, algorithms, results, best model
- Enables multi-agent orchestration

### 6. Database Models (`models.py`)
- `Dataset` - Store datasets
- `MLProject` - Track projects
- `ModelResult` - Store predictions and metrics
- `TrainingRun` - Track training history

### 7. API Routes (`routes.py`)
- `POST /upload-dataset` - Upload CSV/JSON
- `GET /sample-datasets` - Get sample datasets
- `GET /datasets` - List user datasets
- `POST /predict` - Run prediction
- `GET /projects` - List projects
- `GET /projects/{id}` - Get project details
- `GET /algorithms` - List algorithms
- `GET /algorithms/{name}` - Get algorithm info

## Workflow

1. **User Input**
   - Uploads dataset or selects sample
   - Describes problem

2. **Master Agent Analysis**
   - Analyzes problem description using AI
   - Examines dataset structure
   - Determines: Classification or Regression
   - Detects target variable

3. **Data Preparation**
   - Loads dataset
   - Handles missing values
   - Encodes categorical variables
   - Splits into train (80%) and test (20%)
   - Scales features

4. **Algorithm Selection**
   - Master Agent queries registry
   - Selects top 3 algorithms based on:
     - Problem type
     - Dataset size
     - Feature count
     - Data characteristics

5. **Parallel Training**
   - Each algorithm agent trains independently
   - Generates predictions on test set
   - Calculates metrics
   - Extracts feature importance

6. **Evaluation**
   - Evaluation Agent compares results
   - Ranks algorithms by performance
   - Selects best model
   - Generates insights

7. **Response**
   - Best model name and metrics
   - Predictions on test set
   - Feature importance
   - Comparison table
   - Insights and recommendations

## Algorithm Selection Logic

```python
IF dataset_size < 1000 AND features < 20:
    Prefer: Decision Tree, SVM, Logistic Regression
ELIF dataset_size > 10000 AND features > 50:
    Prefer: Random Forest, Gradient Boosting, Neural Networks
ELSE:
    Use: Top 3 from registry by relevance score
```

## Metrics

### Classification
- Accuracy
- Precision
- Recall
- F1 Score

### Regression
- RMSE (Root Mean Squared Error)
- MAE (Mean Absolute Error)
- R² Score
- MSE (Mean Squared Error)

## Sample Datasets

1. **Iris** - 150 samples, 4 features, 3 classes (classification)
2. **Breast Cancer** - 569 samples, 30 features, binary (classification)
3. **House Prices** - 1460 samples, 5 features (regression)
4. **Wine Quality** - 1599 samples, 11 features (regression)
5. **Titanic** - 891 samples, 6 features, binary (classification)

## Extensibility

### Adding New Algorithm

1. Create file: `algorithms/my_algorithm.py`
2. Implement BaseAlgorithm interface
3. Register in algorithm_registry.py
4. Master Agent automatically considers it

### Adding New Agent

1. Create agent class
2. Add node to coordinator graph
3. Define state transitions
4. Coordinator handles orchestration

## Tech Stack

- **Backend**: FastAPI + LangGraph 1.0.1
- **ML**: scikit-learn
- **Data**: pandas, numpy
- **Database**: PostgreSQL
- **AI**: Gemini/Groq/Bedrock (via ai_service)
- **Auth**: JWT

## Performance

- **Training Time**: Varies by algorithm and dataset size
- **Parallel Execution**: All algorithms train simultaneously
- **Memory**: Efficient data handling with pandas/numpy
- **Scalability**: Handles datasets up to 100K+ rows

## Error Handling

- Graceful fallback if AI analysis fails
- Algorithm-level error handling
- Project status tracking (pending, processing, completed, failed)
- Detailed error messages

## Future Enhancements

- Time series algorithms (ARIMA, Prophet, LSTM)
- Neural network support
- Hyperparameter tuning
- Cross-validation
- Model persistence and loading
- Batch predictions
- Real-time monitoring
