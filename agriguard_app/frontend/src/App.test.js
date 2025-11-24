import { render, screen } from '@testing-library/react';
import App from './App';

test('renders AgriGuard heading', () => {
  render(<App />);
  const heading = screen.getByRole('heading', { name: /agriguard/i });
  expect(heading).toBeInTheDocument();
});
