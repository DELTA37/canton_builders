import os
import dotenv

dotenv.load_dotenv()

LEDGER_URL = os.environ.get("LEDGER_URL")
print(LEDGER_URL)