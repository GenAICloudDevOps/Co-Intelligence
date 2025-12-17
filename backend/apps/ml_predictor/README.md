# ML Predictor App

🤖 Multi-agent ML system that analyzes datasets and predicts using multiple algorithms.

## Features

✅ **Multi-Agent System** - 5 specialized agents (Master, Algorithm x3, Evaluation)  
✅ **Auto Problem Detection** - Determines classification vs regression  
✅ **11 Algorithms** - 6 classification, 5 regression  
✅ **Intelligent Selection** - Picks best algorithms for your problem  
✅ **Dataset Upload** - CSV/JSON support  
✅ **5 Sample Datasets** - Pre-loaded for testing  
✅ **Train-Test Split** - 80-20 split with scaling  
✅ **Comprehensive Metrics** - Accuracy, RMSE, F1, Precision, Recall, R²  
✅ **Feature Importance** - Shows which features matter most  
✅ **Comparison Reports** - Side-by-side algorithm comparison  
✅ **PostgreSQL Storage** - Persist all projects and results  

## How It Works

1. **Upload Dataset** - CSV or JSON file
2. **Describe Problem** - "Predict house prices", "Classify emails as spam"
3. **System Analyzes** - Determines problem type and target variable
4. **Selects Algorithms** - Picks best 3 algorithms for your problem
5. **Trains in Parallel** - All algorithms train simultaneously
6. **Compares Results** - Ranks by performance
7. **Returns Best Model** - With predictions and insights

## API Endpoints

### Dataset Management
```
POST   /api/apps/ml-predictor/upload-dataset
GET    /api/apps/ml-predictor/sample-datasets
GET    /api/apps/ml-predictor/datasets
```

### Prediction
```
POST   /api/apps/ml-predictor/predict
GET    /api/apps/ml-predictor/projects
GET    /api/apps/ml-predictor/projects/{id}
```

### Algorithm Info
```
GET    /api/apps/ml-predictor/algorithms
GET    /api/apps/ml-predictor/algorithms/{name}
```

## Example Usage

### Upload Dataset
```bash
curl -X POST http://localhost:8000/api/apps/ml-predictor/upload-dataset \
  -F "file=@data.csv" \
  -F "name=My Dataset" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Sample Datasets
```bash
curl http://localhost:8000/api/apps/ml-predictor/sample-datasets \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Run Prediction
```bash
curl -X POST http://localhost:8000/api/apps/ml-predictor/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "dataset_id": 1,
    "problem_description": "Predict house prices based on features",
    "model": "gemini-3-flash-preview"
  }'
```

### Get Project Results
```bash
curl http://localhost:8000/api/apps/ml-predictor/projects/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Sample Datasets

1. **Iris Flower Classification**
   - 150 samples, 4 features
   - Predict: flower species (3 classes)

2. **Breast Cancer Classification**
   - 569 samples, 30 features
   - Predict: malignant or benign

3. **House Prices Regression**
   - 1460 samples, 5 features
   - Predict: house price

4. **Wine Quality Regression**
   - 1599 samples, 11 features
   - Predict: quality score (3-9)

5. **Titanic Survival Classification**
   - 891 samples, 6 features
   - Predict: survived (yes/no)

## Algorithms

### Classification (6)
- Decision Tree - Fast, interpretable
- Random Forest - Robust, handles non-linear
- Gradient Boosting - High accuracy
- SVM - Good for high-dimensional data
- Logistic Regression - Fast, interpretable
- KNN - Non-linear, local patterns

### Regression (5)
- Linear Regression - Simple, fast
- Ridge/Lasso - Regularized, feature selection
- SVR - Non-linear, handles outliers
- Random Forest Regressor - Complex patterns
- Gradient Boosting Regressor - High accuracy

## Metrics

### Classification
- **Accuracy** - Overall correctness
- **Precision** - True positives / predicted positives
- **Recall** - True positives / actual positives
- **F1 Score** - Harmonic mean of precision and recall

### Regression
- **RMSE** - Root mean squared error (lower is better)
- **MAE** - Mean absolute error (lower is better)
- **R²** - Coefficient of determination (higher is better)
- **MSE** - Mean squared error (lower is better)

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## Tech Stack

- **Backend**: FastAPI + LangGraph 1.0.1
- **ML**: scikit-learn
- **Data**: pandas, numpy
- **Database**: PostgreSQL
- **AI**: Gemini/Groq/Bedrock
- **Auth**: JWT

## Future Enhancements

- Time series algorithms
- Neural networks
- Hyperparameter tuning
- Cross-validation
- Model persistence
- Batch predictions
- Real-time monitoring
