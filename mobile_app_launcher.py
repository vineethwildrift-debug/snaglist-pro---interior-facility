import os
import sys

from mobile_app import create_mobile_app


if __name__ == "__main__":
    host = os.environ.get("SNAGLIST_MOBILE_HOST", "0.0.0.0")
    port = int(os.environ.get("SNAGLIST_MOBILE_PORT", "5000"))
    app = create_mobile_app()
    app.run(host=host, port=port, debug=False)
