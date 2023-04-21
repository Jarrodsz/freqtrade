import ccxt
import json
import os
import shutil
from termcolor import colored
from tqdm import tqdm

DEFAULT_EXCHANGE = 'kucoin'
DEFAULT_MARKET = 'USDT'
DEFAULT_THRESHOLD = 0.001
DEFAULT_NUM_COINS = 250


def load_blacklist_pairs(exchange: str = DEFAULT_EXCHANGE) -> list:
    # Load and parse the blacklist pairs
    blacklist_file_path = f"./user_data/config/pairs/_{exchange.lower()}-blacklist.json"
    try:
        with open(blacklist_file_path, 'r') as f:
            blacklist = json.load(f)
            pair_blacklist = blacklist['exchange']['pair_blacklist']
            parsed_pairs = []
            for pair in pair_blacklist:
                pair = pair.strip('/')
                pair = pair.replace('*', '.*')
                parsed_pairs.append(pair)
            return parsed_pairs
    except json.JSONDecodeError as e:
        print(f"Error: {e.msg} in {blacklist_file_path} at line {e.lineno} column {e.colno}")
        exit(1)


def fetch_valid_pairs(exchange: str = DEFAULT_EXCHANGE,
                      market: str = DEFAULT_MARKET,
                      spread_threshold: float = DEFAULT_THRESHOLD,
                      num_coins: int = DEFAULT_NUM_COINS) -> list:
    # Get the valid pairs based on the parameters
    blacklist_pairs = load_blacklist_pairs(exchange)
    exchange_instance = getattr(ccxt, exchange.lower())()
    tickers = exchange_instance.fetch_tickers()
    valid_pairs = []
    for symbol, ticker in tqdm(tickers.items()):
        if not symbol.endswith(f'/{market}'):
            continue
        if symbol in blacklist_pairs:
            continue
        try:
            ticker = exchange_instance.fetch_ticker(symbol)
        except ccxt.BadSymbol:
            continue
        bid = float(ticker.get('bid', 0))
        ask = float(ticker.get('ask', 0))
        if bid == 0 or ask == 0:
            continue
        spread = (ask - bid) / bid
        if spread > spread_threshold:
            valid_pairs.append((symbol, spread))
    valid_pairs = sorted(valid_pairs, key=lambda x: float(x[1]), reverse=True)[:num_coins]
    return valid_pairs


def update_whitelist_pairs(exchange: str = DEFAULT_EXCHANGE,
                           valid_pairs: list = []) -> None:
    # Update the exchange configuration file with the valid pairs
    pair_whitelist = [f"{pair[0]}" for pair in valid_pairs]
    pair_whitelist_count = len(pair_whitelist)
    config_file_path = f"./user_data/config/pairs/_{exchange.lower()}-default.json"
    print(f"Number of pairs in whitelist: {pair_whitelist_count}")
    user_input = input("Press key to continue")
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            config = json.load(f)
            if 'exchange' in config and 'pair_whitelist' in config['exchange']:
                existing_pair_whitelist = config['exchange']['pair_whitelist']
            else:
                existing_pair_whitelist = []
    else:
        existing_pair_whitelist = []
    removed_pairs = set(existing_pair_whitelist) - set(pair_whitelist)
    new_pairs = set(pair_whitelist) - set(existing_pair_whitelist)
    print("\nUpdated Pair Whitelist:")
    for i, pair in enumerate(pair_whitelist):
        if pair in removed_pairs:
            print(colored(f"- {pair}", "red"))
        elif pair in new_pairs:
            print(colored(f"+ {pair}", "green"))
        else:
            print(f"{i + 1}. {pair}")
    # Prompt user before overwriting the config file
    if os.path.isfile(config_file_path):
        overwrite = input("Do you want to overwrite the existing config file? (y/n) ").lower().strip()
        if overwrite != "y":
            return

    # add a file backup feature
    bak_file_path = f"{config_file_path}.bak"
    if os.path.isfile(bak_file_path):
        bak_num = 1
        while True:
            bak_num += 1
            new_bak_file_path = f"{bak_file_path}{bak_num}"
            if not os.path.isfile(new_bak_file_path):
                bak_file_path = new_bak_file_path
                break
        shutil.copy(config_file_path, bak_file_path)
    else:
        shutil.copy(config_file_path, bak_file_path)

    # write the new json file
    with open(config_file_path, 'w') as f:
        config = {
            "exchange": {
                "pair_whitelist": pair_whitelist
            }
        }
        json.dump(config, f, indent=2)


def pairlist():
    blacklist_pairs = load_blacklist_pairs()
    valid_pairs = fetch_valid_pairs()
    update_whitelist_pairs(valid_pairs=valid_pairs)

