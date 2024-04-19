import os
from textwrap import dedent
import time
import atexit
import requests
import bot_core

from web3 import Web3
from inputimeout import inputimeout, TimeoutOccurred
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

last_known_prices = {
    'eth': 0
}

stat_tracker = {
    "start_epoch": 0,
    "moon": {
        "entry_count": 0,
        "wins": 0,
        "win_percent": 0,
        "wagered": 0,
        "winnings": 0
    },
    "doom": {
        "entry_count": 0,
        "wins": 0,
        "win_percent": 0,
        "wagered": 0,
        "winnings": 0
    },
    "total": {
        "entry_count": 0,
        "wins": 0,
        "win_percent": 0,
        "wagered": 0,
        "winnings": 0
    },
    "gas_fees": {
        "total": 0
    }
}

latest_entry = {
    "epoch": [],
    "wager": [],
    "position": []
}

unclaimed_win = {
    "epochs": [],
    "amount": 0
}

WETH_ADDRESS = os.environ.get("WETH_ADDRESS") # Blast L2 WETH address
CONTRACT_ADDRESS = os.environ.get("MOD_CONTRACT_ADDRESS") # Moon or Doom Contract Address

CONTRACT_ABI = bot_core.get_contract_abi(CONTRACT_ADDRESS)

web3 = Web3(Web3.HTTPProvider(os.environ.get("BLAST_RPC_URL")))

# Blast L2 Moon or Doom contract
mod_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

account = bot_core.initialize_hot_wallet()


def moon_or_doom():
    start_epoch = int(time.time())
    stat_tracker['start_epoch'] = start_epoch
    last_known_prices['eth'] = get_eth_to_usd_rate()
    wager = 0
    time_limit = 10
    while True:
        try:
            if wager == 0:
                wager = float(input("How much ETH would you like to wager?\n"))
            print(f"\n{bcolors.OKBLACK}Current wager is:{bcolors.ENDC}{bcolors.OKGREEN} {wager} {bcolors.ENDC}{bcolors.OKBLACK}ETH{bcolors.ENDC}\n")
            wei_wager = web3.to_wei(wager, 'ether')
            try: 
                user_input = inputimeout(prompt="Moon or Doom? ('m' or 'd' || 'w' to change wager, 'c' claim winnings, 'x' to exit): ", timeout=time_limit).lower()
            except TimeoutOccurred:
                user_input = "s"
            
            if user_input == "x":
                break

            elif user_input == "w":
                wager = float(input("How much ETH would you like to wager?\n"))
                wei_wager = web3.to_wei(wager, 'ether')
                continue

            elif user_input == "c":
                claim_winnings()
                continue

            elif user_input == "s":
                current_epoch = get_current_yolo_epoch()
                check_for_win()
                print("\033c", end="")
                print(f"\n \
{bcolors.OKCYAN}Session: {(int(time.time()) - stat_tracker['start_epoch']) / 60:.2f} minutes\t\t\t\tCurrent Epoch: {current_epoch}{bcolors.ENDC}\n\n \
{bcolors.OKGREEN}\
                    Moon Entries: {stat_tracker['moon']['entry_count']}\n \
                    Moon Wins: {stat_tracker['moon']['wins']}\n \
                    Moon Win %: {stat_tracker['moon']['win_percent']:.2f}\n \
                    Moon ETH Wagered: {stat_tracker['moon']['wagered']}\n \
                    Moon Winnings: {stat_tracker['moon']['winnings']}{bcolors.ENDC}\n\n \
{bcolors.OKRED}\
                    Doom Entries: {stat_tracker['doom']['entry_count']}\n \
                    Doom Wins: {stat_tracker['doom']['wins']}\n \
                    Doom Win %: {stat_tracker['doom']['win_percent']:.2f}\n \
                    Doom ETH Wagered: {stat_tracker['doom']['wagered']}\n \
                    Doom Winnings: {stat_tracker['doom']['winnings']}{bcolors.ENDC}\n\n \
\
{bcolors.OKBLACK}Session Profit: {bcolors.ENDC}{bcolors.OKGREEN}{stat_tracker['total']['winnings']}{bcolors.ENDC}{bcolors.OKBLACK} ETH{bcolors.ENDC}\t\t\t{bcolors.OKBLACK}Total Gas Fees: {bcolors.ENDC}{bcolors.BURNTORANGE}{round(stat_tracker['gas_fees']['total'], 2)}{bcolors.ENDC}{bcolors.OKBLACK} USD{bcolors.ENDC}\n \
{bcolors.OKBLACK}Unclaimed Profit: {bcolors.ENDC}{bcolors.OKGREEN}{unclaimed_win['amount']}{bcolors.ENDC}{bcolors.OKBLACK} ETH{bcolors.ENDC} \
                ")
                continue
            elif user_input in ["m", "d"]:
                yolo_txn = build_transaction(wei_wager, user_input)
                if yolo_txn is not None:
                    txn_receipt = sign_and_send_transaction(yolo_txn)
                    txn_status = process_txn_receipt(txn_receipt)

                    if txn_status == 1:
                        if user_input == "m":
                            stat_tracker['moon']['entry_count'] += 1
                            stat_tracker['moon']['wagered'] += wager
                            latest_entry['position'].append("moon")
                            
                        elif user_input == "d":
                            stat_tracker['doom']['entry_count'] += 1
                            stat_tracker['doom']['wagered'] += wager
                            latest_entry['position'].append("doom")

                        latest_entry['wager'].append(wager)
                        latest_entry['epoch'].append(get_current_yolo_epoch())
                else:
                    print("Error building transaction. Please try again.")
                    continue
            else:
                print(f"\nInvalid input: {user_input}. Please enter a valid option.")
                continue
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)


