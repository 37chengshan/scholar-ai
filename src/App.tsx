import React, { Suspense } from 'react';
import { HelmetProvider } from 'react-helmet-async';
import { Hero } from './components/sections/Hero';
import { Features } from './components/sections/Features';
import { Footer } from './components/sections/Footer';
import { ParticleBackground } from './components/effects/ParticleBackground';
import { Navigation } from './components/ui/Navigation';
import { LandingSEO } from './components/seo/LandingSEO';
import './styles/globals.css';

// Lazy load Demo section (below the fold)
const Demo = React.lazy(() => import('./components/sections/Demo').then(module => ({ default: module.Demo })));

// Skeleton loader for Demo section
const DemoSkeleton: React.FC = () => (
  <div className="py-24 lg:py-32">
    <div className="container px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="animate-pulse">
          <div className="h-8 bg-white/5 rounded-lg w-1/3 mx-auto mb-4" />
          <div className="h-12 bg-white/5 rounded-lg w-1/2 mx-auto mb-16" />
          <div className="h-[400px] bg-white/5 rounded-2xl" />
        </div>
      </div>
    </div>
  </div>
);

function App() {
  return (
    <HelmetProvider>
      <div className="min-h-screen bg-bg-primary relative">
        {/* Global Particle Background - Fixed to cover entire page */}
        <div className="fixed inset-0 z-0 pointer-events-none">
          <ParticleBackground />
        </div>

        {/* SEO */}
        <LandingSEO />

        {/* Navigation */}
        <Navigation />

        {/* Page Content */}
        <div className="relative z-10">
          <section id="hero"><Hero /></section>
          <section id="features"><Features /></section>
          <section id="demo">
            <Suspense fallback={<DemoSkeleton />}>
              <Demo />
            </Suspense>
          </section>
          <Footer />
        </div>
      </div>
    </HelmetProvider>
  );
}

export default App;
