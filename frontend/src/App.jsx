import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar, Footer } from './components/layout';
import Home from './pages/Home';
import Product from './pages/Product';

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col font-sans selection:bg-blue-500/30">
        <Navbar />
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<Product />} />
          </Routes>
        </main>
        <Routes>
          {/* Hide footer on product page for full height workspace */}
          <Route path="/" element={null} />
          <Route path="*" element={<Footer />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