def build_transaction(wei_wager, user_input):
    if user_input == "m":
        yolo_txn = mod_contract.functions.enterMoon(
            mod_contract.functions.currentEpoch().call()
        ).build_transaction({
            'from': account.address,
            'value': wei_wager,
            'gas': 0,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address)
        })
        gas = web3.eth.estimate_gas(yolo_txn)
        yolo_txn.update({'gas': gas})
        return yolo_txn
    elif user_input == "d":
        yolo_txn = mod_contract.functions.enterDoom(
            mod_contract.functions.currentEpoch().call()
        ).build_transaction({
            'from': account.address,
            'value': wei_wager,
            'gas': 0,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address)
        })
        gas = web3.eth.estimate_gas(yolo_txn)
        yolo_txn.update({'gas': gas})
        return yolo_txn


def sign_and_send_transaction(yolo_txn):
    try:
        signed_txn = account.sign_transaction(yolo_txn)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
        return txn_receipt
    except Exception as e:
        print(f"Error signing and sending transaction: {e}")
        return None


def process_txn_receipt(txn_receipt):
    parsed_receipt = receipt_to_dict(txn_receipt)
    if parsed_receipt['status'] == 1:
        gas_fee_usd = round(float(get_eth_to_usd_rate() * float(web3.from_wei(int(parsed_receipt['l1Fee'], 16), 'ether'))), 2)
        print(f"Txn successful: {parsed_receipt['transactionHash']} || Gas Fee: {gas_fee_usd}")
        stat_tracker['gas_fees']['total'] += gas_fee_usd
        return parsed_receipt['status']
    else:
        print(f"Txn failed: {parsed_receipt['transactionHash']} || Either an error occurred or it was too late to enter this round.")
        return parsed_receipt['status']


def get_current_yolo_epoch():
    current_yolo_epoch = mod_contract.functions.currentEpoch().call()
    return current_yolo_epoch


def get_gas_estimate(wei_wager):
    try:
        gas_estimate = mod_contract.functions.enterMoon(
            wei_wager
        ).estimate_gas({
            'from': account.address,
            'value': wei_wager,
        })
        return gas_estimate
    except Exception as e:
        print(f"Error getting gas estimate: {e}")
        return 0

