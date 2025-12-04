#!/usr/bin/env python3
"""Test suite for XGBoost Yield Forecast Service"""

import requests
import json
import numpy as np

BASE_URL = "http://localhost:8001"

def test_health_check():
    print("\n✓ TEST 1: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['model_trained'] == True
    print(f"  Model: {data['model_type']}")
    print(f"  Status: {data['status']}")

def test_model_info():
    print("\n✓ TEST 2: Model Information")
    response = requests.get(f"{BASE_URL}/model/info")
    data = response.json()
    print(f"  Model: {data['model_type']}")
    print(f"  R² Score: {data['r2_score']:.3f}")
    print(f"  MAE: {data['mae_bu_acre']:.2f} bu/acre")
    print(f"  Hyperparameters: {data['hyperparameters']}")
    assert data['r2_score'] > 0.85

def test_quick_forecast():
    print("\n✓ TEST 3: Quick Forecast")
    response = requests.get(f"{BASE_URL}/forecast/county/19001?week=30&year=2025")
    data = response.json()
    print(f"  Forecast: {data['yield_forecast_bu_acre']:.1f} ± {data['forecast_uncertainty']:.1f} bu/acre")
    print(f"  Model: {data['model_type']}")
    assert 100 < data['yield_forecast_bu_acre'] < 200

def test_detailed_forecast():
    print("\n✓ TEST 4: Detailed Forecast with Feature Importance")
    
    mcsi_data = {
        str(w): {
            'water_stress_index': max(0, np.random.normal(20, 10)),
            'heat_stress_index': max(0, np.random.normal(15, 8)),
            'vegetation_health_index': max(20, min(80, np.random.normal(50, 10))),
            'atmospheric_stress_index': max(0, np.random.normal(20, 10)),
        }
        for w in range(22, 31)
    }
    
    response = requests.post(
        f"{BASE_URL}/forecast",
        json={
            'fips': '19003',
            'current_week': 30,
            'year': 2025,
            'mcsi_data': mcsi_data
        }
    )
    
    data = response.json()
    print(f"  Forecast: {data['yield_forecast_bu_acre']:.1f} bu/acre")
    print(f"  Confidence: [{data['confidence_interval_lower']:.1f}, {data['confidence_interval_upper']:.1f}]")
    print(f"  Primary driver: {data['primary_driver']}")
    print(f"  Feature importance (top 3):")
    for i, (feature, importance) in enumerate(list(data['feature_importance'].items())[:3]):
        print(f"    {i+1}. {feature}: {importance:.3f}")
    
    assert response.status_code == 200
    assert data['model_r2'] > 0.85

def test_batch_forecast():
    print("\n✓ TEST 5: Batch Forecast")
    
    counties = ["19001", "19003", "19005"]
    requests_list = []
    
    for fips in counties:
        mcsi = {str(w): {
            'water_stress_index': 20,
            'heat_stress_index': 15,
            'vegetation_health_index': 50,
            'atmospheric_stress_index': 20,
        } for w in range(22, 31)}
        requests_list.append({
            'fips': fips,
            'current_week': 30,
            'year': 2025,
            'mcsi_data': mcsi
        })
    
    response = requests.post(f"{BASE_URL}/forecast/batch", json=requests_list)
    results = response.json()
    
    print(f"  Forecasted {len(results)} counties")
    for r in results[:3]:
        if 'error' not in r:
            print(f"    {r['fips']}: {r['yield_forecast_bu_acre']:.1f} bu/acre")
    
    assert len(results) == len(counties)

def test_forecast_progression():
    print("\n✓ TEST 6: Forecast Progression (Uncertainty Shrinking)")
    
    fips = "19001"
    test_weeks = [22, 27, 30, 36, 40]
    
    print(f"  Week | Forecast     | Uncertainty")
    print(f"  -----|--------------|-------------")
    
    uncertainties = []
    for week in test_weeks:
        mcsi = {str(w): {
            'water_stress_index': 20,
            'heat_stress_index': 15,
            'vegetation_health_index': 50,
            'atmospheric_stress_index': 20,
        } for w in range(22, week + 1)}
        
        response = requests.post(
            f"{BASE_URL}/forecast",
            json={
                'fips': fips,
                'current_week': week,
                'year': 2025,
                'mcsi_data': mcsi
            }
        )
        
        data = response.json()
        unc = data['forecast_uncertainty']
        uncertainties.append(unc)
        
        print(f"  {week}   | {data['yield_forecast_bu_acre']:6.1f} ± {unc:4.1f}  | {unc:5.1f}")
    
    # Check uncertainty shrinks
    assert uncertainties == sorted(uncertainties, reverse=True), "Uncertainty should decrease"
    print(f"  ✓ Uncertainty shrinking correctly")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("XGBoost Yield Forecast Service - Test Suite")
    print("="*60)
    
    try:
        test_health_check()
        test_model_info()
        test_quick_forecast()
        test_detailed_forecast()
        test_batch_forecast()
        test_forecast_progression()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Could not connect to {BASE_URL}")
        print("Make sure the service is running: python yield_forecast_service.py")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
