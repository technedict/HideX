# HideX

> **Privacy-Hygiene and Transaction-Risk Management Tool for Blockchain Users**

---

## ⚠️ CRITICAL DISCLAIMERS

### What HideX IS NOT

- **NOT a mixer, tumbler, or obfuscation service**
- **NOT a tool for "untraceable" or "anonymous" transfers**
- **NOT a sanction bypass or KYC evasion tool**
- **NOT a guarantee of privacy or anonymity**

### What HideX IS

HideX is a **privacy hygiene tool** that helps blockchain users:

1. **Simulate** transaction paths before execution
2. **Score** privacy/traceability risk with explainable metrics
3. **Enforce** wallet hygiene and operational discipline
4. **Plan** safer transaction routes under explicit user policies
5. **Audit** all actions for compliance and learning

**The goal is to REDUCE TRANSACTION LINKABILITY THROUGH DISCIPLINE, NOT SECRECY.**

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Policy Configuration](#policy-configuration)
- [Risk Scoring](#risk-scoring)
- [Legal & Compliance](#legal--compliance)
- [Development](#development)
- [TODO / Post-MVP](#todo--post-mvp)

---

## ✨ Features

### Core Modules

| Module | Description |
|--------|-------------|
| **Privacy Policy Engine** | Rule-based, deterministic policy validation from JSON |
| **Wallet Hygiene Manager** | HD wallet generation with role-based separation |
| **Risk Simulation Engine** | Explainable 0-100 risk scoring with detailed factors |
| **Routing Planner** | Multi-hop and split-amount transaction planning |
| **Transaction Executor** | Dry-run by default, explicit confirmation required |
| **Audit Logger** | Immutable, append-only logs for forensic review |
| **Frontend Dashboard** | Minimal React UI with no analytics or telemetry |

### Design Principles

- ✅ **Simulation Only by Default** - No execution without explicit confirmation
- ✅ **Deterministic** - Same inputs always produce same outputs
- ✅ **Explainable** - No black-box ML, all factors are documented
- ✅ **Local-First** - No cloud dependencies, all data stored locally
- ✅ **Auditable** - Complete logging for compliance review
- ✅ **Seedable Randomness** - Reproducible simulations for testing

---

## 🏗️ Architecture

```
hidex/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/               # REST API endpoints
│   │   ├── config/            # Application settings
│   │   ├── core/              # Core service orchestration
│   │   ├── models/            # Pydantic data models
│   │   ├── modules/           # Core business logic
│   │   │   ├── policy_engine.py
│   │   │   ├── wallet_manager.py
│   │   │   ├── risk_engine.py
│   │   │   ├── routing_planner.py
│   │   │   ├── transaction_executor.py
│   │   │   └── audit_logger.py
│   │   ├── schemas/           # API request/response schemas
│   │   └── utils/             # Utilities (crypto, random)
│   ├── tests/                 # Test suite
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── types/             # TypeScript types
│   │   └── utils/             # API client
│   ├── package.json
│   └── vite.config.ts
├── examples/                   # Example policy files
│   ├── default_policy.json
│   └── strict_policy.json
└── docs/                       # Documentation
```

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:5173` and will proxy API requests to the backend.

---

## 📖 Usage

### 1. Initialize Wallet System

```bash
curl -X POST http://localhost:8000/wallets/initialize
```

**⚠️ Save the returned mnemonic securely!**

### 2. Create Wallets

```bash
# Create a funding wallet (source)
curl -X POST http://localhost:8000/wallets \
  -H "Content-Type: application/json" \
  -d '{"role": "funding", "label": "Main source"}'

# Create transit wallets (intermediate)
curl -X POST http://localhost:8000/wallets \
  -H "Content-Type: application/json" \
  -d '{"role": "transit", "label": "Transit 1"}'

# Create destination wallet
curl -X POST http://localhost:8000/wallets \
  -H "Content-Type: application/json" \
  -d '{"role": "destination", "label": "Final destination"}'
```

### 3. Create a Transaction Plan

```bash
curl -X POST http://localhost:8000/plans \
  -H "Content-Type: application/json" \
  -d '{
    "source_address": "0x1234...",
    "destination_address": "0xabcd...",
    "amount_wei": "1000000000000000000",
    "plan_type": "multi_hop",
    "num_hops": 2
  }'
```

### 4. Simulate the Plan

```bash
curl -X POST http://localhost:8000/plans/{plan_id}/simulate
```

### 5. Review Risk Assessment

```bash
curl http://localhost:8000/plans/{plan_id}/risk
```

---

## 📚 API Reference

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/health/ready` | GET | Readiness check |

### Wallets

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/wallets/initialize` | POST | Initialize wallet system |
| `/wallets` | GET | List all wallets |
| `/wallets` | POST | Create new wallet |
| `/wallets/{id}` | GET | Get wallet details |
| `/wallets/{id}/retire` | POST | Retire a wallet |

### Plans

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/plans` | POST | Create transaction plan |
| `/plans/{id}` | GET | Get plan details |
| `/plans/{id}/simulate` | POST | Simulate plan |
| `/plans/{id}/risk` | GET | Get risk assessment |
| `/plans/{id}/validate` | GET | Validate against policy |
| `/plans/{id}/execute` | POST | Execute plan (requires confirmation) |

### Policies

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/policies` | GET | List policies |
| `/policies/{id}` | GET | Get policy details |
| `/policies/{id}/activate` | POST | Set active policy |
| `/policies/default/template` | GET | Get default policy template |

### Audit

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/audit/current` | GET | Get current session log |
| `/audit/sessions` | GET | List all sessions |
| `/audit/sessions/{id}` | GET | Get session details |
| `/audit/reports/{plan_id}` | GET | Generate compliance report |

---

## ⚙️ Policy Configuration

Policies are loaded from JSON files in the `policies/` directory.

### Example Policy

```json
{
  "id": "default",
  "name": "Default Privacy Policy",
  "version": "1.0.0",
  "description": "Standard privacy hygiene policy",
  "strict_mode": false,
  "allow_override": true,
  "rules": [
    {
      "id": "no_reuse",
      "type": "no_address_reuse",
      "name": "No Address Reuse",
      "description": "Prevent reusing addresses",
      "enabled": true,
      "severity": "error",
      "rationale": "Address reuse creates clear links"
    },
    {
      "id": "min_delay",
      "type": "min_delay",
      "name": "Minimum Delay",
      "description": "Minimum time between steps",
      "severity": "warning",
      "parameters": {"min_seconds": 300}
    }
  ]
}
```

### Available Rule Types

| Rule Type | Description | Parameters |
|-----------|-------------|------------|
| `no_address_reuse` | Prevent address reuse | - |
| `min_delay` | Minimum delay between steps | `min_seconds` |
| `max_delay` | Maximum delay between steps | `max_seconds` |
| `no_same_block` | No same-block transactions | - |
| `min_hops` | Minimum number of hops | `min_hops` |
| `max_hops` | Maximum number of hops | `max_hops` |
| `max_amount_similarity` | Limit amount similarity | `max_percent` |

---

## 📊 Risk Scoring

### Risk Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Source Contamination | 25% | CEX/KYC history of source address |
| Timing Correlation | 20% | How close transactions are in time |
| Amount Similarity | 20% | How similar amounts are |
| Address Reuse | 15% | Reusing addresses in plan |
| Cross-Chain Heuristic | 10% | Multi-chain correlation risk |
| Same Block Activity | 5% | Transactions in same block |
| Round Amount | 3% | Using round numbers |
| Gas Pattern | 2% | Consistent gas usage |

### Risk Bands

| Band | Score Range | Meaning |
|------|-------------|---------|
| **LOW** | 0-33 | Well-structured plan |
| **MEDIUM** | 34-66 | Review recommended |
| **HIGH** | 67-100 | Significant issues |

---

## ⚖️ Legal & Compliance

### Intended Use

HideX is designed for **legitimate privacy hygiene** purposes:

- Separating personal and business transactions
- Reducing on-chain correlation for operational security
- Learning about transaction privacy best practices
- Self-auditing transaction patterns

### Prohibited Uses

HideX MUST NOT be used for:

- ❌ Money laundering
- ❌ Sanctions evasion
- ❌ Tax evasion
- ❌ Terrorist financing
- ❌ Any illegal activity

### Compliance Features

- Complete audit logging for regulatory review
- Policy-based validation with clear violation tracking
- Compliance report generation
- No obfuscation or mixing features

### Disclaimer

This software is provided "as-is" without warranty. Users are responsible for complying with all applicable laws and regulations in their jurisdiction.

---

## 🛠️ Development

### Running Tests

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v
```

### Code Style

```bash
# Linting
ruff check .

# Type checking
mypy app/
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HIDEX_DEBUG` | Enable debug mode | `false` |
| `HIDEX_SECRET_KEY` | Encryption key | (required in production) |
| `HIDEX_DATABASE_URL` | Database URL | `sqlite:///./hidex.db` |
| `HIDEX_SIMULATION_SEED` | Seed for determinism | `null` |

---

## 📝 TODO / Post-MVP

The following features are planned for future development:

### High Priority
- [ ] Multi-chain support (Polygon, Arbitrum, etc.)
- [ ] Token transfer support (ERC20)
- [ ] Database persistence for plans and wallets
- [ ] Enhanced gas estimation

### Medium Priority
- [ ] Import/export wallet functionality
- [ ] Batch plan creation
- [ ] Advanced timing strategies
- [ ] Chain analysis API integration

### Low Priority
- [ ] Mobile-responsive UI improvements
- [ ] Plan templates
- [ ] Historical risk trend analysis
- [ ] Integration with hardware wallets

### Security Enhancements
- [ ] Hardware security module (HSM) support
- [ ] Multi-signature wallet support
- [ ] Enhanced key derivation options
- [ ] Secure enclave integration

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.

**Remember: This is a privacy hygiene tool, not an anonymity tool. All contributions must align with this philosophy.**

---

*HideX - Reduce transaction linkability through discipline, not secrecy.*