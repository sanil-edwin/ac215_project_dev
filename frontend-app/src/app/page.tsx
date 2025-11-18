'use client'

import { useState, useEffect } from 'react'
import CountySelector from '@/components/CountySelector'
import MCSIDisplay from '@/components/MCSIDisplay'
import YieldPredictor from '@/components/YieldPredictor'
import HistoricalChart from '@/components/HistoricalChart'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

export default function Home() {
  const [selectedCounty, setSelectedCounty] = useState<string>('19153') // Polk County default
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 to-white">
      {/* Header */}
      <header className="bg-green-700 text-white py-6 shadow-lg">
        <div className="container mx-auto px-4">
          <h1 className="text-4xl font-bold">🌽 AgriGuard</h1>
          <p className="text-green-100 mt-2">Iowa Corn Stress Monitoring & Yield Prediction</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        
        {/* County Selector */}
        <div className="mb-8">
          <CountySelector 
            selectedCounty={selectedCounty}
            onSelectCounty={setSelectedCounty}
          />
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          
          {/* MCSI Card */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Current Stress Index</h2>
            <MCSIDisplay 
              countyFips={selectedCounty}
              apiUrl={API_URL}
            />
          </div>

          {/* Yield Prediction Card */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Yield Prediction</h2>
            <YieldPredictor 
              countyFips={selectedCounty}
              apiUrl={API_URL}
            />
          </div>
        </div>

        {/* Historical Chart */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-4 text-gray-800">Historical Stress Trend</h2>
          <HistoricalChart 
            countyFips={selectedCounty}
            apiUrl={API_URL}
          />
        </div>

        {/* Info Section */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h3 className="text-xl font-bold mb-3 text-blue-900">About MCSI</h3>
          <p className="text-gray-700 mb-2">
            The <strong>Multi-Factor Corn Stress Index (MCSI)</strong> combines satellite and weather data to assess corn crop stress:
          </p>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li><strong>Water Stress (45%)</strong>: Based on water deficit and precipitation</li>
            <li><strong>Heat Stress (35%)</strong>: Land surface temperature during critical periods</li>
            <li><strong>Vegetation Stress (20%)</strong>: NDVI-based crop health assessment</li>
          </ul>
          <div className="mt-4 grid grid-cols-4 gap-2 text-center">
            <div className="bg-green-100 p-2 rounded">
              <div className="font-bold text-green-700">Low</div>
              <div className="text-sm">0-30</div>
            </div>
            <div className="bg-yellow-100 p-2 rounded">
              <div className="font-bold text-yellow-700">Moderate</div>
              <div className="text-sm">30-50</div>
            </div>
            <div className="bg-orange-100 p-2 rounded">
              <div className="font-bold text-orange-700">High</div>
              <div className="text-sm">50-70</div>
            </div>
            <div className="bg-red-100 p-2 rounded">
              <div className="font-bold text-red-700">Severe</div>
              <div className="text-sm">70-100</div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-6 mt-12">
        <div className="container mx-auto px-4 text-center">
          <p>AgriGuard | AC215 Project | Harvard University</p>
          <p className="text-gray-400 text-sm mt-2">Data: USDA, NASA MODIS, gridMET</p>
        </div>
      </footer>
    </div>
  )
}
