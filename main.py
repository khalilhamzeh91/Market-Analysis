"""
AI Market Analysis Bot
======================
Scans multiple symbols, runs Claude deep analysis on top opportunities,
analyses open positions and trade history, and generates an HTML report.

Usage:
    python main.py              # run once
    python main.py --loop       # run every 15 minutes continuously
"""

import sys
import time
import argparse

import config
import github_publisher
import mt5_connector
import data_fetcher
import scanner
import symbol_analyzer
import portfolio_analyzer
import report_builder


def run_once():
    print("\n" + "=" * 50)
    print(" AI Market Analysis Bot")
    print("=" * 50)

    # 1. Connect
    if not mt5_connector.initialize():
        print("ERROR: Could not connect to MetaTrader5.")
        return False

    account = mt5_connector.get_account_info()

    try:
        # 2. Scan all symbols
        print(f"\n[1/4] Scanning {len(config.SYMBOLS)} symbols...")
        scanner_results = scanner.scan_all_symbols()
        if not scanner_results:
            print("  WARNING: No symbols returned data. Check MT5 connection and symbol names.")
        else:
            print(f"  Top opportunity: {scanner_results[0]['symbol']} (score {scanner_results[0]['score']}/100)")

        # 3. Deep analysis on top symbols
        print(f"\n[2/4] Deep analysis on top {config.TOP_SYMBOLS_FOR_DEEP_ANALYSIS} symbols (Claude AI)...")
        analyses = symbol_analyzer.analyze_top_symbols(
            scanner_results,
            top_n=config.TOP_SYMBOLS_FOR_DEEP_ANALYSIS
        )

        # 4. Portfolio
        print("\n[3/4] Analysing portfolio...")
        positions_df = data_fetcher.fetch_open_positions()
        history_df   = data_fetcher.fetch_trade_history(days_back=config.HISTORY_DAYS)

        n_pos = len(positions_df)
        n_his = len(history_df)
        print(f"  Open positions: {n_pos} | Closed trades (90d): {n_his}")

        portfolio = portfolio_analyzer.analyze_open_positions(positions_df, account)
        history   = portfolio_analyzer.analyze_trade_history(history_df)

        # 5. Build report
        print("\n[4/4] Building HTML report...")
        html = report_builder.build_report(account, scanner_results, analyses, portfolio, history)

        import os
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        with open(config.REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"\n  Report saved: {config.REPORT_FILE}")

        # Publish to GitHub Pages
        print("\n  Publishing to GitHub...")
        github_publisher.publish()

        return True

    except Exception as e:
        print(f"\nERROR during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        mt5_connector.shutdown()


def main():
    parser = argparse.ArgumentParser(description="AI Market Analysis Bot")
    parser.add_argument("--loop", action="store_true",
                        help="Run continuously every 15 minutes")
    parser.add_argument("--interval", type=int, default=3,
                        help="Loop interval in minutes (default: 3)")
    args = parser.parse_args()

    if args.loop:
        print(f"Loop mode: running every {args.interval} minutes. Press Ctrl+C to stop.")
        try:
            while True:
                run_once()
                print(f"\nNext run in {args.interval} minutes...\n")
                time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            print("\nBot stopped.")
    else:
        success = run_once()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
