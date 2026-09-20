"""Build or restore the accepted Phase 1 dataset without manually supplied identity hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config
from sessionzero_bitget import BitgetMarketClient, BitgetReferenceDataProvider
from sessionzero_config import get_settings
from sessionzero_market_data.native import NativeDataError

from .dataset import materialize, persist_manifest
from .dataset_artifacts import (
    ARCHIVES,
    METADATA,
    calendar_artifact,
    digest,
    load_cohort,
    write_json,
)
from .dataset_fetch import collect
from .engine import create_database_engine
from .native_cohort import reverify_native_cohort


def replay_mapping(cohort, archive_dir: Path) -> None:
    """Offline replay through the accepted Bitget parser; no new historical retrieval claim."""
    raw = json.loads((archive_dir / "mapping.json").read_text())
    responses = {(r["endpoint"], tuple(sorted(r["params"].items()))): r for r in raw}

    def respond(request):
        key = (request.url.path, tuple(sorted(dict(request.url.params).items())))
        if key not in responses:
            raise NativeDataError("MAPPING_ARCHIVE_INCOMPLETE")
        return httpx.Response(200, json=responses[key]["payload"])

    with BitgetMarketClient(transport=httpx.MockTransport(respond)) as client:
        verified, _ = reverify_native_cohort(
            BitgetReferenceDataProvider(client, minimum_reality_request_interval=0),
            evidence_id=cohort.members[0].source_session_evidence_ids[0],
            original_universe_version=cohort.universe_version,
            expected_cohort_version=cohort.cohort_version,
        )
    if verified != cohort:
        raise NativeDataError("ARCHIVED_MAPPING_COHORT_MISMATCH")


def source_provenance() -> dict:
    paths = sorted(Path("packages").rglob("*.py"))
    paths += sorted(Path("migrations").rglob("*.py"))
    paths += [Path("pyproject.toml")]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return {
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_code_version": digest(hashes),
        "source_file_hashes": hashes,
        "git_commit_semantics": "BUILD_BASE_COMMIT; source_file_hashes identify exact build code",
    }


def archive_index(archive_dir: Path, cohort) -> dict:
    names = [f"{leg}-{m.symbol}.json" for m in cohort.members for leg in ("native", "reality")]
    names += ["mapping.json", "collection.json", "reality-telemetry.json"]
    return {
        name: hashlib.sha256((archive_dir / name).read_bytes()).hexdigest()
        for name in sorted(names)
    }


def check_archives(manifest: dict, archive_dir: Path) -> None:
    for name, expected in manifest["archives"]["sha256"].items():
        if Path(name).name != name:
            raise NativeDataError("INVALID_ARCHIVE_PATH")
        if hashlib.sha256((archive_dir / name).read_bytes()).hexdigest() != expected:
            raise NativeDataError("PRIVATE_ARCHIVE_CHECKSUM_MISMATCH")


def build(
    *, restore: bool = False, archive_dir: Path | None = None, manifest_path: Path | None = None
) -> dict:
    cohort = load_cohort()
    calendar = json.loads((METADATA / "calendar.json").read_text())
    if calendar != calendar_artifact(cohort):
        raise NativeDataError("PINNED_CALENDAR_MISMATCH")
    original = None
    if restore:
        if manifest_path is None:
            latest = json.loads((METADATA / "latest.json").read_text())
            manifest_path = METADATA / f"{latest['dataset_version']}.json"
        original = json.loads(manifest_path.read_text())
        if original["dataset_version"] != digest(original["identity"]):
            raise NativeDataError("DATASET_MANIFEST_HASH_MISMATCH")
        archive_dir = archive_dir or ARCHIVES / original["archives"]["directory"]
        check_archives(original, archive_dir)
        code = {
            k: original["identity"][k]
            for k in (
                "git_commit",
                "source_code_version",
                "source_file_hashes",
                "git_commit_semantics",
            )
        }
        current = source_provenance()
        if current["source_code_version"] != code["source_code_version"]:
            raise NativeDataError("RESTORE_SOURCE_CODE_VERSION_MISMATCH")
    else:
        archive_dir = archive_dir or ARCHIVES / datetime.now(UTC).strftime("build-%Y%m%dT%H%M%SZ")
        collect(cohort, calendar, archive_dir)
        code = source_provenance()
    replay_mapping(cohort, archive_dir)
    # The build owns schema setup, so the advertised command also works on a fresh database.
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_database_engine(get_settings().require_database_url())
    try:
        manifest, targets, reality = materialize(
            engine, cohort, calendar, archive_dir, code_provenance=code
        )
        if original is not None:
            if manifest["dataset_version"] != original["dataset_version"]:
                raise NativeDataError(
                    "RESTORED_DATASET_VERSION_MISMATCH",
                    details={
                        "expected": original["dataset_version"],
                        "recomputed": manifest["dataset_version"],
                    },
                )
            manifest = original
        else:
            manifest["archives"] = {
                "directory": archive_dir.name,
                "sha256": archive_index(archive_dir, cohort),
                "access": "PRIVATE_LOCAL_ONLY",
                "root": str(ARCHIVES),
            }
            manifest["cohort_artifact"] = {
                "path": str(METADATA / "cohort.json"),
                "sha256": hashlib.sha256((METADATA / "cohort.json").read_bytes()).hexdigest(),
            }
            manifest["calendar_artifact"] = str(METADATA / "calendar.json")
            manifest["collection"] = json.loads((archive_dir / "collection.json").read_text())
            manifest["reality_telemetry"] = json.loads(
                (archive_dir / "reality-telemetry.json").read_text()
            )
        persist_manifest(engine, manifest, targets, reality)
        if not restore:
            write_json(METADATA / f"{manifest['dataset_version']}.json", manifest)
            write_json(METADATA / "latest.json", {"dataset_version": manifest["dataset_version"]})
        return manifest
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Reproduce exact version from private archives; no provider calls",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help="Resume a collection directory or locate retained private archives",
    )
    parser.add_argument(
        "--manifest", type=Path, help="Restore this manifest; defaults to tracked latest.json"
    )
    args = parser.parse_args()
    try:
        manifest = build(
            restore=args.restore, archive_dir=args.archive_dir, manifest_path=args.manifest
        )
        print(
            json.dumps(
                {
                    "dataset_version": manifest["dataset_version"],
                    "phase1_exit": manifest["phase1_exit"],
                    "restored": args.restore,
                    "target_pairs": manifest["summary"]["all_target_pairs"],
                    "reality_rows": manifest["summary"]["reality_rows"],
                }
            )
        )
        if manifest["phase1_exit"] != "YES":
            raise SystemExit(1)
    except Exception as exc:
        # No provider body, credentials, DB connection string or exception repr reaches stdout.
        print(
            json.dumps(
                {
                    "phase1_exit": "NO",
                    "error": exc.code
                    if isinstance(exc, NativeDataError)
                    else "DATASET_CONFIGURATION_OR_STORAGE_FAILURE",
                    "details": exc.details if isinstance(exc, NativeDataError) else {},
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
