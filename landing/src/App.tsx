import GrainOverlay from "./components/GrainOverlay";
import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import SahelionStackSection from "./components/SahelionStackSection";
import CapabilitiesSection from "./components/CapabilitiesSection";
import InstallSection from "./components/InstallSection";
import MetricsSection from "./components/MetricsSection";
import TrustformerSection from "./components/TrustformerSection";
import EcosystemSection from "./components/EcosystemSection";
import RoadmapSection from "./components/RoadmapSection";
import GrantsSection from "./components/GrantsSection";
import CtaSection from "./components/CtaSection";
import Footer from "./components/Footer";
import "./index.css";

export default function App() {
  return (
    <div className="relative min-h-screen" style={{ background: "var(--bg)" }}>
      <GrainOverlay />
      <Navbar />
      <main>
        <HeroSection />
        <SahelionStackSection />
        <CapabilitiesSection />
        <MetricsSection />
        <TrustformerSection />
        <InstallSection />
        <EcosystemSection />
        <RoadmapSection />
        <GrantsSection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
