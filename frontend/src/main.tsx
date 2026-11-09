import '@/index.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router'
import { Toaster } from 'sonner'
import { Shell } from '@/components/Shell'
import { setupApiClient } from '@/lib/api'
import { ThemeProvider } from '@/lib/theme'
import { Explorer } from '@/pages/Explorer'
import { HowItWorks } from '@/pages/HowItWorks'
import { NotFound } from '@/pages/NotFound'

setupApiClient()
const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 10_000 } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route element={<Shell />}>
              <Route index element={<Explorer />} />
              <Route path="how-it-works" element={<HowItWorks />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster richColors />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
