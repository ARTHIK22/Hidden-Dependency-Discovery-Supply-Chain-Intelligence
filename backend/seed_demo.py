"""Seed the configured development database with explicitly labeled fixtures."""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_engine
from app.demo_data import seed_demo_data


def main() -> None:
    if not settings.development_demo_mode:
        raise SystemExit("Set DEMO_MODE=true in a development environment before seeding demo data")
    with Session(get_engine()) as db:
        investigation = seed_demo_data(db)
    print(f"Demo fixtures are ready for investigation {investigation.id}.")
    print("All entities, risks, alerts, and evidence are labeled DEMO and are not verified facts.")


if __name__ == "__main__":
    main()