def get_eth_to_usd_rate():
    url = f"https://api.thruster.finance/token/price?tokenAddress={WETH_ADDRESS}&chainId=81457"

    try:
        response = requests.get(url).json()
        return response['price']
    except Exception as e:
        return last_known_prices['eth']


def receipt_to_dict(txn_receipt):
    # convert any 'AttributeDict' type found to 'dict'
    parsedDict = dict(txn_receipt)
    for key, val in parsedDict.items():
        if 'list' in str(type(val)):
            parsedDict[key] = [_parse_value(x) for x in val]
        else:
            parsedDict[key] = _parse_value(val)
    return parsedDict


def _parse_value(val):
    # check for nested dict structures to iterate through
    if 'dict' in str(type(val)).lower():
        return receipt_to_dict(val)
    # convert 'HexBytes' type to 'str'
    elif 'HexBytes' in str(type(val)):
        return val.hex()
    else:
        return val
    

def check_for_win():
    query = {"query":"\n    query MoDRounds($filter: MoDFilterInput!, $player: Address, $pagination: PaginationInput) {\n      modRounds(filter: $filter, pagination: $pagination) {\n        ...MoDRound\n      }\n    }\n    \n  fragment MoDRound on MoDRound {\n    id\n    onChainId\n    startedAt\n    lockedAt\n    closedAt\n    lockPrice\n    closePrice\n\n    totalAmount\n    moonAmount\n    moonPayoutRatio\n    doomAmount\n    doomPayoutRatio\n    status\n    result {\n      ...MoDRoundResult\n    }\n\n    setting {\n      ...MoDRoundSetting\n    }\n    entries(player: $player) {\n      ...MoDEntry\n    }\n  }\n  \n  fragment MoDRoundResult on MoDRoundResult {\n    result\n    payoutRatio\n  }\n\n  \n  fragment MoDRoundSetting on MoDRoundSetting {\n    minimumEnterAmount\n    roundIntervalSecs\n  }\n\n  \n  fragment MoDEntry on MoDEntry {\n    moonPosition\n    amount\n    payoutAmount\n  }\n\n\n  ","variables":{"filter":{"contract":"MOON_OR_DOOM_ETHUSD_V1_BLAST","status":["CANCELLED","CLOSED"]},"player":"0xA9D8963402f6575995B4c3e66f64583D890e6bbf","pagination":{"first":1}},"operationName":"MoDRounds"}
    response = requests.post("https://graphql.yologames.io/graphql", json=query).json()

    if 'data' in response:
        if 'modRounds' in response['data']:
            round_data = response['data']['modRounds'][0]
            if round_data['status'] == "CLOSED" and round_data['onChainId'] in latest_entry['epoch']:
                if round_data['result']['result'] == "MOON" and latest_entry['position'][0] == "moon":
                    stat_tracker['moon']['wins'] += 1
                    stat_tracker['moon']['win_percent'] = round((stat_tracker['moon']['wins'] / stat_tracker['moon']['entry_count']) * 100, 2)
                    stat_tracker['moon']['winnings'] += round(float(latest_entry['wager'][0]) * float(round_data['result']['payoutRatio']), 5) - float(latest_entry['wager'][0])
                    unclaimed_win['epochs'].append(round_data['onChainId'])
                    unclaimed_win['amount'] += round(float(latest_entry['wager'][0]) * float(round_data['result']['payoutRatio']), 5) - float(latest_entry['wager'][0])
                elif round_data['result']['result'] == "DOOM" and latest_entry['position'][0] == "moon":
                    stat_tracker['moon']['winnings'] -= float(latest_entry['wager'][0])
                elif round_data['result']['result'] == "DOOM" and latest_entry['position'][0] == "doom":
                    stat_tracker['doom']['wins'] += 1
                    stat_tracker['doom']['win_percent'] = round((stat_tracker['doom']['wins'] / stat_tracker['doom']['entry_count']) * 100, 2)
                    stat_tracker['doom']['winnings'] += round(float(latest_entry['wager'][0]) * float(round_data['result']['payoutRatio']), 5) - float(latest_entry['wager'][0])
                    unclaimed_win['epochs'].append(round_data['onChainId'])
                    unclaimed_win['amount'] += round(float(latest_entry['wager'][0]) * float(round_data['result']['payoutRatio']), 5) - float(latest_entry['wager'][0])
                elif round_data['result']['result'] == "MOON" and latest_entry['position'][0] == "doom":
                    stat_tracker['doom']['winnings'] -= float(latest_entry['wager'][0])

                stat_tracker['total']['entry_count'] = stat_tracker['moon']['entry_count'] + stat_tracker['doom']['entry_count']
                stat_tracker['total']['wins'] = stat_tracker['moon']['wins'] + stat_tracker['doom']['wins']
                stat_tracker['total']['win_percent'] = round((stat_tracker['total']['wins'] / stat_tracker['total']['entry_count']) * 100, 2)
                stat_tracker['total']['wagered'] = stat_tracker['moon']['wagered'] + stat_tracker['doom']['wagered']
                stat_tracker['total']['winnings'] = round(float(stat_tracker['moon']['winnings']) + float(stat_tracker['doom']['winnings']), 5)
                index_of_epoch = latest_entry['epoch'].index(round_data['onChainId'])
                latest_entry['epoch'].remove(round_data['onChainId'])
                del latest_entry['position'][index_of_epoch]
                del latest_entry['wager'][index_of_epoch]

