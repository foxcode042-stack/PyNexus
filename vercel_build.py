import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if os.environ.get("VERCEL") == "1" and not os.environ.get(
        "DATABASE_URL", ""
    ).strip():
        raise SystemExit(
            "Set DATABASE_URL to a persistent PostgreSQL database in Vercel "
            "before deploying. Vercel function storage is not a persistent database."
        )

    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("manage.py")), "migrate", "--noinput"],
        check=True,
    )


if __name__ == "__main__":
    main()
