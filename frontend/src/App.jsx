import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar, Footer } from './components/layout';
import Home from './pages/Home';
import About from './pages/About';
import Service from './pages/Service';
import Product from './pages/Product';

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col font-sans selection:bg-blue-500/30">
        <Navbar />
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/service" element={<Service />} />
            <Route path="/product" element={<Product />} />
          </Routes>
        </main>
        <Routes>
          {/* Hide footer on product page for full height workspace */}
          <Route path="/product" element={null} />
          <Route path="*" element={<Footer />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
