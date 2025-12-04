"""
Multi-Factor Corn Stress Index (MCSI) API Service

Calculates weekly corn stress indicators from satellite and weather data:
- Water Stress Index (WSI)
- Heat Stress Index (HSI)
- Vegetation Health Index (VHI)
- Composite Corn Stress Index (CCSI)

Data source: Clean weekly aggregates from GCS
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgriGuard MCSI Service",
    description="Multi-Factor Corn Stress Index API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Data Models ====================

class StressLevel(str, Enum):
    HEALTHY = "healthy"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class SubIndex(BaseModel):
    """Individual stress component"""
    name: str
    value: float  # 0-100 scale
    status: StressLevel
    key_driver: str
    description: str


class MCSIResponse(BaseModel):
    """Weekly MCSI calculation response"""
    fips: str
    county_name: str
    week_start: str
    week_end: str
    week_of_season: int
    
    # Composite index
    overall_stress_index: float  # 0-100
    overall_status: StressLevel
    
    # Sub-indices
    water_stress_index: SubIndex
    heat_stress_index: SubIndex
    vegetation_health_index: SubIndex
    atmospheric_stress_index: SubIndex
    
    # Key drivers (ranked)
    primary_driver: str
    secondary_driver: str
    
    # Historical context
    historical_percentile: Optional[float]  # How does this week compare to history?
    anomaly: Optional[float]  # Standard deviations from normal
    
    # Raw indicators (for transparency)
    indicators: Dict[str, float]
    
    # Recommendations
    farm_recommendations: List[str]


class CountyWeeklyData(BaseModel):
    """County data for a specific week"""
    fips: str
    county_name: str
    week_start: str
    week_end: str
    mcsi: MCSIResponse


# ==================== MCSI Calculator ====================

class MCSICalculator:
    """
    Calculates Multi-Factor Corn Stress Index
    
    Aggregates multiple indicators into meaningful stress components:
    - Water Stress: Based on water_deficit, precipitation, ET
    - Heat Stress: Based on LST, VPD during critical periods
    - Vegetation Health: Based on NDVI
    - Atmospheric Stress: Based on VPD, ETo (demand indicators)
    """
    
    def __init__(self):
        """Initialize calculator with thresholds"""
        self.data = None
        self.climatology = None
        self._load_data()
    
    def _load_data(self):
        """Load clean weekly data and climatology from GCS"""
        try:
            logger.info("Loading weekly clean data from GCS...")
            self.data = pd.read_parquet(
                'gs://agriguard-ac215-data/data_clean/weekly/iowa_corn_weekly_20160501_20251031.parquet'
            )
            
            logger.info("Loading climatology baseline...")
            try:
                self.climatology = pd.read_parquet(
                    'gs://agriguard-ac215-data/data_clean/climatology/daily_normals_2016_2024.parquet'
                )
                self.climatology['date'] = pd.to_datetime(self.climatology['date'])
            except Exception as e:
                logger.warning(f"Climatology not available: {e}. Proceeding without it.")
                self.climatology = None
            
            # Ensure date columns are datetime
            self.data['week_start'] = pd.to_datetime(self.data['week_start'])
            
            logger.info(f"Loaded {len(self.data)} weekly records")
            logger.info(f"Data date range: {self.data['week_start'].min()} to {self.data['week_start'].max()}")
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise
    
    def get_latest_week(self) -> tuple:
        """Get the most recent week in the dataset"""
        if self.data is None or len(self.data) == 0:
            raise ValueError("No data loaded")
        
        latest_date = self.data['week_start'].max()
        week_mask = (self.data['week_start'] >= latest_date - timedelta(days=6)) & \
                    (self.data['week_start'] <= latest_date)
        week_data = self.data[week_mask].groupby(['fips', 'county_name', 'week_of_season']).first().reset_index()
        
        return week_data, latest_date
    
    def calculate_water_stress_index(self, row: pd.Series) -> tuple:
        """
        Calculate Water Stress Index (WSI) 0-100
        
        Based on:
        - water_deficit (primary): Higher deficit = more stress
        - precipitation: Lower precip = more stress
        - ET: High ET without precip = stress
        
        Returns: (index_value, status, key_driver)
        """
        wsi_components = []
        weights = {}
        
        # Component 1: Water Deficit (40% weight)
        # Deficit > 4 mm/day = severe stress for corn
        if 'water_deficit_mean' in row and pd.notna(row['water_deficit_mean']):
            deficit = row['water_deficit_mean']
            # Map: 0 deficit = 0 stress, 6+ = 100 stress (sigmoid-like)
            deficit_stress = min(100, max(0, (deficit / 6.0) * 100))
            wsi_components.append(deficit_stress)
            weights['water_deficit'] = 0.40
        
        # Component 2: Precipitation (35% weight)
        # During growing season, <2 mm/day for multiple days = stress
        if 'pr_sum' in row and pd.notna(row['pr_sum']):
            precip = row['pr_sum'] / 7.0  # Convert weekly sum to daily average
            # Map: >4 mm/day = 0 stress, 0 mm/day = 100 stress
            precip_stress = min(100, max(0, (1 - precip / 4.0) * 100))
            wsi_components.append(precip_stress)
            weights['precipitation'] = 0.35
        
        # Component 3: ET (25% weight)
        # High ET without rain = atmospheric demand for water
        if 'eto_sum' in row and pd.notna(row['eto_sum']):
            et = row['eto_sum']  # Weekly sum in mm
            et_daily = et / 7.0  # Convert to daily
            # High ET (>6 mm/day) = water demand
            et_stress = min(100, max(0, (et_daily / 8.0) * 100))
            wsi_components.append(et_stress)
            weights['et'] = 0.25
        
        # Calculate weighted average
        if wsi_components and weights:
            total_weight = sum(weights.values())
            normalized_weights = {k: v / total_weight for k, v in weights.items()}
            wsi = sum(c * list(normalized_weights.values())[i] 
                     for i, c in enumerate(wsi_components))
        else:
            wsi = 0
        
        # Determine status
        status = self._get_stress_status(wsi)
        
        # Key driver (which component is highest?)
        if 'deficit_stress' in locals() and deficit_stress > 60:
            key_driver = "High water deficit"
        elif 'precip_stress' in locals() and precip_stress > 60:
            key_driver = "Low precipitation"
        else:
            key_driver = "Moderate water stress across indicators"
        
        return wsi, status, key_driver
    
    def calculate_heat_stress_index(self, row: pd.Series) -> tuple:
        """
        Calculate Heat Stress Index (HSI) 0-100
        
        Based on:
        - LST (Land Surface Temperature): >35°C = stress, especially during pollination
        - VPD (Vapor Pressure Deficit): High VPD = high evaporative demand
        
        Returns: (index_value, status, key_driver)
        """
        hsi_components = []
        weights = {}
        
        # Component 1: Land Surface Temperature (60% weight)
        # Optimal: 25-30°C, Stress threshold: >35°C
        if 'lst_day_1km_mean' in row and pd.notna(row['lst_day_1km_mean']):
            lst = row['lst_day_1km_mean']
            
            # Piecewise function
            if lst < 25:
                lst_stress = (25 - lst) * 2  # Cold stress (less critical)
            elif lst <= 32:
                lst_stress = 0  # Optimal range
            elif lst <= 38:
                lst_stress = (lst - 32) * 15  # Heat stress ramp
            else:
                lst_stress = min(100, 90 + (lst - 38) * 5)  # Critical
            
            hsi_components.append(min(100, lst_stress))
            weights['lst'] = 0.60
        
        # Component 2: Vapor Pressure Deficit (40% weight)
        # High VPD = low humidity = high evaporative stress
        if 'vpd_mean' in row and pd.notna(row['vpd_mean']):
            vpd = row['vpd_mean']
            # Typical range: 0-3 kPa, >2.5 = stress
            vpd_stress = min(100, max(0, (vpd / 3.0) * 100))
            hsi_components.append(vpd_stress)
            weights['vpd'] = 0.40
        
        # Calculate weighted average
        if hsi_components and weights:
            total_weight = sum(weights.values())
            normalized_weights = {k: v / total_weight for k, v in weights.items()}
            hsi = sum(c * list(normalized_weights.values())[i] 
                     for i, c in enumerate(hsi_components))
        else:
            hsi = 0
        
        status = self._get_stress_status(hsi)
        
        # Key driver
        if 'lst_stress' in locals() and lst_stress > 50:
            key_driver = f"High temperature ({lst:.1f}°C)"
        elif 'vpd_stress' in locals() and vpd_stress > 50:
            key_driver = "High atmospheric dryness"
        else:
            key_driver = "Moderate heat stress"
        
        return hsi, status, key_driver
    
    def calculate_vegetation_health_index(self, row: pd.Series) -> tuple:
        """
        Calculate Vegetation Health Index (VHI) 0-100
        
        Based on:
        - NDVI: Normalized Difference Vegetation Index
        - Higher NDVI = healthier vegetation
        
        Returns: (index_value, status, key_driver)
        """
        if 'ndvi_mean' not in row or pd.isna(row['ndvi_mean']):
            return 0, StressLevel.HEALTHY, "No NDVI data"
        
        ndvi = row['ndvi_mean']
        
        # NDVI interpretation
        # <0.3 = severe stress, 0.3-0.5 = moderate stress, 0.5-0.7 = mild, >0.7 = healthy
        # Convert to stress (inverse)
        if ndvi < 0.3:
            vhi = 100  # Severe stress
        elif ndvi < 0.5:
            vhi = 70 - (ndvi - 0.3) / 0.2 * 25  # Moderate
        elif ndvi < 0.7:
            vhi = 30 - (ndvi - 0.5) / 0.2 * 20  # Mild
        else:
            vhi = max(0, 10 - (ndvi - 0.7) / 0.23 * 10)  # Healthy
        
        vhi = min(100, max(0, vhi))
        status = self._get_stress_status(vhi)
        
        key_driver = f"NDVI {ndvi:.3f} (vegetation vigor)"
        
        return vhi, status, key_driver
    
    def calculate_atmospheric_stress_index(self, row: pd.Series) -> tuple:
        """
        Calculate Atmospheric Stress Index (ASI) 0-100
        
        Based on:
        - VPD: Vapor Pressure Deficit (atmospheric dryness)
        - ETo: Reference Evapotranspiration (water demand)
        
        Returns: (index_value, status, key_driver)
        """
        asi_components = []
        weights = {}
        
        # Component 1: VPD (50% weight)
        if 'vpd_mean' in row and pd.notna(row['vpd_mean']):
            vpd = row['vpd_mean']
            vpd_stress = min(100, max(0, (vpd / 3.0) * 100))
            asi_components.append(vpd_stress)
            weights['vpd'] = 0.50
        
        # Component 2: ETo (50% weight)
        # High ETo = high water demand
        if 'eto_mean' in row and pd.notna(row['eto_mean']):
            eto = row['eto_mean']
            # Typical peak: 6-8 mm/day, >8 = atmospheric stress
            eto_stress = min(100, max(0, (eto / 10.0) * 100))
            asi_components.append(eto_stress)
            weights['eto'] = 0.50
        
        if asi_components and weights:
            total_weight = sum(weights.values())
            normalized_weights = {k: v / total_weight for k, v in weights.items()}
            asi = sum(c * list(normalized_weights.values())[i] 
                     for i, c in enumerate(asi_components))
        else:
            asi = 0
        
        status = self._get_stress_status(asi)
        key_driver = "Atmospheric evaporative demand"
        
        return asi, status, key_driver
    
    def calculate_composite_stress_index(self, wsi: float, hsi: float, 
                                         vhi: float, asi: float) -> float:
        """
        Calculate overall Composite Corn Stress Index (CCSI)
        
        Weights:
        - Water Stress (40%): Most critical for corn yield
        - Heat Stress (30%): Especially during pollination
        - Vegetation Health (20%): Reflects overall plant condition
        - Atmospheric Stress (10%): Supporting factor
        """
        ccsi = (wsi * 0.40) + (hsi * 0.30) + (vhi * 0.20) + (asi * 0.10)
        return min(100, max(0, ccsi))
    
    def _get_stress_status(self, index: float) -> StressLevel:
        """Convert 0-100 index to stress level"""
        if index < 20:
            return StressLevel.HEALTHY
        elif index < 40:
            return StressLevel.MILD
        elif index < 60:
            return StressLevel.MODERATE
        elif index < 80:
            return StressLevel.SEVERE
        else:
            return StressLevel.CRITICAL
    
    def get_farm_recommendations(self, ccsi: float, wsi: float, hsi: float, 
                                 vhi: float, row: pd.Series) -> List[str]:
        """Generate actionable recommendations based on stress indices"""
        recommendations = []
        
        # Water stress recommendations
        if wsi > 70:
            recommendations.append("🚨 CRITICAL: Implement emergency irrigation if available")
            recommendations.append("Consider harvesting early if grain fill advanced")
        elif wsi > 50:
            recommendations.append("⚠️  Monitor soil moisture closely - irrigation recommended")
            recommendations.append("Apply water management practices")
        
        # Heat stress recommendations
        if hsi > 70 and 'week_of_season' in row:
            week = row.get('week_of_season', 0)
            if 8 <= week <= 10:  # Pollination period (roughly mid-July to early Aug)
                recommendations.append("🌡️  CRITICAL PERIOD: High heat during pollination - monitor pollen viability")
        elif hsi > 50:
            recommendations.append("⚠️  High temperatures - ensure adequate water availability")
        
        # Vegetation health recommendations
        if vhi > 60:
            recommendations.append("Investigate vegetation stress - check for pests/disease")
            recommendations.append("Consider nutrient status evaluation")
        elif vhi > 40:
            recommendations.append("Monitor for signs of pest or disease pressure")
        
        # Combined recommendations
        if ccsi > 70:
            recommendations.append("⚠️  HIGH OVERALL STRESS: Consider crop insurance claim documentation")
        
        if not recommendations:
            recommendations.append("✅ Conditions are favorable - continue standard management")
        
        return recommendations
    
    def calculate_week_mcsi(self, fips: str, week_start: str, 
                           week_end: Optional[str] = None) -> MCSIResponse:
        """
        Calculate MCSI for a specific county and week
        
        Args:
            fips: 5-digit county FIPS code
            week_start: Start date (YYYY-MM-DD)
            week_end: End date (optional, defaults to 6 days after start)
        """
        try:
            week_start_date = pd.to_datetime(week_start)
            if week_end:
                week_end_date = pd.to_datetime(week_end)
            else:
                week_end_date = week_start_date + timedelta(days=6)
            
            # Get data for this week and county
            mask = (self.data['fips'] == fips) & \
                   (self.data['week_start'] >= week_start_date) & \
                   (self.data['week_start'] <= week_end_date)
            
            week_data = self.data[mask]
            
            if len(week_data) == 0:
                raise ValueError(f"No data found for county {fips} in week {week_start}")
            
            # Use the first record (should be representative for the week)
            row = week_data.iloc[0]
            
            # Calculate sub-indices
            wsi, wsi_status, wsi_driver = self.calculate_water_stress_index(row)
            hsi, hsi_status, hsi_driver = self.calculate_heat_stress_index(row)
            vhi, vhi_status, vhi_driver = self.calculate_vegetation_health_index(row)
            asi, asi_status, asi_driver = self.calculate_atmospheric_stress_index(row)
            
            # Calculate composite index
            ccsi = self.calculate_composite_stress_index(wsi, hsi, vhi, asi)
            ccsi_status = self._get_stress_status(ccsi)
            
            # Determine primary and secondary drivers
            drivers = [
                ("Water stress", wsi),
                ("Heat stress", hsi),
                ("Low vegetation health", vhi),
                ("Atmospheric stress", asi),
            ]
            drivers.sort(key=lambda x: x[1], reverse=True)
            primary_driver = drivers[0][0]
            secondary_driver = drivers[1][0] if len(drivers) > 1 else "None"
            
            # Get raw indicators for transparency
            indicators = {
                'water_deficit_mean': float(row.get('water_deficit_mean', 0)),
                'precipitation_mean': float(row.get('pr_mean', 0)),
                'et_mean': float(row.get('et_ensemble_mad_mean', 0)),
                'lst_mean': float(row.get('lst_day_1km_mean', 0)),
                'vpd_mean': float(row.get('vpd_mean', 0)),
                'eto_mean': float(row.get('eto_mean', 0)),
                'ndvi_mean': float(row.get('ndvi_mean', 0)),
            }
            
            # Generate recommendations
            recommendations = self.get_farm_recommendations(ccsi, wsi, hsi, vhi, row)
            
            # Build response
            return MCSIResponse(
                fips=fips,
                county_name=row.get('county_name', 'Unknown'),
                week_start=week_start_date.strftime('%Y-%m-%d'),
                week_end=week_end_date.strftime('%Y-%m-%d'),
                week_of_season=int(row.get('week_of_season', 0)),
                
                overall_stress_index=round(ccsi, 2),
                overall_status=ccsi_status,
                
                water_stress_index=SubIndex(
                    name="Water Stress Index",
                    value=round(wsi, 2),
                    status=wsi_status,
                    key_driver=wsi_driver,
                    description="Combination of water deficit, precipitation, and ET"
                ),
                heat_stress_index=SubIndex(
                    name="Heat Stress Index",
                    value=round(hsi, 2),
                    status=hsi_status,
                    key_driver=hsi_driver,
                    description="Based on land surface temperature and atmospheric dryness"
                ),
                vegetation_health_index=SubIndex(
                    name="Vegetation Health Index",
                    value=round(vhi, 2),
                    status=vhi_status,
                    key_driver=vhi_driver,
                    description="Normalized Difference Vegetation Index (NDVI)"
                ),
                atmospheric_stress_index=SubIndex(
                    name="Atmospheric Stress Index",
                    value=round(asi, 2),
                    status=asi_status,
                    key_driver=asi_driver,
                    description="Evaporative demand and atmospheric conditions"
                ),
                
                primary_driver=primary_driver,
                secondary_driver=secondary_driver,
                
                historical_percentile=None,  # TODO: Calculate from climatology
                anomaly=None,  # TODO: Calculate from climatology
                
                indicators=indicators,
                farm_recommendations=recommendations,
            )
        
        except Exception as e:
            logger.error(f"Error calculating MCSI: {e}")
            raise


# ==================== API Endpoints ====================

calculator = MCSICalculator()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MCSI API",
        "data_loaded": calculator.data is not None
    }


@app.get("/mcsi/latest", response_model=List[MCSIResponse])
async def get_latest_mcsi():
    """
    Get MCSI for all counties for the latest week
    """
    try:
        week_data, latest_date = calculator.get_latest_week()
        
        results = []
        for _, row in week_data.iterrows():
            fips = row['fips']
            week_start = (latest_date - timedelta(days=6)).strftime('%Y-%m-%d')
            
            mcsi = calculator.calculate_week_mcsi(fips, week_start)
            results.append(mcsi)
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting latest MCSI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcsi/county/{fips}", response_model=MCSIResponse)
async def get_county_mcsi(
    fips: str,
    date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD). Defaults to latest.")
):
    """
    Get MCSI for a specific county and week
    
    Args:
        fips: 5-digit county FIPS code (e.g., "19001" for Adair County)
        date: Start date of week (YYYY-MM-DD). If omitted, returns latest week.
    
    Example:
        GET /mcsi/county/19001?date=2025-10-20
    """
    try:
        if not date:
            _, latest_date = calculator.get_latest_week()
            date = (latest_date - timedelta(days=6)).strftime('%Y-%m-%d')
        
        mcsi = calculator.calculate_week_mcsi(fips, date)
        return mcsi
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating MCSI for {fips}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcsi/county/{fips}/timeseries", response_model=List[MCSIResponse])
async def get_county_timeseries(
    fips: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Maximum weeks to return")
):
    """
    Get MCSI timeseries for a county across multiple weeks
    
    Example:
        GET /mcsi/county/19001/timeseries?start_date=2025-08-01&end_date=2025-10-31&limit=50
    """
    try:
        if calculator.data is not None:
            county_data = calculator.data[calculator.data['fips'] == fips]
        
        if start_date:
            start = pd.to_datetime(start_date)
            county_data = county_data[county_data['week_start'] >= start]
        
        if end_date:
            end = pd.to_datetime(end_date)
            county_data = county_data[county_data['week_start'] <= end]
        
        county_data = county_data.sort_values('week_start').tail(limit)
        
        results = []
        for _, row in county_data.iterrows():
            date_str = row['week_start'].strftime('%Y-%m-%d')
            try:
                mcsi = calculator.calculate_week_mcsi(fips, date_str)
                results.append(mcsi)
            except Exception as e:
                logger.warning(f"Skipping {fips} on {date_str}: {e}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting timeseries for {fips}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcsi/summary")
async def get_mcsi_summary(
    date: Optional[str] = Query(None, description="Week start date (YYYY-MM-DD)")
):
    """
    Get summary statistics across all Iowa counties for a week
    
    Returns stress distribution, top stressed counties, etc.
    """
    try:
        if not date:
            _, latest_date = calculator.get_latest_week()
            date = (latest_date - timedelta(days=6)).strftime('%Y-%m-%d')
        
        week_data, _ = calculator.get_latest_week()
        
        mcsi_values = []
        for _, row in week_data.iterrows():
            try:
                mcsi = calculator.calculate_week_mcsi(row['fips'], date)
                mcsi_values.append(mcsi)
            except:
                pass
        
        if not mcsi_values:
            raise ValueError("No data for requested week")
        
        # Calculate statistics
        stress_indices = [m.overall_stress_index for m in mcsi_values]
        
        return {
            "week_date": date,
            "counties_analyzed": len(mcsi_values),
            "average_stress_index": round(np.mean(stress_indices), 2),
            "max_stress_index": round(np.max(stress_indices), 2),
            "min_stress_index": round(np.min(stress_indices), 2),
            "std_stress_index": round(np.std(stress_indices), 2),
            "critical_counties": [
                {
                    "fips": m.fips,
                    "county_name": m.county_name,
                    "stress_index": m.overall_stress_index,
                    "status": m.overall_status
                }
                for m in sorted(mcsi_values, key=lambda x: x.overall_stress_index, reverse=True)[:5]
            ],
            "healthy_counties": [
                {
                    "fips": m.fips,
                    "county_name": m.county_name,
                    "stress_index": m.overall_stress_index,
                    "status": m.overall_status
                }
                for m in sorted(mcsi_values, key=lambda x: x.overall_stress_index)[:5]
            ]
        }
    
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/indicators")
async def get_indicators():
    """Get documentation on all indicators and their interpretation"""
    return {
        "water_stress_index": {
            "range": "0-100",
            "description": "Measures water availability and atmospheric demand",
            "components": {
                "water_deficit": "ETo - Precipitation (40% weight)",
                "precipitation": "Daily rainfall (35% weight)",
                "evapotranspiration": "Atmospheric water demand (25% weight)"
            },
            "thresholds": {
                "0-20": "Healthy - adequate water",
                "20-40": "Mild stress - monitor",
                "40-60": "Moderate stress - irrigation recommended",
                "60-80": "Severe stress - take action",
                "80-100": "Critical - emergency measures"
            }
        },
        "heat_stress_index": {
            "range": "0-100",
            "description": "Measures temperature and atmospheric dryness stress",
            "components": {
                "land_surface_temperature": "Daytime temperature (60% weight, °C)",
                "vapor_pressure_deficit": "Atmospheric dryness (40% weight, kPa)"
            },
            "critical_period": "July 15 - Aug 15 (Pollination)",
            "temperature_thresholds": {
                "25-30": "Optimal",
                "30-35": "Mild stress",
                "35-38": "Severe stress",
                ">38": "Critical - pollen sterility risk"
            }
        },
        "vegetation_health_index": {
            "range": "0-100",
            "description": "Measures plant vigor and health (inverted NDVI)",
            "data_source": "NDVI (MOD13A1)",
            "ndvi_interpretation": {
                "<0.3": "Severe stress - low vigor",
                "0.3-0.5": "Moderate stress",
                "0.5-0.7": "Mild stress",
                ">0.7": "Healthy vegetation"
            }
        },
        "atmospheric_stress_index": {
            "range": "0-100",
            "description": "Measures atmospheric evaporative demand",
            "components": {
                "vapor_pressure_deficit": "Atmospheric dryness (50% weight)",
                "reference_evapotranspiration": "Water demand (50% weight)"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
