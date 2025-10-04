#!/usr/bin/env python3
"""
Train stress detection model (unsupervised autoencoder)
Detects crop stress by identifying anomalous patterns
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import click
from loguru import logger
import yaml
from sklearn.preprocessing import StandardScaler
import joblib
import json

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logging_utils import setup_logging
from src.models.autoencoder import StressAutoencoder, calculate_threshold


class StressModelTrainer:
    """Train unsupervised stress detection model"""
    
    def __init__(self, config_path: str = "configs/model_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        np.random.seed(self.config['random_seed'])
        
        logger.info("StressModelTrainer initialized")
    
    def load_data(self) -> tuple:
        """Load stress features from Container 2"""
        
        input_dir = self.config['data']['input_dir']
        
        logger.info(f"Loading data from: {input_dir}")
        
        train = pd.read_parquet(f"{input_dir}/train.parquet")
        val = pd.read_parquet(f"{input_dir}/val.parquet")
        test = pd.read_parquet(f"{input_dir}/test.parquet")
        
        logger.info(f"Train: {len(train)} samples")
        logger.info(f"Val: {len(val)} samples")
        logger.info(f"Test: {len(test)} samples")
        
        return train, val, test
    
    def prepare_features(self, train: pd.DataFrame, val: pd.DataFrame, 
                        test: pd.DataFrame) -> tuple:
        """Prepare features for training"""
        
        # Remove metadata columns
        feature_cols = [col for col in train.columns if col not in ['county', 'year']]
        
        logger.info(f"Using {len(feature_cols)} features:")
        for col in feature_cols:
            logger.info(f"  - {col}")
        
        X_train = train[feature_cols].values
        X_val = val[feature_cols].values
        X_test = test[feature_cols].values
        
        # Standardize features
        logger.info("Standardizing features...")
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        X_test_scaled = scaler.transform(X_test)
        
        return X_train_scaled, X_val_scaled, X_test_scaled, scaler, feature_cols
    
    def train_autoencoder(self, X_train: np.ndarray, X_val: np.ndarray) -> StressAutoencoder:
        """Train the autoencoder model"""
        
        model_config = self.config['model']
        training_config = self.config['training']
        
        # Build model
        model = StressAutoencoder(
            input_dim=X_train.shape[1],
            latent_dim=model_config['latent_dim'],
            hidden_layers=model_config['hidden_layers'],
            dropout_rate=model_config['dropout_rate']
        )
        
        # Show architecture
        logger.info("\nModel architecture:")
        model.summary()
        
        # Compile
        model.compile(learning_rate=training_config['learning_rate'])
        
        # Train
        history = model.train(
            X_train, X_val,
            epochs=training_config['epochs'],
            batch_size=training_config['batch_size'],
            early_stopping_patience=training_config['early_stopping_patience']
        )
        
        return model, history
    
    def evaluate_model(self, model: StressAutoencoder, X_train: np.ndarray, 
                      X_val: np.ndarray, X_test: np.ndarray) -> dict:
        """Evaluate the model and determine anomaly threshold"""
        
        logger.info("\nEvaluating model...")
        
        # Compute reconstruction errors
        train_errors = model.compute_reconstruction_error(X_train)
        val_errors = model.compute_reconstruction_error(X_val)
        test_errors = model.compute_reconstruction_error(X_test)
        
        # Calculate threshold from training data
        threshold = calculate_threshold(
            train_errors, 
            self.config['anomaly_detection']['threshold_percentile']
        )
        
        logger.info(f"Anomaly threshold: {threshold:.6f}")
        
        # Detect anomalies
        _, train_anomalies = model.detect_anomalies(X_train, threshold)
        _, val_anomalies = model.detect_anomalies(X_val, threshold)
        _, test_anomalies = model.detect_anomalies(X_test, threshold)
        
        # Statistics
        metrics = {
            'threshold': float(threshold),
            'train': {
                'mean_error': float(np.mean(train_errors)),
                'std_error': float(np.std(train_errors)),
                'anomaly_rate': float(np.mean(train_anomalies)),
                'anomaly_count': int(np.sum(train_anomalies))
            },
            'val': {
                'mean_error': float(np.mean(val_errors)),
                'std_error': float(np.std(val_errors)),
                'anomaly_rate': float(np.mean(val_anomalies)),
                'anomaly_count': int(np.sum(val_anomalies))
            },
            'test': {
                'mean_error': float(np.mean(test_errors)),
                'std_error': float(np.std(test_errors)),
                'anomaly_rate': float(np.mean(test_anomalies)),
                'anomaly_count': int(np.sum(test_anomalies))
            }
        }
        
        logger.info("\nPerformance metrics:")
        logger.info(f"Train - Mean error: {metrics['train']['mean_error']:.6f}, Anomalies: {metrics['train']['anomaly_count']}/{len(train_errors)} ({metrics['train']['anomaly_rate']*100:.1f}%)")
        logger.info(f"Val   - Mean error: {metrics['val']['mean_error']:.6f}, Anomalies: {metrics['val']['anomaly_count']}/{len(val_errors)} ({metrics['val']['anomaly_rate']*100:.1f}%)")
        logger.info(f"Test  - Mean error: {metrics['test']['mean_error']:.6f}, Anomalies: {metrics['test']['anomaly_count']}/{len(test_errors)} ({metrics['test']['anomaly_rate']*100:.1f}%)")
        
        return metrics
    
    def save_model(self, model: StressAutoencoder, scaler: StandardScaler, 
                   threshold: float, feature_cols: list, metrics: dict):
        """Save trained model and artifacts"""
        
        output_dir = self.config['data']['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        
        # Save model
        model.save(f"{output_dir}/autoencoder_model.keras")
        
        # Save scaler
        joblib.dump(scaler, f"{output_dir}/scaler.pkl")
        logger.info(f"Saved scaler to: {output_dir}/scaler.pkl")
        
        # Save threshold
        np.save(f"{output_dir}/threshold.npy", threshold)
        logger.info(f"Saved threshold to: {output_dir}/threshold.npy")
        
        # Save metadata
        metadata = {
            'model_type': 'autoencoder',
            'input_dim': len(feature_cols),
            'latent_dim': self.config['model']['latent_dim'],
            'features': feature_cols,
            'threshold': threshold,
            'metrics': metrics
        }
        
        with open(f"{output_dir}/model_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.success(f"Saved all artifacts to: {output_dir}")


@click.command()
@click.option('--config', default='configs/model_config.yaml', help='Config file')
@click.option('--verbose', is_flag=True, help='Verbose logging')
def main(config, verbose):
    """Train stress detection model (unsupervised)"""
    
    setup_logging(verbose=verbose)
    
    logger.info("="*70)
    logger.info("AgriGuard Stress Detection - Container 3")
    logger.info("Model: Unsupervised Autoencoder")
    logger.info("="*70)
    
    trainer = StressModelTrainer(config_path=config)
    
    # Load data
    train, val, test = trainer.load_data()
    
    # Prepare features
    X_train, X_val, X_test, scaler, feature_cols = trainer.prepare_features(train, val, test)
    
    # Train model
    model, history = trainer.train_autoencoder(X_train, X_val)
    
    # Evaluate
    metrics = trainer.evaluate_model(model, X_train, X_val, X_test)
    
    # Save
    trainer.save_model(model, scaler, metrics['threshold'], feature_cols, metrics)
    
    logger.info("\n" + "="*70)
    logger.info("TRAINING COMPLETE")
    logger.info("="*70)
    logger.success("Model ready for inference!")


if __name__ == "__main__":
    main()
