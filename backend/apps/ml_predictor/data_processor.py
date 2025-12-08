import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import json
import io
from services.file_service import extract_text_from_pdf, extract_text_from_docx, load_dataframe

class DataProcessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        self.target_name = None
    
    def load_dataset(self, file_path: str) -> pd.DataFrame:
        """Load dataset from file - uses central file service"""
        return load_dataframe(file_path)
    
    def load_data_from_text(self, text: str) -> pd.DataFrame:
        """Load data from raw text string (assuming CSV format)"""
        try:
            return pd.read_csv(io.StringIO(text))
        except:
            return pd.DataFrame({"raw_text": [text]})

    def analyze_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze dataset and return statistics"""
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "data_types": {col: str(df[col].dtype) for col in df.columns},
            "missing_values": df.isnull().sum().to_dict(),
            "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
            "shape": df.shape,
            "memory_usage": df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        }
    
    def detect_target_variable(self, df: pd.DataFrame, problem_description: str) -> str:
        """
        Detect target variable from dataset.
        Simple heuristic: look for common target names or use last column
        """
        common_targets = ['target', 'label', 'class', 'output', 'result', 'prediction', 'y']
        
        # Check for common target names
        for col in df.columns:
            if col.lower() in common_targets:
                return col
        
        # Check if problem description mentions a column
        for col in df.columns:
            if col.lower() in problem_description.lower():
                return col
        
        # Default to last column
        return df.columns[-1]
    
    def preprocess_data(self, df: pd.DataFrame, target_col: str = None) -> Tuple[pd.DataFrame, Any]:
        """
        Preprocess data: handle missing values, encode categorical variables
        """
        df = df.copy()
        
        # Separate features and target
        if target_col and target_col in df.columns:
            X = df.drop(columns=[target_col])
            y = df[target_col]
        else:
            X = df
            y = None
        
        # Handle missing values in features
        for col in X.columns:
            if X[col].isnull().sum() > 0:
                if X[col].dtype in [np.float64, np.int64]:
                    X[col].fillna(X[col].mean(), inplace=True)
                else:
                    X[col].fillna(X[col].mode()[0] if len(X[col].mode()) > 0 else 'unknown', inplace=True)
        
        # Handle missing values in target
        if y is not None and y.isnull().sum() > 0:
            if y.dtype in [np.float64, np.int64]:
                y.fillna(y.mean(), inplace=True)
            else:
                y.fillna(y.mode()[0] if len(y.mode()) > 0 else 'unknown', inplace=True)
        
        # Encode categorical variables in features
        for col in X.columns:
            if X[col].dtype == 'object':
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                self.label_encoders[col] = le
        
        # Encode target if categorical
        if y is not None and y.dtype == 'object':
            le = LabelEncoder()
            y = le.fit_transform(y.astype(str))
            self.label_encoders['target'] = le
        
        self.feature_names = X.columns.tolist()
        self.target_name = target_col
        
        return X, y
    
    def split_data(self, X: pd.DataFrame, y: pd.Series = None, test_size: float = 0.2, random_state: int = None) -> Tuple:
        """Split data into train and test sets"""
        from sklearn.model_selection import train_test_split
        
        if y is not None:
            return train_test_split(X, y, test_size=test_size, random_state=random_state or 42)
        return train_test_split(X, test_size=test_size, random_state=random_state or 42)
    
    def preprocess_features(self, df: pd.DataFrame) -> np.ndarray:
        """Preprocess features only (for prediction on new data)"""
        df = df.copy()
        
        # Handle missing values
        for col in df.columns:
            if df[col].isnull().sum() > 0:
                if df[col].dtype in [np.float64, np.int64]:
                    df[col].fillna(df[col].mean(), inplace=True)
                else:
                    df[col].fillna('unknown', inplace=True)
        
        # Encode categorical variables using stored encoders or create new
        for col in df.columns:
            if df[col].dtype == 'object':
                if col in self.label_encoders:
                    # Use existing encoder
                    le = self.label_encoders[col]
                    # Handle unseen labels
                    df[col] = df[col].apply(lambda x: x if x in le.classes_ else le.classes_[0])
                    df[col] = le.transform(df[col].astype(str))
                else:
                    # Create new encoder
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str))
        
        return df.values
        if y is None:
            # Unsupervised case: just split X
            X_train, X_test = train_test_split(
                X, test_size=test_size, random_state=random_state
            )
            y_train, y_test = None, None
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state
            )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def get_feature_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed feature information"""
        info = {}
        for col in df.columns:
            col_info = {
                "dtype": str(df[col].dtype),
                "missing": int(df[col].isnull().sum()),
                "unique": int(df[col].nunique())
            }
            
            if df[col].dtype in [np.float64, np.int64]:
                col_info.update({
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std())
                })
            
            info[col] = col_info
        
        return info
    
    def get_dataset_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive dataset summary"""
        analysis = self.analyze_dataset(df)
        return {
            "total_rows": analysis["rows"],
            "total_columns": analysis["columns"],
            "column_names": analysis["column_names"],
            "numeric_columns": analysis["numeric_columns"],
            "categorical_columns": analysis["categorical_columns"],
            "missing_values": analysis["missing_values"],
            "memory_usage_mb": round(analysis["memory_usage"], 2)
        }
