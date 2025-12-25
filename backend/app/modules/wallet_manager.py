"""
Wallet Hygiene Manager for HideX.

The Wallet Manager is responsible for:
- Deterministic HD wallet generation
- Role-based wallet separation (funding, transit, destination)
- One-time address enforcement
- Encrypted keystore management
- NEVER transmitting private keys

Design principles:
- Keys stored locally only
- Encrypted at rest
- Role separation for operational hygiene
"""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from eth_account import Account
from eth_account.hdaccount import generate_mnemonic, seed_from_mnemonic

from ..models.wallet import Wallet, WalletRole, WalletState, WalletBalance
from ..utils.crypto import encrypt_data, decrypt_data, generate_id, hash_data
from ..config import get_settings


# Enable HD wallet features
Account.enable_unaudited_hdwallet_features()


class WalletManager:
    """
    Wallet Hygiene Manager.
    
    Manages wallets with:
    - Deterministic HD derivation
    - Role-based separation
    - One-time address enforcement
    - Encrypted storage
    
    SECURITY: Private keys are NEVER transmitted or exposed.
    """
    
    # Standard derivation paths by role
    DERIVATION_PATHS = {
        WalletRole.FUNDING: "m/44'/60'/0'/0",  # Standard Ethereum path
        WalletRole.TRANSIT: "m/44'/60'/1'/0",  # Separate account for transit
        WalletRole.DESTINATION: "m/44'/60'/2'/0",  # Separate account for destination
    }
    
    def __init__(
        self,
        keystore_dir: Optional[Path] = None,
        password: Optional[str] = None
    ):
        """
        Initialize the Wallet Manager.
        
        Args:
            keystore_dir: Directory for encrypted keystores
            password: Master password for encryption
        """
        settings = get_settings()
        self._keystore_dir = keystore_dir or settings.keystore_dir
        self._keystore_dir.mkdir(parents=True, exist_ok=True)
        
        # Password for encryption (should be provided by user in production)
        self._password = password or settings.secret_key
        
        # In-memory wallet registry (addresses only, not keys)
        self._wallets: dict[str, Wallet] = {}
        
        # Mnemonic storage path
        self._mnemonic_path = self._keystore_dir / ".mnemonic.enc"
        
        # Derivation indices by role
        self._derivation_indices: dict[WalletRole, int] = {
            role: 0 for role in WalletRole
        }
    
    def generate_mnemonic(self, num_words: int = 12) -> str:
        """
        Generate a new mnemonic phrase.
        
        Args:
            num_words: Number of words (12, 15, 18, 21, or 24)
            
        Returns:
            Mnemonic phrase (space-separated words)
            
        WARNING: Store this securely! Loss means loss of all wallets.
        """
        return generate_mnemonic(num_words=num_words, lang="english")
    
    def set_mnemonic(self, mnemonic: str, save_encrypted: bool = True) -> None:
        """
        Set the master mnemonic for HD derivation.
        
        Args:
            mnemonic: The mnemonic phrase
            save_encrypted: Whether to save encrypted to disk
            
        WARNING: Never transmit or expose the mnemonic.
        """
        # Validate mnemonic by attempting to derive
        Account.from_mnemonic(mnemonic)
        
        self._mnemonic = mnemonic
        
        if save_encrypted:
            encrypted, salt = encrypt_data(mnemonic, self._password)
            with open(self._mnemonic_path, 'wb') as f:
                # Store salt length, salt, then encrypted data
                f.write(len(salt).to_bytes(4, 'big'))
                f.write(salt)
                f.write(encrypted)
    
    def load_mnemonic(self) -> bool:
        """
        Load encrypted mnemonic from disk.
        
        Returns:
            True if successfully loaded, False otherwise
        """
        if not self._mnemonic_path.exists():
            return False
        
        try:
            with open(self._mnemonic_path, 'rb') as f:
                salt_len = int.from_bytes(f.read(4), 'big')
                salt = f.read(salt_len)
                encrypted = f.read()
            
            self._mnemonic = decrypt_data(encrypted, self._password, salt)
            return True
        except Exception:
            return False
    
    def has_mnemonic(self) -> bool:
        """Check if a mnemonic is set."""
        return hasattr(self, '_mnemonic') and self._mnemonic is not None
    
    def create_wallet(
        self,
        role: WalletRole,
        label: Optional[str] = None,
        chain: str = "ethereum"
    ) -> Wallet:
        """
        Create a new wallet with specified role.
        
        Uses deterministic HD derivation from the master mnemonic.
        The wallet is automatically marked as one-time use.
        
        Args:
            role: Wallet role (funding, transit, destination)
            label: Optional user-defined label
            chain: Blockchain network
            
        Returns:
            Created Wallet object (without private key)
        """
        if not self.has_mnemonic():
            raise ValueError("No mnemonic set. Call set_mnemonic() first.")
        
        # Get derivation path for role
        base_path = self.DERIVATION_PATHS[role]
        index = self._derivation_indices[role]
        derivation_path = f"{base_path}/{index}"
        
        # Derive account from mnemonic
        account = Account.from_mnemonic(
            self._mnemonic,
            account_path=derivation_path
        )
        
        # Create wallet object (no private key stored here)
        wallet_id = generate_id("wallet")
        wallet = Wallet(
            id=wallet_id,
            address=account.address,
            role=role,
            state=WalletState.ACTIVE,
            chain=chain,
            derivation_path=derivation_path,
            derivation_index=index,
            label=label or f"{role.value}_{index}",
            is_one_time=True,
            reuse_allowed=False,
        )
        
        # Store encrypted private key
        self._store_private_key(wallet_id, account.key.hex())
        
        # Update index for next derivation
        self._derivation_indices[role] = index + 1
        
        # Register wallet
        self._wallets[wallet_id] = wallet
        
        return wallet
    
    def _store_private_key(self, wallet_id: str, private_key: str) -> None:
        """
        Store private key encrypted on disk.
        
        SECURITY: Keys are encrypted with the master password.
        """
        keystore_file = self._keystore_dir / f"{wallet_id}.key"
        encrypted, salt = encrypt_data(private_key, self._password)
        
        with open(keystore_file, 'wb') as f:
            f.write(len(salt).to_bytes(4, 'big'))
            f.write(salt)
            f.write(encrypted)
    
    def _load_private_key(self, wallet_id: str) -> str:
        """
        Load private key from encrypted storage.
        
        SECURITY: This should only be called when signing transactions.
        """
        keystore_file = self._keystore_dir / f"{wallet_id}.key"
        
        if not keystore_file.exists():
            raise ValueError(f"Keystore not found for wallet: {wallet_id}")
        
        with open(keystore_file, 'rb') as f:
            salt_len = int.from_bytes(f.read(4), 'big')
            salt = f.read(salt_len)
            encrypted = f.read()
        
        return decrypt_data(encrypted, self._password, salt)
    
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID."""
        return self._wallets.get(wallet_id)
    
    def get_wallet_by_address(self, address: str) -> Optional[Wallet]:
        """Get wallet by address."""
        for wallet in self._wallets.values():
            if wallet.address.lower() == address.lower():
                return wallet
        return None
    
    def list_wallets(
        self,
        role: Optional[WalletRole] = None,
        state: Optional[WalletState] = None
    ) -> list[Wallet]:
        """
        List wallets with optional filtering.
        
        Args:
            role: Filter by role
            state: Filter by state
            
        Returns:
            List of matching wallets
        """
        wallets = list(self._wallets.values())
        
        if role:
            wallets = [w for w in wallets if w.role == role]
        if state:
            wallets = [w for w in wallets if w.state == state]
        
        return wallets
    
    def mark_wallet_used(self, wallet_id: str) -> Wallet:
        """
        Mark a wallet as used.
        
        One-time wallets should not be reused after this.
        """
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        wallet.state = WalletState.USED
        wallet.used_at = datetime.utcnow()
        wallet.transaction_count += 1
        
        return wallet
    
    def can_use_wallet(self, wallet_id: str) -> tuple[bool, str]:
        """
        Check if a wallet can be used.
        
        Returns:
            (can_use, reason) tuple
        """
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            return False, "Wallet not found"
        
        if wallet.state == WalletState.COMPROMISED:
            return False, "Wallet is marked as compromised"
        
        if wallet.state == WalletState.RETIRED:
            return False, "Wallet is retired"
        
        if wallet.state == WalletState.USED and wallet.is_one_time and not wallet.reuse_allowed:
            return False, "One-time wallet already used"
        
        return True, "OK"
    
    def retire_wallet(self, wallet_id: str) -> Wallet:
        """Retire a wallet from use."""
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        wallet.state = WalletState.RETIRED
        return wallet
    
    def mark_compromised(self, wallet_id: str) -> Wallet:
        """Mark a wallet as compromised."""
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        wallet.state = WalletState.COMPROMISED
        return wallet
    
    def get_signing_account(self, wallet_id: str) -> Account:
        """
        Get a signing-capable account.
        
        SECURITY: Only use this when actually signing transactions.
        Do not cache or store the returned account.
        """
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        can_use, reason = self.can_use_wallet(wallet_id)
        if not can_use:
            raise ValueError(f"Cannot use wallet: {reason}")
        
        private_key = self._load_private_key(wallet_id)
        return Account.from_key(private_key)
    
    def save_state(self) -> None:
        """Save wallet registry to disk."""
        state_file = self._keystore_dir / "wallets.json"
        state = {
            "wallets": {
                wid: wallet.model_dump() for wid, wallet in self._wallets.items()
            },
            "derivation_indices": {
                role.value: idx for role, idx in self._derivation_indices.items()
            },
        }
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def load_state(self) -> bool:
        """Load wallet registry from disk."""
        state_file = self._keystore_dir / "wallets.json"
        
        if not state_file.exists():
            return False
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            self._wallets = {
                wid: Wallet(**data) for wid, data in state.get("wallets", {}).items()
            }
            
            for role_value, idx in state.get("derivation_indices", {}).items():
                role = WalletRole(role_value)
                self._derivation_indices[role] = idx
            
            return True
        except Exception:
            return False
