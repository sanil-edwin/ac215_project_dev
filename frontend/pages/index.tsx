import { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AgriBot } from '../components/rag_client';

const IOWA_COUNTIES = [
  { code: '19001', name: 'Adair' },
  { code: '19003', name: 'Adams' },
  { code: '19005', name: 'Allamakee' },
  { code: '19007', name: 'Appanoose' },
  { code: '19009', name: 'Audubon' },
  { code: '19011', name: 'Benton' },
  { code: '19013', name: 'Black Hawk' },
  { code: '19015', name: 'Boone' },
  { code: '19017', name: 'Bremer' },
  { code: '19019', name: 'Buchanan' },
  { code: '19021', name: 'Buena Vista' },
  { code: '19023', name: 'Butler' },
  { code: '19025', name: 'Calhoun' },
  { code: '19027', name: 'Carroll' },
  { code: '19029', name: 'Cass' },
  { code: '19031', name: 'Cedar' },
  { code: '19033', name: 'Cerro Gordo' },
  { code: '19035', name: 'Cherokee' },
  { code: '19037', name: 'Chickasaw' },
  { code: '19039', name: 'Clarke' },
  { code: '19041', name: 'Clay' },
  { code: '19043', name: 'Clayton' },
  { code: '19045', name: 'Clinton' },
  { code: '19047', name: 'Crawford' },
  { code: '19049', name: 'Dallas' },
  { code: '19051', name: 'Davis' },
  { code: '19053', name: 'Decatur' },
  { code: '19055', name: 'Delaware' },
  { code: '19057', name: 'Des Moines' },
  { code: '19059', name: 'Dickinson' },
  { code: '19061', name: 'Dubuque' },
  { code: '19065', name: 'Emmet' },
  { code: '19067', name: 'Fayette' },
  { code: '19069', name: 'Floyd' },
  { code: '19071', name: 'Franklin' },
  { code: '19073', name: 'Fremont' },
  { code: '19075', name: 'Greene' },
  { code: '19077', name: 'Grundy' },
  { code: '19079', name: 'Guthrie' },
  { code: '19081', name: 'Hamilton' },
  { code: '19083', name: 'Hancock' },
  { code: '19085', name: 'Hardin' },
  { code: '19087', name: 'Harrison' },
  { code: '19089', name: 'Henry' },
  { code: '19091', name: 'Howard' },
  { code: '19093', name: 'Humboldt' },
  { code: '19095', name: 'Ida' },
  { code: '19097', name: 'Iowa' },
  { code: '19099', name: 'Jackson' },
  { code: '19101', name: 'Jasper' },
  { code: '19103', name: 'Jefferson' },
  { code: '19105', name: 'Johnson' },
  { code: '19107', name: 'Jones' },
  { code: '19109', name: 'Keokuk' },
  { code: '19111', name: 'Kossuth' },
  { code: '19113', name: 'Lee' },
  { code: '19115', name: 'Linn' },
  { code: '19117', name: 'Louisa' },
  { code: '19119', name: 'Lucas' },
  { code: '19121', name: 'Lyon' },
  { code: '19123', name: 'Madison' },
  { code: '19125', name: 'Mahaska' },
  { code: '19127', name: 'Marion' },
  { code: '19129', name: 'Marshall' },
  { code: '19131', name: 'Mills' },
  { code: '19133', name: 'Mitchell' },
  { code: '19135', name: 'Monona' },
  { code: '19137', name: 'Monroe' },
  { code: '19139', name: 'Montgomery' },
  { code: '19141', name: 'Muscatine' },
  { code: '19143', name: "O'Brien" },
  { code: '19145', name: 'Osceola' },
  { code: '19147', name: 'Page' },
  { code: '19149', name: 'Palo Alto' },
  { code: '19151', name: 'Plymouth' },
  { code: '19153', name: 'Pocahontas' },
  { code: '19155', name: 'Polk' },
  { code: '19157', name: 'Pottawattamie' },
  { code: '19159', name: 'Poweshiek' },
  { code: '19161', name: 'Ringgold' },
  { code: '19163', name: 'Sac' },
  { code: '19165', name: 'Scott' },
  { code: '19167', name: 'Shelby' },
  { code: '19169', name: 'Sioux' },
  { code: '19171', name: 'Story' },
  { code: '19173', name: 'Tama' },
  { code: '19175', name: 'Taylor' },
  { code: '19177', name: 'Union' },
  { code: '19179', name: 'Van Buren' },
  { code: '19181', name: 'Wapello' },
  { code: '19183', name: 'Warren' },
  { code: '19185', name: 'Washington' },
  { code: '19187', name: 'Wayne' },
  { code: '19189', name: 'Webster' },
  { code: '19191', name: 'Winnebago' },
  { code: '19193', name: 'Winneshiek' },
  { code: '19195', name: 'Woodbury' },
  { code: '19197', name: 'Worth' },
  { code: '19199', name: 'Wright' },
];

