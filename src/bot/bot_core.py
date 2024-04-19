import requests
import os

from web3 import Web3
from dotenv import load_dotenv
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.middleware import construct_sign_and_send_raw_middleware



load_dotenv()

web3 = Web3(Web3.HTTPProvider(os.environ.get("BLAST_RPC_URL")))

def get_contract_abi(token_address):
    response = requests.get(f"https://api.blastscan.io/api?module=contract&action=getabi&address={token_address}&apikey={os.environ.get('BLASTSCAN_API_KEY')}").json()
    if 'result' in response and response['result'] is not None:
        return response['result']
    else:
        print(f"Error getting contract ABI for {token_address}.\nRetrying...")


def initialize_hot_wallet():
    PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
    assert PRIVATE_KEY is not None, "You must set the PRIVATE_KEY in the .env file'."
    assert PRIVATE_KEY.startswith("0x")

    account: LocalAccount = Account.from_key(PRIVATE_KEY)
    web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    return account


def get_token_dexscreen_data(token_address):
    response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}").json()
    if 'pairs' in response and response['pairs'] is not None:
        i = 0
        for pair in response['pairs']:
            if response['pairs'][i]['pairAddress'] == os.environ.get("PAIR_ADDRESS"):
                return response['pairs'][i]
            i += 1
    else:
        return None


def get_thruster_token_price(token_address):
    response = requests.get(f"https://api.thruster.finance/token/price?tokenAddress={token_address.lower()}&chainId=81457").json()
    if 'price' in response:
        return response['price']
    else:
        return None