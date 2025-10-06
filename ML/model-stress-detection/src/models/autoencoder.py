"""
Autoencoder for unsupervised stress detection
High reconstruction error indicates anomalous patterns (crop stress)
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
import numpy as np
from loguru import logger


class StressAutoencoder:
    """
    Autoencoder model for detecting crop stress anomalies
    
    Normal patterns: Low reconstruction error
    Stress patterns: High reconstruction error (anomaly)
    """
    
    def __init__(self, input_dim: int, latent_dim: int = 8, 
                 hidden_layers: list = [32, 16], dropout_rate: float = 0.2):
        """
        Initialize autoencoder
        
        Args:
            input_dim: Number of input features
            latent_dim: Dimension of latent (compressed) representation
            hidden_layers: List of hidden layer sizes
            dropout_rate: Dropout rate for regularization
        """
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.hidden_layers = hidden_layers
        self.dropout_rate = dropout_rate
        
        self.model = self._build_model()
        
        logger.info(f"Built autoencoder: {input_dim} -> {latent_dim} -> {input_dim}")
    
    def _build_model(self) -> Model:
        """Build the autoencoder architecture"""
        
        # Input
        input_layer = layers.Input(shape=(self.input_dim,), name='input')
        
        # Encoder
        x = input_layer
        for i, units in enumerate(self.hidden_layers):
            x = layers.Dense(units, activation='relu', name=f'encoder_{i}')(x)
            x = layers.BatchNormalization(name=f'encoder_bn_{i}')(x)
            x = layers.Dropout(self.dropout_rate, name=f'encoder_dropout_{i}')(x)
        
        # Latent representation
        latent = layers.Dense(self.latent_dim, activation='relu', name='latent')(x)
        
        # Decoder (mirror of encoder)
        x = latent
        for i, units in enumerate(reversed(self.hidden_layers)):
            x = layers.Dense(units, activation='relu', name=f'decoder_{i}')(x)
            x = layers.BatchNormalization(name=f'decoder_bn_{i}')(x)
            x = layers.Dropout(self.dropout_rate, name=f'decoder_dropout_{i}')(x)
        
        # Output (reconstruction)
        output = layers.Dense(self.input_dim, activation='linear', name='output')(x)
        
        # Build model
        model = Model(inputs=input_layer, outputs=output, name='stress_autoencoder')
        
        return model
    
    def compile(self, learning_rate: float = 0.001):
        """Compile the model"""
        
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        logger.info(f"Compiled model with lr={learning_rate}")
    
    def train(self, X_train: np.ndarray, X_val: np.ndarray, 
              epochs: int = 100, batch_size: int = 32, 
              early_stopping_patience: int = 15) -> dict:
        """
        Train the autoencoder
        
        Args:
            X_train: Training data
            X_val: Validation data
            epochs: Number of epochs
            batch_size: Batch size
            early_stopping_patience: Early stopping patience
            
        Returns:
            Training history
        """
        
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=early_stopping_patience,
                restore_best_weights=True,
                verbose=1
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1
            )
        ]
        
        logger.info(f"Training autoencoder...")
        logger.info(f"  Train samples: {len(X_train)}")
        logger.info(f"  Val samples: {len(X_val)}")
        logger.info(f"  Epochs: {epochs}")
        logger.info(f"  Batch size: {batch_size}")
        
        history = self.model.fit(
            X_train, X_train,  # Autoencoder: input = output
            validation_data=(X_val, X_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        return history.history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Get reconstructions
        
        Args:
            X: Input data
            
        Returns:
            Reconstructed data
        """
        return self.model.predict(X, verbose=0)
    
    def compute_reconstruction_error(self, X: np.ndarray) -> np.ndarray:
        """
        Compute reconstruction error (MSE per sample)
        
        Args:
            X: Input data
            
        Returns:
            Reconstruction error per sample
        """
        reconstructions = self.predict(X)
        errors = np.mean(np.square(X - reconstructions), axis=1)
        return errors
    
    def detect_anomalies(self, X: np.ndarray, threshold: float) -> tuple:
        """
        Detect anomalies based on reconstruction error
        
        Args:
            X: Input data
            threshold: Anomaly threshold
            
        Returns:
            (anomaly_scores, is_anomaly)
        """
        errors = self.compute_reconstruction_error(X)
        is_anomaly = errors > threshold
        
        return errors, is_anomaly
    
    def save(self, filepath: str):
        """Save the model"""
        self.model.save(filepath)
        logger.info(f"Saved model to: {filepath}")
    
    def load(self, filepath: str):
        """Load the model"""
        self.model = keras.models.load_model(filepath)
        logger.info(f"Loaded model from: {filepath}")
    
    def summary(self):
        """Print model summary"""
        return self.model.summary()


def calculate_threshold(errors: np.ndarray, percentile: float = 95) -> float:
    """
    Calculate anomaly threshold based on percentile
    
    Args:
        errors: Reconstruction errors
        percentile: Percentile for threshold (default: 95 = top 5% are anomalies)
        
    Returns:
        Threshold value
    """
    threshold = np.percentile(errors, percentile)
    return threshold