const WEEK_HINTS = {
  7: "V2-V3 (Early vegetative)",
  10: "V10 (Mid vegetative)",
  13: "R1 (Silking - Pollination start)",
  14: "R2 (Blister)",
  15: "R3 (Milk)",
  16: "R4 (Dough)",
  18: "R5 (Dent)",
  20: "R6 (Black layer)",
  22: "R7 (Maturity)",
  26: "R7 (Mature - Harvest ready)"
};

export default function Home() {
  const [county, setCounty] = useState('19001');
  const [selectedWeek, setSelectedWeek] = useState(18);
  const [timeseries, setTimeseries] = useState([]);
  const [allTimeseries, setAllTimeseries] = useState([]);
  const [currentData, setCurrentData] = useState(null);
  const [yield_, setYield] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (countyCode) => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/mcsi/county/${countyCode}/timeseries`);
      const data = await res.json();
      const fullData = Array.isArray(data) ? data : [data];
      setAllTimeseries(fullData);
      setTimeseries(fullData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(county);
  }, [county, fetchData]);

  useEffect(() => {
    const week = allTimeseries.find(item => item.week_of_season === selectedWeek);
    setCurrentData(week);
  }, [selectedWeek, allTimeseries]);

  useEffect(() => {
    const fetchYield = async () => {
      if (!currentData) return;
      
      try {
        // Call orchestrator instead of direct yield service - uses XGBoost!
        const res = await fetch(`http://localhost:8002/yield/${county}?week=${selectedWeek}`);
        if (res.ok) {
          const data = await res.json();
          // Map orchestrator response to expected format
          setYield({
            predicted_yield: data.predicted_yield,
            uncertainty: data.confidence_interval,
            confidence_lower: data.confidence_lower,
            confidence_upper: data.confidence_upper,
            model_r2: data.model_r2,
            primary_driver: data.primary_driver
          });
        }
      } catch (err) {
        console.error('Yield fetch error:', err);
      }
    };
    fetchYield();
  }, [currentData, county, selectedWeek]);

  // Helper to extract value from number or object with .value property
  const getValueSafe = (obj) => {
    if (typeof obj === 'number') return obj;
    if (obj && typeof obj.value === 'number') return obj.value;
    return null;
  };

  // ALL stress indices use same scale: 0-100, higher = MORE stress
  // 0-20: Healthy, 20-40: Mild, 40-60: Moderate, 60-80: Severe, 80-100: Critical
  const getStressColor = (obj) => {
    const value = getValueSafe(obj);
    if (value == null) return '#6b7280';
    if (value < 20) return '#10b981';  // green - healthy
    if (value < 40) return '#f59e0b';  // yellow - mild
    if (value < 60) return '#f97316';  // orange - moderate
    return '#ef4444';                   // red - severe
  };

  const getStressLabel = (obj) => {
    const value = getValueSafe(obj);
    if (value == null) return 'N/A';
    if (value < 20) return 'Healthy';
    if (value < 40) return 'Mild Stress';
    if (value < 60) return 'Moderate Stress';
    return 'Severe Stress';
  };

  const chartData = timeseries.map((item) => ({
    date: `${item.week_start?.slice(5, 10) || ''}`,
    week: item.week_of_season,
    overall: getValueSafe(item.overall_stress_index),
    water: getValueSafe(item.water_stress_index),
    heat: getValueSafe(item.heat_stress_index),
    vegetation: getValueSafe(item.vegetation_health_index),
    atmosphere: getValueSafe(item.atmospheric_stress_index),
  }));

  const uniqueWeeks = Array.from(new Set(allTimeseries.map(item => item.week_of_season))).sort((a, b) => a - b);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">
      <div className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-8 py-6 flex items-center gap-4">
          <h1 className="text-4xl font-bold text-gray-900">AgriGuard</h1>
          <p className="ml-auto text-lg text-gray-700">Corn Stress Monitoring & Yield Forecasting</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-12">
        <div className="bg-white p-8 rounded-lg shadow mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Select County & Week</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-3">Iowa County</label>
              <select
                value={county}
                onChange={(e) => setCounty(e.target.value)}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg text-lg"
              >
                {IOWA_COUNTIES.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-3">Corn Season Week</label>
              <select
                value={selectedWeek}
                onChange={(e) => setSelectedWeek(parseInt(e.target.value))}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg text-lg"
              >
                {uniqueWeeks.map(w => (
                  <option key={w} value={w}>
                    Week {w} {WEEK_HINTS[w] ? `(${WEEK_HINTS[w]})` : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <p className="text-gray-600 text-lg">Loading data...</p>
          </div>
        ) : (
          <>
            <div className="bg-white p-8 rounded-lg shadow mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Corn Stress Index (CSI)</h2>
              <p className="text-sm text-gray-600 mb-4">CSI (0-100) integrates water stress, heat exposure, vegetation vigor (NDVI), and evaporative demand. Higher values indicate greater stress. Monitor weekly to adjust irrigation, pest management, and harvest timing decisions.</p>
              
              <div className="mb-8 p-6 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Week {selectedWeek} {WEEK_HINTS[selectedWeek] ? `- ${WEEK_HINTS[selectedWeek]}` : ''}</h3>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  <div className="bg-white p-6 rounded-lg shadow text-center">
                    <p className="text-gray-600 font-semibold mb-2">Overall Stress</p>
                    <p className="text-5xl font-bold" style={{ color: getStressColor(currentData?.overall_stress_index) }}>
                      {getValueSafe(currentData?.overall_stress_index)?.toFixed(1) || 'N/A'}
                    </p>
                    <p className="text-sm font-semibold mt-2" style={{ color: getStressColor(currentData?.overall_stress_index) }}>
                      {getStressLabel(currentData?.overall_stress_index)}
                    </p>
                  </div>

                  <div className="bg-white p-6 rounded-lg shadow text-center">
                    <p className="text-gray-600 font-semibold mb-2">Water Stress</p>
                    <p className="text-3xl font-bold" style={{ color: getStressColor(currentData?.water_stress_index) }}>
                      {getValueSafe(currentData?.water_stress_index)?.toFixed(1) || 'N/A'}
                    </p>
                    <p className="text-xs font-semibold mt-2" style={{ color: getStressColor(currentData?.water_stress_index) }}>
                      {getStressLabel(currentData?.water_stress_index)}
                    </p>
                  </div>

                  <div className="bg-white p-6 rounded-lg shadow text-center">
                    <p className="text-gray-600 font-semibold mb-2">Heat Stress</p>
                    <p className="text-3xl font-bold" style={{ color: getStressColor(currentData?.heat_stress_index) }}>
                      {getValueSafe(currentData?.heat_stress_index)?.toFixed(1) || 'N/A'}
                    </p>
                    <p className="text-xs font-semibold mt-2" style={{ color: getStressColor(currentData?.heat_stress_index) }}>
                      {getStressLabel(currentData?.heat_stress_index)}
                    </p>
                  </div>

                  <div className="bg-white p-6 rounded-lg shadow text-center">
                    <p className="text-gray-600 font-semibold mb-2">Vegetation</p>
                    <p className="text-3xl font-bold" style={{ color: getStressColor(currentData?.vegetation_health_index) }}>
                      {getValueSafe(currentData?.vegetation_health_index)?.toFixed(1) || 'N/A'}
                    </p>
                    <p className="text-xs font-semibold mt-2" style={{ color: getStressColor(currentData?.vegetation_health_index) }}>
                      {getStressLabel(currentData?.vegetation_health_index)}
                    </p>
                  </div>

                  <div className="bg-white p-6 rounded-lg shadow text-center">
                    <p className="text-gray-600 font-semibold mb-2">Atmosphere</p>
                    <p className="text-3xl font-bold" style={{ color: getStressColor(currentData?.atmospheric_stress_index) }}>
                      {getValueSafe(currentData?.atmospheric_stress_index)?.toFixed(1) || 'N/A'}
                    </p>
                    <p className="text-xs font-semibold mt-2" style={{ color: getStressColor(currentData?.atmospheric_stress_index) }}>
                      {getStressLabel(currentData?.atmospheric_stress_index)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-8">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Stress Trend</h3>
                {chartData.length > 0 && (
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" interval={2} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="overall" stroke="#f59e0b" name="Overall" strokeWidth={3} dot={false} />
                      <Line type="monotone" dataKey="water" stroke="#3b82f6" name="Water" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="heat" stroke="#ef4444" name="Heat" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="vegetation" stroke="#10b981" name="Vegetation" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            <div className="bg-white p-8 rounded-lg shadow">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Yield Forecast</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="p-8 bg-gradient-to-br from-green-50 to-green-100 rounded-lg border-2 border-green-300">
                  <p className="text-gray-700 font-semibold mb-3">Predicted Yield (Week {selectedWeek})</p>
                  <div className="text-5xl font-bold text-green-700">
                    {yield_?.predicted_yield?.toFixed(1) || 'N/A'}
                  </div>
                  <p className="text-lg text-gray-600 mt-2">bu/acre</p>
                </div>

                <div className="p-8 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border-2 border-blue-300">
                  <p className="text-gray-700 font-semibold mb-3">Forecast Uncertainty</p>
                  <div className="text-4xl font-bold text-blue-700">
                    ±{yield_?.uncertainty?.toFixed(2) || 'N/A'}
                  </div>
                  <p className="text-lg text-gray-600 mt-2">bu/acre</p>
                </div>
              </div>
            </div>
            {/* RAG Chat Section */}
            <div className="bg-white p-8 rounded-lg shadow mt-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">💬 AgriBot Assistant</h2>
              <p className="text-gray-600 text-sm mb-6">
                Ask questions about corn stress, yields, or farming practices. AgriBot uses AI to provide intelligent insights based on your current data.
              </p>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200" style={{ minHeight: "500px" }}>
                <AgriBot
                  apiUrl="http://localhost:8002"
                  fips={county}
                  county={county}
                  week={selectedWeek}
                  currentData={currentData}
                  yield_={yield_}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
