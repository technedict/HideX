"""Wallet management endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from ..core.service import HideXService
from ..models.wallet import WalletRole
from ..schemas.requests import InitializeWalletRequest, CreateWalletRequest
from ..schemas.responses import WalletResponse, WalletListResponse, ErrorResponse

router = APIRouter(prefix="/wallets", tags=["wallets"])

# Service instance (would use dependency injection in production)
_service: Optional[HideXService] = None


def get_service() -> HideXService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = HideXService()
    return _service


@router.post("/initialize")
async def initialize_wallet(
    request: InitializeWalletRequest,
    service: HideXService = Depends(get_service)
):
    """
    Initialize the wallet system.
    
    If no mnemonic is provided, generates a new one.
    
    ⚠️ IMPORTANT: Store the returned mnemonic securely!
    Loss of mnemonic means loss of all wallets.
    """
    try:
        mnemonic = service.initialize_wallet(request.mnemonic)
        return {
            "success": True,
            "message": "Wallet system initialized",
            "mnemonic": mnemonic,
            "warning": "STORE THIS MNEMONIC SECURELY. DO NOT SHARE IT.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/load")
async def load_wallet(service: HideXService = Depends(get_service)):
    """
    Load existing wallet from encrypted storage.
    
    Requires the correct password to decrypt.
    """
    success = service.load_wallet()
    if success:
        return {"success": True, "message": "Wallet loaded successfully"}
    else:
        raise HTTPException(
            status_code=404,
            detail="No existing wallet found or decryption failed"
        )


@router.post("", response_model=WalletResponse)
async def create_wallet(
    request: CreateWalletRequest,
    service: HideXService = Depends(get_service)
):
    """
    Create a new wallet with specified role.
    
    Roles:
    - funding: Source wallets (may have KYC/CEX history)
    - transit: Intermediate wallets for breaking links
    - destination: Final destination wallets
    """
    try:
        wallet = service.create_wallet(
            role=request.role,
            label=request.label,
            chain=request.chain,
        )
        return WalletResponse(
            id=wallet.id,
            address=wallet.address,
            role=wallet.role,
            state=wallet.state,
            chain=wallet.chain,
            label=wallet.label,
            created_at=wallet.created_at,
            transaction_count=wallet.transaction_count,
            is_one_time=wallet.is_one_time,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=WalletListResponse)
async def list_wallets(
    role: Optional[WalletRole] = None,
    service: HideXService = Depends(get_service)
):
    """List all wallets, optionally filtered by role."""
    wallets = service.list_wallets(role=role)
    return WalletListResponse(
        wallets=[
            WalletResponse(
                id=w.id,
                address=w.address,
                role=w.role,
                state=w.state,
                chain=w.chain,
                label=w.label,
                created_at=w.created_at,
                transaction_count=w.transaction_count,
                is_one_time=w.is_one_time,
            )
            for w in wallets
        ],
        total=len(wallets),
    )


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: str,
    service: HideXService = Depends(get_service)
):
    """Get wallet by ID."""
    wallet = service.get_wallet(wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return WalletResponse(
        id=wallet.id,
        address=wallet.address,
        role=wallet.role,
        state=wallet.state,
        chain=wallet.chain,
        label=wallet.label,
        created_at=wallet.created_at,
        transaction_count=wallet.transaction_count,
        is_one_time=wallet.is_one_time,
    )


@router.post("/{wallet_id}/retire", response_model=WalletResponse)
async def retire_wallet(
    wallet_id: str,
    service: HideXService = Depends(get_service)
):
    """Retire a wallet from use."""
    try:
        wallet = service.retire_wallet(wallet_id)
        return WalletResponse(
            id=wallet.id,
            address=wallet.address,
            role=wallet.role,
            state=wallet.state,
            chain=wallet.chain,
            label=wallet.label,
            created_at=wallet.created_at,
            transaction_count=wallet.transaction_count,
            is_one_time=wallet.is_one_time,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
