"""
Snaglist Pro — CLI / Web entry point.

Usage:
    python -m snaglist_pro --zip <whatsapp_zip> --checklist <checklist_xlsx> --output <output_dir>
    python -m snaglist_pro --web
"""

import argparse
import sys
from pathlib import Path

from snaglist_pro.config import settings
from snaglist_pro.database import init_db
from snaglist_pro.pipeline import SnaglistPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Snaglist Pro — Process WhatsApp chat ZIP into formatted snaglist Excel."
    )
    parser.add_argument("--zip", default=None, help="Path to WhatsApp chat export ZIP")
    parser.add_argument("--checklist", default="C:\\Users\\vinee\\Downloads\\Untitled spreadsheet (2).xlsx", help="Path to checklist XLSX")
    parser.add_argument("--output", default="./output", help="Output directory (default: ./output)")
    parser.add_argument("--project", default=None, help="Project name (optional)")
    parser.add_argument("--web", action="store_true", help="Launch web UI (Flask)")
    parser.add_argument("--port", type=int, default=5000, help="Web UI port (default: 5000)")
    args = parser.parse_args()

    if args.web:
        from snaglist_pro.web.app import app
        init_db()
        app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)
        return

    if not args.zip:
        parser.print_help()
        sys.exit(1)

    zip_path = Path(args.zip)
    checklist_path = Path(args.checklist)
    output_dir = Path(args.output)

    if not zip_path.exists():
        print(f"ERROR: ZIP not found: {zip_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    init_db()
    pipeline = SnaglistPipeline()

    result = pipeline.run(
        zip_path=str(zip_path),
        checklist_path=str(checklist_path),
        output_dir=str(output_dir),
        project_name=args.project,
    )
    print(f"\nDone. Output directory: {output_dir.resolve()}")
    print(f"  Master file: {result['excel_path']}")


if __name__ == "__main__":
    main()
