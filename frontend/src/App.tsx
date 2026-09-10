// SpecMatch main application routes

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './layouts/Layout';
import { HomePage } from './pages/HomePage';
import { SearchPage } from './pages/SearchPage';
import { AnalyzePage } from './pages/AnalyzePage';
import { StandardsPage } from './pages/StandardsPage';
import { StandardDetailPage } from './pages/StandardDetailPage';
import { ComparePage } from './pages/ComparePage';
import { SavedPage } from './pages/SavedPage';
import { HistoryPage } from './pages/HistoryPage';
import { MethodologyPage } from './pages/MethodologyPage';

export function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="analyze" element={<AnalyzePage />} />
          <Route path="standards" element={<StandardsPage />} />
          <Route path="standards/:standardNumber" element={<StandardDetailPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="saved" element={<SavedPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="methodology" element={<MethodologyPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
