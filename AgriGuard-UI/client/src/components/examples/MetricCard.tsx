import MetricCard from '../MetricCard';
import { Leaf } from 'lucide-react';

export default function MetricCardExample() {
  return <MetricCard title="NDVI" value="0.78" unit="index" trend={5.2} icon={Leaf} />;
}
