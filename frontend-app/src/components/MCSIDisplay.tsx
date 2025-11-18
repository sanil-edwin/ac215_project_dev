'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'

interface MCSIData {
  county_fips: string
  county_name: string
  mcsi_score: number
  stress_level: string
  color: string
  components: {
    water_stress: number
    heat_stress: number
    vegetation_stress: number
  }
  growth_stage: string
  start_date: string
  end_date: string
}

interface Props {
  countyFips: string
  apiUrl: string
}

export default function MCSIDisplay({ countyFips, apiUrl }: Props) {
  const [data, setData] = useState<MCSIData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMonth, setSelectedMonth] = useState('08')
  const [selectedYear, setSelectedYear] = useState('2024')

  useEffect(() => {
    fetchMCSI()
  }, [countyFips, apiUrl, selectedMonth, selectedYear])

  const fetchMCSI = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const startDate = `${selectedYear}-${selectedMonth}-01`
      const lastDay = new Date(parseInt(selectedYear), parseInt(selectedMonth), 0).getDate()
      const endDate = `${selectedYear}-${selectedMonth}-${lastDay}`
      
      const response = await axios.get(
        `${apiUrl}/api/mcsi/${countyFips}?start_date=${startDate}&end_date=${endDate}`
      )
      setData(response.data)
    } catch (err) {
      setError('Failed to load MCSI data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700"></div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error || 'No data available'}
      </div>
    )
  }

  const getStressColor = (level: string) => {
    switch (level) {
      case 'Low': return 'bg-green-500'
      case 'Moderate': return 'bg-yellow-500'
      case 'High': return 'bg-orange-500'
      case 'Severe': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const getTextColor = (level: string) => {
    switch (level) {
      case 'Low': return 'text-green-700'
      case 'Moderate': return 'text-yellow-700'
      case 'High': return 'text-orange-700'
      case 'Severe': return 'text-red-700'
      default: return 'text-gray-700'
    }
  }

  const months = [
    { value: '05', label: 'May' },
    { value: '06', label: 'June' },
    { value: '07', label: 'July' },
    { value: '08', label: 'August' },
    { value: '09', label: 'September' },
    { value: '10', label: 'October' },
  ]

  const years = ['2025', '2024', '2023', '2022']

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 rounded-lg p-3">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Month & Year:
        </label>
        <div className="flex gap-2">
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="flex-1 p-2 border-2 border-gray-300 rounded-lg focus:border-green-500 focus:outline-none"
          >
            {months.map((month) => (
              <option key={month.value} value={month.value}>
                {month.label}
              </option>
            ))}
          </select>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            className="flex-1 p-2 border-2 border-gray-300 rounded-lg focus:border-green-500 focus:outline-none"
          >
            {years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="text-center">
        <div className="inline-flex items-center justify-center">
          <div className={`${getStressColor(data.stress_level)} rounded-full p-8`}>
            <div className="text-5xl font-bold text-white">
              {data.mcsi_score.toFixed(1)}
            </div>
          </div>
        </div>
        <div className={`text-2xl font-bold mt-3 ${getTextColor(data.stress_level)}`}>
          {data.stress_level} Stress
        </div>
        <div className="text-sm text-gray-500 mt-1 capitalize">
          Growth Stage: {data.growth_stage.replace('_', ' ')}
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="font-semibold text-gray-700 text-sm uppercase">Stress Components:</h3>
        
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Water Stress (45%)</span>
            <span className="font-semibold">{data.components.water_stress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full"
              style={{ width: `${Math.min(data.components.water_stress, 100)}%` }}
            ></div>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Heat Stress (35%)</span>
            <span className="font-semibold">{data.components.heat_stress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-red-600 h-2 rounded-full"
              style={{ width: `${Math.min(data.components.heat_stress, 100)}%` }}
            ></div>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Vegetation Stress (20%)</span>
            <span className="font-semibold">{data.components.vegetation_stress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-green-600 h-2 rounded-full"
              style={{ width: `${Math.min(data.components.vegetation_stress, 100)}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="text-xs text-gray-500 text-center pt-2 border-t">
        Data from {new Date(data.start_date).toLocaleDateString()} to {new Date(data.end_date).toLocaleDateString()}
      </div>
    </div>
  )
}
