import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { AppLayout } from '@/components/layout/AppLayout'
import Overview from '@/pages/Overview'
import Market from '@/pages/Market'
import Signals from '@/pages/Signals'
import History from '@/pages/History'
import Stats from '@/pages/Stats'
import Logs from '@/pages/Logs'
import Settings from '@/pages/Settings'
import Candles from '@/pages/Candles'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Overview />} />
            <Route path="market" element={<Market />} />
            <Route path="signals" element={<Signals />} />
            <Route path="history" element={<History />} />
            <Route path="stats" element={<Stats />} />
            <Route path="logs" element={<Logs />} />
            <Route path="settings" element={<Settings />} />
            <Route path="candles" element={<Candles />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" />
    </QueryClientProvider>
  )
}
