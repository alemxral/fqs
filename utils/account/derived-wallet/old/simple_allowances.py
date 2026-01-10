#!/usr/bin/env python3
"""
Simple Allowances Setter - Works with web3 6.14.0
=================================================
"""
from web3 import Web3
from web3.constants import MAX_INT

# Your Polymarket credentials - use the wallet your private key actually controls
rpc_url = "https://polygon-rpc.com"
priv_key = "0xe4f46edc2c00bb8253775a7fc55af8c832d5e0616137883ac3594741c8f4203b"

# Use the wallet that matches your private key (not FUNDER)
from web3 import Web3
temp_web3 = Web3()
account = temp_web3.eth.account.from_key(priv_key)
pub_key = account.address  # This will be 0xBA4696ec3BA07806bC5960674a9a7316D9d00d52

chain_id = 137

erc20_approve = """[{"constant": false,"inputs": [{"name": "_spender","type": "address" },{ "name": "_value", "type": "uint256" }],"name": "approve","outputs": [{ "name": "", "type": "bool" }],"payable": false,"stateMutability": "nonpayable","type": "function"}]"""
erc1155_set_approval = """[{"inputs": [{ "internalType": "address", "name": "operator", "type": "address" },{ "internalType": "bool", "name": "approved", "type": "bool" }],"name": "setApprovalForAll","outputs": [],"stateMutability": "nonpayable","type": "function"}]"""

usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ctf_address = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

web3 = Web3(Web3.HTTPProvider(rpc_url))

print("🚀 Setting Polymarket Allowances")
print(f"📧 Wallet: {pub_key}")
print(f"🌐 Network: Polygon (Chain ID: {chain_id})")

try:
    # Add POA middleware for Polygon
    from web3.middleware import ExtraDataToPOAMiddleware
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    print("✅ POA middleware added")
except ImportError:
    print("⚠️ POA middleware not available")

# Check connection
if not web3.is_connected():
    print("❌ Failed to connect to network")
    exit(1)

print("✅ Connected to network")

usdc = web3.eth.contract(address=usdc_address, abi=erc20_approve)
ctf = web3.eth.contract(address=ctf_address, abi=erc1155_set_approval)

# Gas settings
gas_limit = 100000
gas_price = web3.to_wei('30', 'gwei')

def safe_approve(contract, spender_address, contract_name, is_erc1155=False):
    """Safely approve with proper gas settings"""
    try:
        nonce = web3.eth.get_transaction_count(pub_key)
        print(f"🔄 {contract_name} approval (nonce: {nonce})...")
        
        if is_erc1155:
            # ERC1155 setApprovalForAll
            raw_txn = contract.functions.setApprovalForAll(spender_address, True).build_transaction({
                "chainId": chain_id,
                "from": pub_key,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price
            })
        else:
            # ERC20 approve
            raw_txn = contract.functions.approve(spender_address, int(MAX_INT, 0)).build_transaction({
                "chainId": chain_id,
                "from": pub_key,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price
            })
        
        signed_tx = web3.eth.account.sign_transaction(raw_txn, private_key=priv_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"   📤 Tx sent: {tx_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, 600)
        
        if receipt.status == 1:
            print(f"   ✅ SUCCESS!")
            return True
        else:
            print(f"   ❌ FAILED!")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)[:100]}...")
        return False

# Set approvals for all Polymarket contracts
contracts = [
    ("0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E", "CTF Exchange"),
    ("0xC5d563A36AE78145C45a50134d48A1215220f80a", "Neg Risk CTF Exchange"),
    ("0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296", "Neg Risk Adapter")
]

success_count = 0
total_count = 0

print("\n🎯 Starting approvals...")

for contract_address, contract_name in contracts:
    print(f"\n📋 {contract_name} ({contract_address})")
    
    # USDC approval
    if safe_approve(usdc, contract_address, f"{contract_name} USDC"):
        success_count += 1
    total_count += 1
    
    # CTF approval
    if safe_approve(ctf, contract_address, f"{contract_name} CTF", is_erc1155=True):
        success_count += 1
    total_count += 1

print(f"\n🎉 COMPLETE!")
print(f"📊 Success: {success_count}/{total_count}")

if success_count == total_count:
    print("✅ ALL ALLOWANCES SET!")
    print("🚀 You can now trade on Polymarket!")
else:
    print("⚠️ Some failures occurred")