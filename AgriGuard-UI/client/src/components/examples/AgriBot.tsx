import AgriBot from '../AgriBot';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

export default function AgriBotExample() {
  const [isOpen, setIsOpen] = useState(true);
  
  return (
    <div className="relative h-screen">
      <Button onClick={() => setIsOpen(!isOpen)} className="m-4">
        Toggle AgriBot
      </Button>
      <AgriBot isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </div>
  );
}
