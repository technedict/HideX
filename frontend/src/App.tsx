import { useState } from 'react';
import Dashboard from './components/Dashboard';
import WalletManager from './components/WalletManager';
import PlanBuilder from './components/PlanBuilder';
import RiskViewer from './components/RiskViewer';
import AuditLog from './components/AuditLog';
import DisclaimerBanner from './components/DisclaimerBanner';

type Tab = 'dashboard' | 'wallets' | 'plans' | 'risk' | 'audit';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  return (
    <div className="app">
      <nav className="nav">
        <span className="nav-brand">🔒 HideX</span>
        <button
          className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          Dashboard
        </button>
        <button
          className={`nav-link ${activeTab === 'wallets' ? 'active' : ''}`}
          onClick={() => setActiveTab('wallets')}
        >
          Wallets
        </button>
        <button
          className={`nav-link ${activeTab === 'plans' ? 'active' : ''}`}
          onClick={() => setActiveTab('plans')}
        >
          Plans
        </button>
        <button
          className={`nav-link ${activeTab === 'risk' ? 'active' : ''}`}
          onClick={() => setActiveTab('risk')}
        >
          Risk Analysis
        </button>
        <button
          className={`nav-link ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          Audit Log
        </button>
      </nav>

      <div className="container">
        <DisclaimerBanner />

        {activeTab === 'dashboard' && <Dashboard onNavigate={setActiveTab} />}
        {activeTab === 'wallets' && <WalletManager />}
        {activeTab === 'plans' && <PlanBuilder />}
        {activeTab === 'risk' && <RiskViewer />}
        {activeTab === 'audit' && <AuditLog />}
      </div>
    </div>
  );
}

export default App;
