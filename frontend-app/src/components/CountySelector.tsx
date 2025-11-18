'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'

interface County {
  fips: string
  name: string
}

interface Props {
  selectedCounty: string
  onSelectCounty: (fips: string) => void
}

export default function CountySelector({ selectedCounty, onSelectCounty }: Props) {
  const [counties, setCounties] = useState<County[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchCounties = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
        const response = await axios.get(`${API_URL}/api/counties`)
        setCounties(response.data.counties)
      } catch (error) {
        console.error('Error fetching counties:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchCounties()
  }, [])

  if (loading) {
    return <div className="text-gray-600">Loading counties...</div>
  }

  const currentCounty = counties.find(c => c.fips === selectedCounty)

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <label htmlFor="county-select" className="block text-lg font-semibold text-gray-700 mb-3">
        Select Iowa County:
      </label>
      <select
        id="county-select"
        value={selectedCounty}
        onChange={(e) => onSelectCounty(e.target.value)}
        className="w-full p-3 border-2 border-gray-300 rounded-lg text-lg focus:border-green-500 focus:outline-none"
      >
        {counties.map((county) => (
          <option key={county.fips} value={county.fips}>
            {county.name} County ({county.fips})
          </option>
        ))}
      </select>
      
      {currentCounty && (
        <div className="mt-4 p-4 bg-green-50 rounded-lg">
          <p className="text-sm text-gray-600">Currently viewing:</p>
          <p className="text-xl font-bold text-green-700">{currentCounty.name} County</p>
          <p className="text-sm text-gray-500">FIPS: {currentCounty.fips}</p>
        </div>
      )}
    </div>
  )
}
