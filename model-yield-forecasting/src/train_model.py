"""Train yield forecasting model"""

import os, sys
from pathlib import Path
import pandas as pd
import numpy as np
import click
from loguru import logger
import yaml
from sklearn.preprocessing import StandardScaler
import joblib, json

sys.path.append(str(Path(__file__).parent.parent))
from src.utils.logging_utils import setup_logging
from src.models.yield_model import YieldForecaster, create_predictions_dataframe

class YieldModelTrainer:
    def __init__(self, config_path="configs/model_config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        np.random.seed(self.config['random_seed'])
    
    def load_data(self):
        d = self.config['data']['input_dir']
        logger.info(f"Loading from: {d}")
        train = pd.read_parquet(f"{d}/train.parquet")
        val = pd.read_parquet(f"{d}/val.parquet")
        test = pd.read_parquet(f"{d}/test.parquet")
        logger.info(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
        return train, val, test
    
    def prepare_features(self, train, val, test):
        cols = [c for c in train.columns if c not in ['county','year','yield_bu_per_acre']]
        X_train, y_train = train[cols].values, train['yield_bu_per_acre'].values
        X_val, y_val = val[cols].values, val['yield_bu_per_acre'].values
        X_test, y_test = test[cols].values, test['yield_bu_per_acre'].values
        
        scaler = StandardScaler()
        return (scaler.fit_transform(X_train), y_train, train[['county','year']],
                scaler.transform(X_val), y_val, val[['county','year']],
                scaler.transform(X_test), y_test, test[['county','year']],
                scaler, cols)
    
    def train_model(self, X_train, y_train, X_val, y_val, features):
        params = {**self.config['model'], 'objective':'reg:squarederror', 
                  'eval_metric':'rmse', 'seed':42}
        model = YieldForecaster(params)
        model.train(X_train, y_train, X_val, y_val, features, 20)
        return model
    
    def save_all(self, model, scaler, features, X_train, y_train, train_meta, 
                 X_val, y_val, val_meta, X_test, y_test, test_meta):
        out = self.config['data']['output_dir']
        os.makedirs(out, exist_ok=True)
        
        model.save(f"{out}/xgboost_model.json")
        joblib.dump(scaler, f"{out}/scaler.pkl")
        
        metrics = {
            'train': model.evaluate(X_train, y_train, "Train"),
            'val': model.evaluate(X_val, y_val, "Val"),
            'test': model.evaluate(X_test, y_test, "Test")
        }
        
        for name, X, y, meta in [('train',X_train,y_train,train_meta),
                                  ('val',X_val,y_val,val_meta),
                                  ('test',X_test,y_test,test_meta)]:
            pred = model.predict(X)
            df = create_predictions_dataframe(y, pred, meta['county'].values, meta['year'].values)
            df.to_csv(f"{out}/predictions_{name}.csv", index=False)
        
        model.get_feature_importance().to_csv(f"{out}/feature_importance.csv", index=False)
        
        with open(f"{out}/model_metadata.json", 'w') as f:
            json.dump({'features':features, 'metrics':metrics}, f, indent=2)
        
        logger.success(f"Saved to: {out}")
        return metrics

@click.command()
@click.option('--config', default='configs/model_config.yaml')
@click.option('--verbose', is_flag=True)
def main(config, verbose):
    setup_logging(verbose)
    logger.info("="*70)
    logger.info("Container 4: Yield Forecasting (XGBoost)")
    logger.info("="*70)
    
    t = YieldModelTrainer(config)
    train, val, test = t.load_data()
    X_tr, y_tr, m_tr, X_v, y_v, m_v, X_te, y_te, m_te, scaler, features = t.prepare_features(train, val, test)
    model = t.train_model(X_tr, y_tr, X_v, y_v, features)
    metrics = t.save_all(model, scaler, features, X_tr, y_tr, m_tr, X_v, y_v, m_v, X_te, y_te, m_te)
    
    logger.info("="*70)
    logger.info(f"Test RMSE: {metrics['test']['rmse']:.2f} bu/acre")
    logger.info(f"Test R2: {metrics['test']['r2']:.4f}")
    logger.success("COMPLETE!")

if __name__ == "__main__":
    main()