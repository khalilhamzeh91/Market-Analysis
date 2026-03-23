import MetaTrader5 as mt5


def initialize() -> bool:
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return False
    info = mt5.account_info()
    print(f"Connected | Login: {info.login} | Balance: ${info.balance:.2f} | Server: {info.server}")
    return True


def get_account_info() -> dict:
    info = mt5.account_info()
    if info is None:
        return {}
    return {
        "login":        info.login,
        "balance":      info.balance,
        "equity":       info.equity,
        "margin":       info.margin,
        "free_margin":  info.margin_free,
        "margin_level": info.margin_level,
        "currency":     info.currency,
        "server":       info.server,
        "leverage":     info.leverage,
    }


def shutdown():
    mt5.shutdown()
    print("MT5 disconnected.")
