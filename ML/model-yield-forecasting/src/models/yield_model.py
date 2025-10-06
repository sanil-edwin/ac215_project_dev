"""XGBoost model for yield forecasting"""

import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from loguru import logger


class YieldForecaster:
    def __init__(self, params: dict = None):
        self.params = params or {}
        self.model = None
        self.feature_names = None
        logger.info("YieldForecaster initialized")
    
    def train(self, X_train, y_train, X_val, y_val, feature_names=None, early_stopping_rounds=20):
        self.feature_names = feature_names
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_names)
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_names)
        evals = [(dtrain, 'train'), (dval, 'val')]
        
        logger.info("Training XGBoost model...")
        logger.info(f"  Train samples: {len(X_train)}")
        logger.info(f"  Val samples: {len(X_val)}")
        
        evals_result = {}
        self.model = xgb.train(
            self.params, dtrain,
            num_boost_round=self.params.get('n_estimators', 200),
            evals=evals,
            early_stopping_rounds=early_stopping_rounds,
            evals_result=evals_result,
            verbose_eval=10
        )
        logger.success(f"Training complete! Best iteration: {self.model.best_iteration}")
        return evals_result
    
    def predict(self, X):
        dtest = xgb.DMatrix(X, feature_names=self.feature_names)
        return self.model.predict(dtest)
    
    def evaluate(self, X, y_true, dataset_name="Test"):
        y_pred = self.predict(X)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        
        metrics = {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'mape': float(mape),
            'mean_actual': float(np.mean(y_true)),
            'mean_predicted': float(np.mean(y_pred))
        }
        
        logger.info(f"\n{dataset_name} Performance:")
        logger.info(f"  RMSE: {rmse:.2f} bu/acre")
        logger.info(f"  MAE:  {mae:.2f} bu/acre")
        logger.info(f"  R2:   {r2:.4f}")
        logger.info(f"  MAPE: {mape:.2f}%")
        
        return metrics
    
    def get_feature_importance(self, importance_type='gain'):
        importance = self.model.get_score(importance_type=importance_type)
        df = pd.DataFrame([
            {'feature': k, 'importance': v}
            for k, v in importance.items()
        ])
        return df.sort_values('importance', ascending=False)
    
    def save(self, filepath):
        self.model.save_model(filepath)
        logger.info(f"Saved model to: {filepath}")


def create_predictions_dataframe(y_true, y_pred, counties, years):
    return pd.DataFrame({
        'county': counties,
        'year': years,
        'actual_yield': y_true,
        'predicted_yield': y_pred,
        'error': y_pred - y_true,
        'abs_error': np.abs(y_pred - y_true),
        'pct_error': ((y_pred - y_true) / y_true) * 100
    })