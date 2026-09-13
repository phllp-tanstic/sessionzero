from __future__ import annotations

import argparse
import json

from sessionzero_bitget import BitgetMarketClient, BitgetProviderError, BitgetReferenceDataProvider
from sessionzero_config import get_settings
from sqlalchemy.exc import SQLAlchemyError

from .engine import create_database_engine, verify_database_connection
from .persistence import ingest_reference_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Read public Bitget Reality reference metadata")
    parser.add_argument("--symbol")
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    engine = None
    try:
        with BitgetMarketClient(
            base_url=str(settings.bitget_base_url),
            timeout_seconds=settings.bitget_timeout_seconds,
            max_retries=settings.bitget_max_retries,
        ) as client:
            online = sorted(
                (item for item in client.get_reality_instruments() if item.status == "online"),
                key=lambda item: item.symbol,
            )
            if not online:
                raise ValueError("no online Reality instrument discovered")
            symbol = args.symbol.upper() if args.symbol else online[0].symbol
            if symbol not in {item.symbol for item in online}:
                raise ValueError(
                    "symbol is not an online Reality instrument discovered from Bitget"
                )
            bundle = BitgetReferenceDataProvider(client).get_reference_bundle(symbol)
        persistence = None
        if args.persist:
            engine = create_database_engine(settings.require_database_url())
            verify_database_connection(engine)
            persistence = ingest_reference_bundle(engine, bundle)
        output = {
            "mapping": bundle.mapping.model_dump(mode="json"),
            "dividends": [item.model_dump(mode="json") for item in bundle.dividends],
            "splits": [item.model_dump(mode="json") for item in bundle.splits],
            "share_changes": [item.model_dump(mode="json") for item in bundle.share_changes],
            "suspensions": [item.model_dump(mode="json") for item in bundle.suspensions],
            "source_session_metadata": bundle.source_session_metadata.model_dump(mode="json"),
            "raw_response_count": len(bundle.raw_responses),
            "persistence": (
                {
                    "run_id": str(persistence.run_id),
                    "records_received": persistence.records_received,
                    "raw_records_written": persistence.raw_records_written,
                    "normalized_records_written": persistence.normalized_records_written,
                }
                if persistence is not None
                else None
            ),
        }
        print(json.dumps(output, indent=2, sort_keys=True))
    except (BitgetProviderError, SQLAlchemyError, ValueError) as exc:
        print(json.dumps({"error": {"code": "REFERENCE_INGESTION_FAILED", "message": str(exc)}}))
        raise SystemExit(1) from exc
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