def claim_winnings():
    if len(unclaimed_win['epochs']) == 0:
        print (f"{bcolors.OKYELLOW}No winnings to claim.{bcolors.ENDC}")
    else:
        claim_txn = mod_contract.functions.claim(
            unclaimed_win['epochs']
        ).build_transaction({
            'from': account.address,
            'gas': 0,
            'value': 0,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address)
        })
        gas = web3.eth.estimate_gas(claim_txn)
        claim_txn.update({'gas': gas})
        claim_receipt = sign_and_send_transaction(claim_txn)
        claim_status = process_txn_receipt(claim_receipt)

        if claim_status == 1:
            print(f"{bcolors.OKGREEN}Winnings claimed successfully!{bcolors.ENDC}")
            unclaimed_win['epochs'].clear()
            unclaimed_win['amount'] = 0
        else:
            print(f"{bcolors.FAIL}Error claiming winnings. Please try again.{bcolors.ENDC}")

def log_session_summary():
    epoch = int(time.time())
    file = open(f"../../logs/mod-summary-{epoch}.log", "w")
    file.write(dedent(f"\
        Session Duration: {(epoch - stat_tracker['start_epoch']) / 60:.2f}\n\n\
        Moon Entries: {stat_tracker['moon']['entry_count']}\n\
        Moon Wins: {stat_tracker['moon']['wins']}\n\
        Moon Win %: {stat_tracker['moon']['win_percent']:.2f}\n\
        Moon ETH Wagered: {stat_tracker['moon']['wagered']}\n\
        Moon Winnings: {stat_tracker['moon']['winnings']}\n\n\
        Doom Entries: {stat_tracker['doom']['entry_count']}\n\
        Doom Wins: {stat_tracker['doom']['wins']}\n\
        Doom Win %: {stat_tracker['doom']['win_percent']:.2f}\n\
        Doom ETH Wagered: {stat_tracker['doom']['wagered']}\n\
        Doom Winnings: {stat_tracker['doom']['winnings']}\n\n\
        Total Gas Fees: {stat_tracker['gas_fees']['total']}\n\
        Total Entries: {stat_tracker['total']['entry_count']}\n\
        Total Wins: {stat_tracker['total']['wins']}\n\
        Total Win %: {stat_tracker['total']['win_percent']:.2f}\n\
        Total ETH Wagered: {stat_tracker['total']['wagered']}\n\
        Total Winnings: {stat_tracker['total']['winnings']}\n\
    "))
    file.close()


def log_handler():
    log_session_summary()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    OKRED = '\033[31m'
    OKYELLOW = '\033[33m'
    OKBLACK = '\033[30m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BURNTORANGE = '\033[38;5;208m'


if __name__ == "__main__":
    atexit.register(log_handler)
    moon_or_doom()
