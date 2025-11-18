'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'

interface YieldData {
  county_fips: string
  county_name: string
  year: number
  predicted_yield: number
  confidence: string
  trend: string
}

interface Props {
  countyFips: string
  apiUrl: string
}

export default function YieldPredictor({ countyFips, apiUrl }: Props) {
  const [year, setYear] = useState(2025)
  const [data, setData] = useState<YieldData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPrediction()
  }, [countyFips])

  const fetchPrediction = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await axios.get(`${apiUrl}/api/predict/${countyFips}?year=${year}`)
      setData(response.data)
    } catch (err) {
      setError('Failed to load prediction')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleYearChange = (newYear: number) => {
    setYear(newYear)
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'above_average': return '↗️'
      case 'below_average': return '↘️'
      case 'average': return '→'
      default: return '→'
    }
  }

  const getTrendText = (trend: string) => {
    switch (trend) {
      case 'above_average': return 'Above Average'
      case 'below_average': return 'Below Average'
      case 'average': return 'Average'
      default: return 'Average'
    }
  }

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'above_average': return 'text-green-600'
      case 'below_average': return 'text-red-600'
      case 'average': return 'text-blue-600'
      default: return 'text-gray-600'
    }
  }

  return (
    <div className="space-y-4">
      {/* Year Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Year:
        </label>
        <div className="flex gap-2">
          {[2024, 2025, 2026].map((y) => (
            <button
              key={y}
              onClick={() => {
                handleYearChange(y)
                fetchPrediction()
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                year === y
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {y}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-700"></div>
        </div>
      )}

      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {data && !loading && (
        <div className="space-y-4">
          {/* Predicted Yield */}
          <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6 text-center">
            <div className="text-sm text-gray-600 mb-1">Predicted Yield</div>
            <div className="text-4xl font-bold text-green-700">
              {data.predicted_yield.toFixed(1)}
            </div>
            <div className="text-lg text-gray-600">bushels/acre</div>
          </div>

          {/* Trend */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="text-gray-600">Trend:</span>
            <span className={`font-semibold ${getTrendColor(data.trend)}`}>
              {getTrendIcon(data.trend)} {getTrendText(data.trend)}
            </span>
          </div>

          {/* Confidence */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="text-gray-600">Confidence:</span>
            <span className="font-semibold">
              {data.confidence === 'High' && '🟢'}
              {data.confidence === 'Medium' && '🟡'}
              {data.confidence === 'Low' && '🔴'}
              {' '}{data.confidence}
            </span>
          </div>

          {/* Context */}
          <div className="text-xs text-gray-500 p-3 bg-blue-50 rounded-lg">
            <p className="font-semibold mb-1">Note:</p>
            <p>Iowa average: ~180 bu/acre. Predictions based on satellite data, weather patterns, and historical yields.</p>
          </div>
        </div>
      )}
    </div>
  )
}
