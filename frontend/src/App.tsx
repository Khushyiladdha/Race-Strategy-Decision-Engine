import { Route, Routes } from 'react-router-dom'

import { AppShell } from './components/layout/AppShell'
import { Dashboard } from './pages/Dashboard'
import { Insights } from './pages/Insights'
import { ReportView } from './pages/ReportView'
import { StyleGuide } from './pages/StyleGuide'
import { ValidationView } from './pages/ValidationView'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="validation" element={<ValidationView />} />
        <Route path="report" element={<ReportView />} />
        <Route path="insights" element={<Insights />} />
        <Route path="styleguide" element={<StyleGuide />} />
      </Route>
    </Routes>
  )
}
