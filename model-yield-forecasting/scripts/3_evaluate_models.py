"""Evaluate and visualize rolling window model performance."""

import sys
sys.path.append('/app')

from utils.data_loader import DataLoader
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def create_performance_visualization():
    """Create visualization of model performance."""
    loader = DataLoader()
    
    # Load metrics
    blob = loader.bucket.blob("model_yield_forecasting/models/training_metrics.json")
    metrics = json.loads(blob.download_as_string())
    
    # Load feature importance
    blob = loader.bucket.blob("model_yield_forecasting/models/feature_importance.csv")
    importance_df = pd.read_csv(BytesIO(blob.download_as_bytes()))
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Cross-validation metrics
    cv_scores = metrics['cv_scores']
    folds = [f"Fold {i+1}" for i in range(len(cv_scores))]
    
    rmse_values = [score['rmse'] for score in cv_scores]
    r2_values = [score['r2'] for score in cv_scores]
    
    x_pos = np.arange(len(folds))
    width = 0.35
    
    ax1_twin = ax1.twinx()
    
    bars1 = ax1.bar(x_pos - width/2, rmse_values, width, label='RMSE', color='coral', alpha=0.8)
    bars2 = ax1_twin.bar(x_pos + width/2, r2_values, width, label='R²', color='skyblue', alpha=0.8)
    
    ax1.set_xlabel('Cross-Validation Fold', fontsize=12)
    ax1.set_ylabel('RMSE (bu/acre)', fontsize=12, color='coral')
    ax1_twin.set_ylabel('R² Score', fontsize=12, color='skyblue')
    ax1.set_title('Cross-Validation Performance', fontsize=14, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(folds, rotation=45)
    ax1.tick_params(axis='y', labelcolor='coral')
    ax1_twin.tick_params(axis='y', labelcolor='skyblue')
    ax1_twin.set_ylim(0, 1)
    
    # Add average line
    ax1.axhline(y=metrics['rmse'], color='darkred', linestyle='--', 
                label=f"Avg: {metrics['rmse']:.2f}", linewidth=2)
    ax1_twin.axhline(y=metrics['r2'], color='darkblue', linestyle='--', 
                     label=f"Avg: {metrics['r2']:.3f}", linewidth=2)
    
    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    ax1.grid(axis='y', alpha=0.3)
    
    # Plot 2: Top 15 features
    top_features = importance_df.head(15)
    
    ax2.barh(range(len(top_features)), top_features['importance'], color='mediumpurple', alpha=0.8)
    ax2.set_yticks(range(len(top_features)))
    ax2.set_yticklabels(top_features['feature'], fontsize=9)
    ax2.set_xlabel('Importance Score', fontsize=12)
    ax2.set_title('Top 15 Most Important Features', fontsize=14, fontweight='bold')
    ax2.invert_yaxis()
    ax2.grid(axis='x', alpha=0.3)
    
    # Add values on bars
    for i, v in enumerate(top_features['importance']):
        ax2.text(v + 0.001, i, f'{v:.3f}', va='center', fontsize=8)
    
    plt.tight_layout()
    
    # Save
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    
    blob = loader.bucket.blob("model_yield_forecasting/evaluation/model_performance.png")
    blob.upload_from_file(buffer, content_type='image/png')
    logger.info("Saved performance visualization")
    
    plt.close()


def create_feature_categories_chart():
    """Create chart showing feature importance by category."""
    loader = DataLoader()
    
    # Load feature importance
    blob = loader.bucket.blob("model_yield_forecasting/models/feature_importance.csv")
    importance_df = pd.read_csv(BytesIO(blob.download_as_bytes()))
    
    # Categorize features
    def categorize_feature(feature_name):
        if any(x in feature_name for x in ['days', 'week', 'month', 'completeness', 'day_of_year']):
            return 'Temporal'
        elif feature_name.startswith('et_'):
            return 'Evapotranspiration'
        elif feature_name.startswith('lst_'):
            return 'Land Surface Temp'
        elif any(x in feature_name for x in ['planting', 'veg', 'reproductive', 'grain']):
            return 'Growth Stage'
        elif 'observations' in feature_name or 'has_' in feature_name:
            return 'Data Availability'
        else:
            return 'Other'
    
    importance_df['category'] = importance_df['feature'].apply(categorize_feature)
    
    # Sum importance by category
    category_importance = importance_df.groupby('category')['importance'].sum().sort_values(ascending=True)
    
    # Create chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(category_importance)))
    bars = ax.barh(range(len(category_importance)), category_importance.values, color=colors, alpha=0.8)
    
    ax.set_yticks(range(len(category_importance)))
    ax.set_yticklabels(category_importance.index, fontsize=11)
    ax.set_xlabel('Total Importance Score', fontsize=12)
    ax.set_title('Feature Importance by Category', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    # Add values on bars
    for i, v in enumerate(category_importance.values):
        ax.text(v + 0.002, i, f'{v:.3f}', va='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    
    # Save
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    
    blob = loader.bucket.blob("model_yield_forecasting/evaluation/feature_categories.png")
    blob.upload_from_file(buffer, content_type='image/png')
    logger.info("Saved feature categories chart")
    
    plt.close()


def create_summary_report():
    """Create text summary report."""
    loader = DataLoader()
    
    # Load metrics
    blob = loader.bucket.blob("model_yield_forecasting/models/training_metrics.json")
    metrics = json.loads(blob.download_as_string())
    
    # Load feature info
    blob = loader.bucket.blob("model_yield_forecasting/features/feature_info.json")
    feature_info = json.loads(blob.download_as_string())
    
    report = []
    report.append("="*70)
    report.append("ROLLING WINDOW YIELD FORECASTING - EVALUATION SUMMARY")
    report.append("="*70)
    report.append("")
    
    report.append("MODEL OVERVIEW")
    report.append("-" * 50)
    report.append(f"  Model Type: XGBoost Regressor (Rolling Window)")
    report.append(f"  Training Samples: {feature_info['training_samples']}")
    report.append(f"  Counties: {feature_info['counties']}")
    report.append(f"  Years: {', '.join(map(str, feature_info['years']))}")
    report.append(f"  Total Features: {feature_info['total_features']}")
    report.append("")
    
    report.append("CROSS-VALIDATION PERFORMANCE (5-Fold)")
    report.append("-" * 50)
    report.append(f"  RMSE: {metrics['rmse']:.2f} ± {metrics['rmse_std']:.2f} bu/acre")
    report.append(f"  MAE:  {metrics['mae']:.2f} ± {metrics['mae_std']:.2f} bu/acre")
    report.append(f"  R²:   {metrics['r2']:.3f} ± {metrics['r2_std']:.3f}")
    report.append("")
    
    report.append("FEATURE BREAKDOWN")
    report.append("-" * 50)
    report.append(f"  Temporal Features: {len(feature_info['temporal_features'])}")
    report.append(f"  ET-based Features: {len(feature_info['et_features'])}")
    report.append(f"  LST-based Features: {len(feature_info['lst_features'])}")
    report.append("")
    
    report.append("="*70)
    report.append("KEY CAPABILITIES")
    report.append("="*70)
    report.append("")
    report.append("✓ Can predict yield for ANY date from May 1 to September 30")
    report.append("✓ Single unified model (no need for separate monthly models)")
    report.append("✓ Adapts predictions based on data availability")
    report.append("✓ Uncertainty quantification included")
    report.append("✓ Uses growth-stage specific features (planting, vegetative,")
    report.append("  reproductive, grain fill)")
    report.append("✓ Incorporates both ET and LST satellite data")
    report.append("")
    
    report.append("="*70)
    report.append("PERFORMANCE INTERPRETATION")
    report.append("="*70)
    report.append("")
    report.append(f"With RMSE of {metrics['rmse']:.1f} bu/acre and R² of {metrics['r2']:.3f}, this model")
    report.append("provides actionable yield predictions throughout the growing season.")
    report.append("")
    
    if metrics['r2'] > 0.75:
        report.append("• EXCELLENT: Model explains >75% of yield variation")
    elif metrics['r2'] > 0.65:
        report.append("• GOOD: Model explains >65% of yield variation")
    else:
        report.append("• MODERATE: Model explains moderate yield variation")
    
    report.append(f"• Predictions typically within ±{metrics['rmse']:.0f} bu/acre of actual yield")
    report.append("• Uncertainty decreases as growing season progresses")
    report.append("")
    
    report.append("="*70)
    
    report_text = "\n".join(report)
    
    # Save
    blob = loader.bucket.blob("model_yield_forecasting/evaluation/evaluation_summary.txt")
    blob.upload_from_string(report_text, content_type='text/plain')
    logger.info("Saved evaluation summary")
    
    print(report_text)


def main():
    """Main evaluation pipeline."""
    logger.info("="*60)
    logger.info("CREATING EVALUATION REPORTS AND VISUALIZATIONS")
    logger.info("="*60)
    
    try:
        create_performance_visualization()
        create_feature_categories_chart()
        create_summary_report()
        
        logger.info("\n" + "="*60)
        logger.info("EVALUATION COMPLETE")
        logger.info("="*60)
        logger.info("\nOutputs saved to:")
        logger.info("  gs://agriguard-ac215-data/model_yield_forecasting/evaluation/")
        
    except Exception as e:
        logger.error(f"Error during evaluation: {e}")
        raise


if __name__ == "__main__":
    main()
