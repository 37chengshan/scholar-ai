import React from 'react';
import { Hero } from './components/sections/Hero';
import { PainPoints } from './components/sections/PainPoints';
import { Features } from './components/sections/Features';
import { Demo } from './components/sections/Demo';
import { Footer } from './components/sections/Footer';
import { ParticleBackground } from './components/effects/ParticleBackground';
import './styles/globals.css';

function App() {
  return (
    <div className="min-h-screen bg-bg-primary relative">
      {/* Global Particle Background - Fixed to cover entire page */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <ParticleBackground />
      </div>

      {/* Page Content */}
      <div className="relative z-10">
        <Hero />
        <PainPoints />
        <Features />
        <Demo />
        <Footer />
      </div>
    </div>
  );
}

export default App;
