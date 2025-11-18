'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface HistoricalPoint {
  date: string
  mcsi_score: number
  stress_level: string
}

interface Props {
  countyFips: string
  apiUrl: string
}

export default function HistoricalChart({ countyFips, apiUrl }: Props) {
  const [data, setData] = useState<HistoricalPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [year, setYear] = useState(2024)

  useEffect(() => {
    const fetchHistorical = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const response = await axios.get(`${apiUrl}/api/historical/${countyFips}?year=${year}`)
        setData(response.data.data)
      } catch (err) {
        setError('Failed to load historical data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    if (countyFips) {
      fetchHistorical()
    }
  }, [countyFips, year, apiUrl])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700"></div>
      </div>
    )
  }

  if (error || !data || data.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-700">
        {error || 'No historical data available'}
      </div>
    )
  }

  // Format data for chart
  const chartData = data.map(point => ({
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    score: point.mcsi_score,
  }))

  return (
    <div className="space-y-4">
      {/* Year Selector */}
      <div className="flex gap-2 justify-end">
        {[2022, 2023, 2024, 2025].map((y) => (
          <button
            key={y}
            onClick={() => setYear(y)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              year === y
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {y}
          </button>
        ))}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            label={{ value: 'MCSI Score', angle: -90, position: 'insideLeft' }}
            domain={[0, 100]}
          />
          <Tooltip />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="score" 
            stroke="#2E7D32" 
            strokeWidth={2}
            name="MCSI Score"
            dot={{ fill: '#2E7D32', r: 4 }}
          />
          {/* Reference lines for stress levels */}
          <Line 
            type="monotone" 
            dataKey={() => 30} 
            stroke="#FFC107" 
            strokeDasharray="5 5"
            strokeWidth={1}
            name="Moderate Threshold"
            dot={false}
          />
          <Line 
            type="monotone" 
            dataKey={() => 50} 
            stroke="#FF9800" 
            strokeDasharray="5 5"
            strokeWidth={1}
            name="High Threshold"
            dot={false}
          />
          <Line 
            type="monotone" 
            dataKey={() => 70} 
            stroke="#F44336" 
            strokeDasharray="5 5"
            strokeWidth={1}
            name="Severe Threshold"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div className="flex items-center">
          <div className="w-3 h-3 bg-green-500 rounded mr-1"></div>
          <span>Low (0-30)</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-yellow-500 rounded mr-1"></div>
          <span>Moderate (30-50)</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-orange-500 rounded mr-1"></div>
          <span>High (50-70)</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-red-500 rounded mr-1"></div>
          <span>Severe (70+)</span>
        </div>
      </div>
    </div>
  )
}
