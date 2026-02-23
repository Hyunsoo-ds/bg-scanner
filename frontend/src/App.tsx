import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ScanPage from '@/pages/ScanPage'
import ResultsPage from '@/pages/ResultsPage'
import WorkPage from '@/pages/WorkPage'
import { Link } from 'react-router-dom'
import './index.css'

const queryClient = new QueryClient()

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <Router>
                <div className="min-h-screen bg-background text-foreground">
                    <header className="border-b bg-card px-6 py-4 flex items-center justify-between sticky top-0 z-10">
                        <div className="font-bold text-xl flex items-center gap-2">
                            <span>🛡️</span>
                            <Link to="/">BG-Scanner</Link>
                        </div>
                        <nav className="flex gap-4 items-center">
                            <Link to="/" className="text-sm font-medium hover:text-primary">Dashboard</Link>
                            <Link to="/work" className="text-sm font-medium hover:text-primary">Workers</Link>
                        </nav>
                        <div className="text-sm text-muted-foreground">
                            v0.1.0 (MVP)
                        </div>
                    </header>
                    <main>
                        <Routes>
                            <Route path="/" element={<ScanPage />} />
                            <Route path="/scans/:scanId" element={<ResultsPage />} />
                            <Route path="/work" element={<WorkPage />} />
                        </Routes>
                    </main>
                </div>
            </Router>
        </QueryClientProvider>
    )
}

export default App
