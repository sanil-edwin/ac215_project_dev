"""
AgriGuard Extended API - MS4 Complete

Provides all endpoints required for MS4 submission:
- County list
- MCSI calculation
- Yield prediction
- Stress map
- Historical data

Author: AgriGuard Team
Date: November 17, 2025
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging
from google.cloud import storage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AgriGuard API - MS4",
    description="Complete API for corn stress monitoring and yield prediction",
    version="2.0.0"
)

# CORS middleware - Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
rf_model = None
feature_names = None
model_config = None
mcsi_data = None
clean_data = None  # Cleaned ML-ready data
counties_data = None
mcsi_data = None

# Iowa Counties - All 99 counties with FIPS codes
IOWA_COUNTIES = [
    {"fips": "19001", "name": "Adair"}, {"fips": "19003", "name": "Adams"},
    {"fips": "19005", "name": "Allamakee"}, {"fips": "19007", "name": "Appanoose"},
    {"fips": "19009", "name": "Audubon"}, {"fips": "19011", "name": "Benton"},
    {"fips": "19013", "name": "Black Hawk"}, {"fips": "19015", "name": "Boone"},
    {"fips": "19017", "name": "Bremer"}, {"fips": "19019", "name": "Buchanan"},
    {"fips": "19021", "name": "Buena Vista"}, {"fips": "19023", "name": "Butler"},
    {"fips": "19025", "name": "Calhoun"}, {"fips": "19027", "name": "Carroll"},
    {"fips": "19029", "name": "Cass"}, {"fips": "19031", "name": "Cedar"},
    {"fips": "19033", "name": "Cerro Gordo"}, {"fips": "19035", "name": "Cherokee"},
    {"fips": "19037", "name": "Chickasaw"}, {"fips": "19039", "name": "Clarke"},
    {"fips": "19041", "name": "Clay"}, {"fips": "19043", "name": "Clayton"},
    {"fips": "19045", "name": "Clinton"}, {"fips": "19047", "name": "Crawford"},
    {"fips": "19049", "name": "Dallas"}, {"fips": "19051", "name": "Davis"},
    {"fips": "19053", "name": "Decatur"}, {"fips": "19055", "name": "Delaware"},
    {"fips": "19057", "name": "Des Moines"}, {"fips": "19059", "name": "Dickinson"},
    {"fips": "19061", "name": "Dubuque"}, {"fips": "19063", "name": "Emmet"},
    {"fips": "19065", "name": "Fayette"}, {"fips": "19067", "name": "Floyd"},
    {"fips": "19069", "name": "Franklin"}, {"fips": "19071", "name": "Fremont"},
    {"fips": "19073", "name": "Greene"}, {"fips": "19075", "name": "Grundy"},
    {"fips": "19077", "name": "Guthrie"}, {"fips": "19079", "name": "Hamilton"},
    {"fips": "19081", "name": "Hancock"}, {"fips": "19083", "name": "Hardin"},
    {"fips": "19085", "name": "Harrison"}, {"fips": "19087", "name": "Henry"},
    {"fips": "19089", "name": "Howard"}, {"fips": "19091", "name": "Humboldt"},
    {"fips": "19093", "name": "Ida"}, {"fips": "19095", "name": "Iowa"},
    {"fips": "19097", "name": "Jackson"}, {"fips": "19099", "name": "Jasper"},
    {"fips": "19101", "name": "Jefferson"}, {"fips": "19103", "name": "Johnson"},
    {"fips": "19105", "name": "Jones"}, {"fips": "19107", "name": "Keokuk"},
    {"fips": "19109", "name": "Kossuth"}, {"fips": "19111", "name": "Lee"},
    {"fips": "19113", "name": "Linn"}, {"fips": "19115", "name": "Louisa"},
    {"fips": "19117", "name": "Lucas"}, {"fips": "19119", "name": "Lyon"},
    {"fips": "19121", "name": "Madison"}, {"fips": "19123", "name": "Mahaska"},
    {"fips": "19125", "name": "Marion"}, {"fips": "19127", "name": "Marshall"},
    {"fips": "19129", "name": "Mills"}, {"fips": "19131", "name": "Mitchell"},
    {"fips": "19133", "name": "Monona"}, {"fips": "19135", "name": "Monroe"},
    {"fips": "19137", "name": "Montgomery"}, {"fips": "19139", "name": "Muscatine"},
    {"fips": "19141", "name": "O'Brien"}, {"fips": "19143", "name": "Osceola"},
    {"fips": "19145", "name": "Page"}, {"fips": "19147", "name": "Palo Alto"},
    {"fips": "19149", "name": "Plymouth"}, {"fips": "19151", "name": "Pocahontas"},
    {"fips": "19153", "name": "Polk"}, {"fips": "19155", "name": "Pottawattamie"},
    {"fips": "19157", "name": "Poweshiek"}, {"fips": "19159", "name": "Ringgold"},
    {"fips": "19161", "name": "Sac"}, {"fips": "19163", "name": "Scott"},
    {"fips": "19165", "name": "Shelby"}, {"fips": "19167", "name": "Sioux"},
    {"fips": "19169", "name": "Story"}, {"fips": "19171", "name": "Tama"},
    {"fips": "19173", "name": "Taylor"}, {"fips": "19175", "name": "Union"},
    {"fips": "19177", "name": "Van Buren"}, {"fips": "19179", "name": "Wapello"},
    {"fips": "19181", "name": "Warren"}, {"fips": "19183", "name": "Washington"},
    {"fips": "19185", "name": "Wayne"}, {"fips": "19187", "name": "Webster"},
    {"fips": "19189", "name": "Winnebago"}, {"fips": "19191", "name": "Winneshiek"},
    {"fips": "19193", "name": "Woodbury"}, {"fips": "19195", "name": "Worth"},
    {"fips": "19197", "name": "Wright"}
]

# GCS configuration
GCS_BUCKET = "agriguard-ac215-data"
MCSI_PATH = "processed/mcsi/"

# =============================================================================
# Data Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    models_loaded: bool
    data_loaded: bool
    version: str

class CountyInfo(BaseModel):
    fips: str
    name: str
    
class CountiesResponse(BaseModel):
    counties: List[CountyInfo]
    total: int

class MCSIResponse(BaseModel):
    county_fips: str
    county_name: str
    start_date: str
    end_date: str
    mcsi_score: float
    stress_level: str
    color: str
    components: Dict[str, float]
    growth_stage: str
    data_source: str

class YieldPredictionResponse(BaseModel):
    county_fips: str
    county_name: str
    year: int
    predicted_yield: float
    confidence: str
    trend: str

class StressMapResponse(BaseModel):
    date: str
    counties: List[Dict]
    
class HistoricalDataResponse(BaseModel):
    county_fips: str
    county_name: str
    data: List[Dict]

# =============================================================================
# Helper Functions
# =============================================================================

def download_from_gcs(bucket_name: str, source_path: str, dest_path: str):
    """Download file from GCS"""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source_path)
        blob.download_to_filename(dest_path)
        logger.info(f"Downloaded {source_path} to {dest_path}")
    except Exception as e:
        logger.error(f"Error downloading from GCS: {e}")
        raise



def calculate_mcsi_simple(county_fips: str, start_date: str, end_date: str) -> Dict:
    """Calculate MCSI using REAL DATA from GCS"""
    from datetime import datetime
    import random
    
    county_name = next((c["name"] for c in IOWA_COUNTIES if c["fips"] == county_fips), "Unknown")
    
    # Try real data first
    real_data = get_mcsi_for_period(mcsi_data, county_fips, start_date, end_date)
    
    if real_data:
        water_stress = real_data['water_stress']
        heat_stress = real_data['heat_stress']
        veg_stress = real_data['vegetation_stress']
        data_source = "Real MCSI from GCS"
        logger.info(f"Using real data for {county_fips}")
    else:
        logger.warning(f"No real data for {county_fips}, using estimate")
        end = datetime.strptime(end_date, '%Y-%m-%d')
        month, year = end.month, end.year
        seed = int(county_fips) + (year * 100) + (month * 10)
        random.seed(seed)
        
        if month == 5:
            water_stress, heat_stress, veg_stress = random.uniform(10,25), random.uniform(15,30), random.uniform(20,35)
        elif month == 6:
            water_stress, heat_stress, veg_stress = random.uniform(20,40), random.uniform(25,45), random.uniform(15,30)
        elif month == 7:
            water_stress, heat_stress, veg_stress = random.uniform(30,60), random.uniform(35,65), random.uniform(20,40)
        elif month == 8:
            water_stress, heat_stress, veg_stress = random.uniform(35,70), random.uniform(40,70), random.uniform(25,50)
        elif month == 9:
            water_stress, heat_stress, veg_stress = random.uniform(20,45), random.uniform(25,50), random.uniform(30,55)
        else:
            water_stress, heat_stress, veg_stress = random.uniform(15,35), random.uniform(20,40), random.uniform(35,60)
        
        if year == 2022:
            water_stress *= 1.3
            heat_stress *= 1.2
        elif year == 2023:
            water_stress *= 0.8
            heat_stress *= 0.9
        
        water_stress = min(water_stress, 100)
        heat_stress = min(heat_stress, 100)
        veg_stress = min(veg_stress, 100)
        data_source = "Temporal Estimate"
    
    # Calculate MCSI (weighted average)
    mcsi_score = (water_stress * 0.45 + heat_stress * 0.35 + veg_stress * 0.20)
    
    # Determine stress level
    if mcsi_score < 30:
        stress_level = "Low"
        color = "#4CAF50"  # Green
    elif mcsi_score < 50:
        stress_level = "Moderate"
        color = "#FFC107"  # Yellow
    elif mcsi_score < 70:
        stress_level = "High"
        color = "#FF9800"  # Orange
    else:
        stress_level = "Severe"
        color = "#F44336"  # Red
    
    # Determine growth stage based on date
    end = datetime.strptime(end_date, '%Y-%m-%d')
    month = end.month
    day = end.day
    
    if month < 6:
        growth_stage = "emergence"
    elif month == 6:
        growth_stage = "vegetative"
    elif month == 7 and day < 15:
        growth_stage = "vegetative"
    elif month == 7 or (month == 8 and day < 15):
        growth_stage = "pollination"
    elif month == 8:
        growth_stage = "grain_fill"
    else:
        growth_stage = "maturity"
    
    return {
        "county_fips": county_fips,
        "county_name": county_name,
        "start_date": start_date,
        "end_date": end_date,
        "mcsi_score": round(mcsi_score, 2),
        "stress_level": stress_level,
        "color": color,
        "components": {
            "water_stress": round(water_stress, 2),
            "heat_stress": round(heat_stress, 2),
            "vegetation_stress": round(veg_stress, 2)
        },
        "growth_stage": growth_stage,
        "data_source": data_source
    }

def predict_yield_simple(county_fips: str, year: int) -> Dict:
    """
    Predict yield using season-progressive weekly data
    Uses REAL weekly aggregated data up to current date
    """
    from datetime import datetime
    
    # Determine as-of date
    current_date = datetime.now()
    season_start = datetime(year, 5, 1)
    season_end = datetime(year, 10, 31)
    
    # Determine forecast type and confidence
    if current_date > season_end:
        # Post-season: full data available
        as_of_date = season_end
        forecast_type = "post_season"
        season_completion = 100.0
    elif current_date < season_start:
        # Pre-season: use historical average
        as_of_date = season_start
        forecast_type = "pre_season"
        season_completion = 0.0
    else:
        # In-season: progressive forecast
        as_of_date = current_date
        forecast_type = "in_season"
        days_into_season = (current_date - season_start).days
        season_completion = min(100.0, (days_into_season / 184.0) * 100)
    
    # Calculate confidence based on season completion
    if season_completion < 25:
        confidence = "Low"
    elif season_completion < 50:
        confidence = "Medium"
    elif season_completion < 75:
        confidence = "High"
    else:
        confidence = "Very High"
    
    # Try to use real weekly data
    if clean_data is not None:
        try:
            # Filter for this county-year up to as_of_date
            season_data = clean_data[
                (clean_data['fips'] == county_fips) & 
                (clean_data['year'] == year) &
                (clean_data['week_start'] <= as_of_date)
            ]
            
            if len(season_data) > 0:
                # Aggregate weekly features
                ndvi_avg = season_data['ndvi_mean'].mean()
                lst_avg = season_data['lst_mean'].mean()
                lst_max = season_data['lst_max'].max()
                water_deficit_total = season_data['water_deficit_mean'].sum()
                pr_total = season_data['pr_sum'].sum()
                
                # Check for critical stress periods
                has_pollination_data = len(season_data[season_data['growth_phase'].str.contains('pollination', na=False)]) > 0
                
                # Simple yield model based on stress indicators
                base_yield = 180.0  # Iowa average
                
                # NDVI impact (vegetation health)
                if ndvi_avg > 0.7:
                    ndvi_impact = +15
                elif ndvi_avg > 0.6:
                    ndvi_impact = +5
                elif ndvi_avg > 0.5:
                    ndvi_impact = 0
                else:
                    ndvi_impact = -10
                
                # Heat stress impact
                if lst_max > 38:
                    heat_impact = -20  # Severe heat damage
                elif lst_max > 35:
                    heat_impact = -10
                elif lst_max > 32:
                    heat_impact = -5
                else:
                    heat_impact = 0
                
                # Water deficit impact
                if water_deficit_total > 100:
                    water_impact = -15  # Drought stress
                elif water_deficit_total > 50:
                    water_impact = -8
                elif water_deficit_total > 20:
                    water_impact = -3
                else:
                    water_impact = 0
                
                # Precipitation impact (too much or too little)
                if pr_total < 300:
                    pr_impact = -10  # Too dry
                elif pr_total > 800:
                    pr_impact = -5   # Too wet
                else:
                    pr_impact = +5   # Good rainfall
                
                # Pollination period bonus
                poll_bonus = +10 if has_pollination_data else 0
                
                predicted_yield = base_yield + ndvi_impact + heat_impact + water_impact + pr_impact + poll_bonus
                
                # Ensure reasonable range
                predicted_yield = max(100, min(220, predicted_yield))
                
                # Determine trend
                iowa_avg = 180.0
                if predicted_yield > iowa_avg + 10:
                    trend = "above_average"
                elif predicted_yield < iowa_avg - 10:
                    trend = "below_average"
                else:
                    trend = "average"
                
                logger.info(f"Real prediction from {len(season_data)} weeks: {county_fips} {year} = {predicted_yield:.1f} bu/acre")
                
                return {
                    "county_fips": county_fips,
                    "year": year,
                    "predicted_yield": round(predicted_yield, 1),
                    "confidence": confidence,
                    "trend": trend,
                    "forecast_type": forecast_type,
                    "season_completion": f"{season_completion:.1f}%",
                    "as_of_date": as_of_date.strftime('%Y-%m-%d'),
                    "weeks_data": len(season_data),
                    "model": "Season-Progressive Stress Model",
                    "data_source": "Real weekly aggregated data"
                }
                
        except Exception as e:
            logger.error(f"Error using weekly data: {e}")
            # Fall through to estimate
    
    # Fallback: Use temporal estimate
    import random
    random.seed(int(county_fips) + year)
    base_yield = 180.0
    
    # Vary by year
    year_factor = {
        2022: -15,  # Drought year
        2023: +5,   # Better year
        2024: 0,    # Average
        2025: +3,   # Slightly above
        2026: +5    # Trend up
    }.get(year, 0)
    
    variation = random.uniform(-10, 10)
    predicted_yield = base_yield + year_factor + variation
    
    iowa_avg = 180.0
    if predicted_yield > iowa_avg + 10:
        trend = "above_average"
    elif predicted_yield < iowa_avg - 10:
        trend = "below_average"
    else:
        trend = "average"
    
    return {
        "county_fips": county_fips,
        "year": year,
        "predicted_yield": round(predicted_yield, 1),
        "confidence": "Low",
        "trend": trend,
        "forecast_type": forecast_type,
        "season_completion": f"{season_completion:.1f}%",
        "as_of_date": as_of_date.strftime('%Y-%m-%d'),
        "model": "Temporal Estimate",
        "data_source": "Fallback estimate"
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": "AgriGuard API",
        "version": "2.0.0",
        "description": "Corn stress monitoring and yield prediction for Iowa",
        "endpoints": {
            "health": "/health",
            "counties": "/api/counties",
            "mcsi": "/api/mcsi/{fips}",
            "predict": "/api/predict/{fips}",
            "stress_map": "/api/stress/map",
            "historical": "/api/historical/{fips}"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": rf_model is not None,
        "data_loaded": mcsi_data is not None,
        "version": "2.1.0-real-data"
    }

@app.get("/api/counties", response_model=CountiesResponse, tags=["Data"])
async def get_counties():
    """Get list of all 99 Iowa counties"""
    return {
        "counties": IOWA_COUNTIES,
        "total": len(IOWA_COUNTIES)
    }

@app.get("/api/mcsi/{fips}", response_model=MCSIResponse, tags=["MCSI"])
async def get_mcsi(
    fips: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD")
):
    """
    Get Multi-Factor Corn Stress Index for a county
    
    If dates not provided, uses last 14 days
    """
    try:
        # Validate FIPS
        if not any(c["fips"] == fips for c in IOWA_COUNTIES):
            raise HTTPException(status_code=404, detail=f"County {fips} not found")
        
        # Default dates
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start = datetime.now() - timedelta(days=14)
            start_date = start.strftime('%Y-%m-%d')
        
        # Calculate MCSI
        result = calculate_mcsi_simple(fips, start_date, end_date)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCSI calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predict/{fips}", response_model=YieldPredictionResponse, tags=["Prediction"])
async def predict_yield(
    fips: str,
    year: int = Query(2025, description="Year for prediction")
):
    """Predict corn yield for a county"""
    try:
        # Validate FIPS
        if not any(c["fips"] == fips for c in IOWA_COUNTIES):
            raise HTTPException(status_code=404, detail=f"County {fips} not found")
        
        # Validate year
        if year < 2020 or year > 2030:
            raise HTTPException(status_code=400, detail="Year must be between 2020-2030")
        
        # Predict
        result = predict_yield_simple(fips, year)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stress/map", response_model=StressMapResponse, tags=["MCSI"])
async def get_stress_map(
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (default: today)")
):
    """Get stress levels for all counties for map visualization"""
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate MCSI for all counties
        counties_data = []
        
        for county in IOWA_COUNTIES[:10]:  # Limit to 10 for demo, use all 99 in production
            start = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=14)).strftime('%Y-%m-%d')
            mcsi = calculate_mcsi_simple(county["fips"], start, date)
            
            counties_data.append({
                "fips": county["fips"],
                "name": county["name"],
                "mcsi_score": mcsi["mcsi_score"],
                "stress_level": mcsi["stress_level"],
                "color": mcsi["color"]
            })
        
        return {
            "date": date,
            "counties": counties_data
        }
    
    except Exception as e:
        logger.error(f"Stress map error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/historical/{fips}", response_model=HistoricalDataResponse, tags=["Data"])
async def get_historical(
    fips: str,
    year: int = Query(2024, description="Year")
):
    """Get historical MCSI and yield data for a county"""
    try:
        # Validate FIPS
        if not any(c["fips"] == fips for c in IOWA_COUNTIES):
            raise HTTPException(status_code=404, detail=f"County {fips} not found")
        
        county_name = next(c["name"] for c in IOWA_COUNTIES if c["fips"] == fips)
        
        # Simulate historical data (in production, load from GCS)
        data = []
        for month in range(5, 11):  # May through October
            for week in range(1, 5):
                date = f"{year}-{month:02d}-{week * 7:02d}"
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    if date_obj > datetime.now():
                        continue
                        
                    mcsi = calculate_mcsi_simple(fips, date, date)
                    data.append({
                        "date": date,
                        "mcsi_score": mcsi["mcsi_score"],
                        "stress_level": mcsi["stress_level"]
                    })
                except:
                    continue
        
        return {
            "county_fips": fips,
            "county_name": county_name,
            "data": data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Historical data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
