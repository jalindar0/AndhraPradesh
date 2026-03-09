from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd
import os
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================

load_dotenv()

app = FastAPI(title="Tamil Nadu PDF Access API")

# =========================
# CONFIGURATION (RELATIVE)
# =========================

BASE_DIR = Path(__file__).resolve().parent

PDF_ROOT  = BASE_DIR / "out"
DATA_FILE = BASE_DIR / "Magananthapuram_Master.xlsx"

API_KEY = os.getenv("API_KEY")

# =========================
# MIDDLEWARE
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# LOAD DATA ON STARTUP
# =========================

if not DATA_FILE.exists():
    raise Exception(f"Excel file not found: {DATA_FILE}")

df = pd.read_excel(DATA_FILE)
df = df.fillna("")

guid_map = {}

for _, row in df.iterrows():
    guid = str(row["guid"]).strip()
    if guid and guid not in guid_map:
        guid_map[guid] = {
            "district": str(row["dtname"]).strip(),
            "taluk":    str(row["taluk_tamil_name"]).strip(),
            "village":  str(row["village_tamil_name"]).strip(),
            "patta_no": str(row["patta_no"]).strip(),
        }

print(f"Loaded {len(guid_map)} GUID records")

# =========================
# UTIL
# =========================

def safe_path(base: Path, *paths: str) -> Path:
    full_path = base.joinpath(*paths).resolve()
    if not str(full_path).startswith(str(base.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return full_path

# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return {"status": "TN PDF API running"}


@app.get("/pdf")
def get_pdf_by_guid(
    state:   str = Query(...),
    guid:    str = Query(...),
    api_key: str = Query(...)
):
    # Validate API key
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # Validate state
    if state.lower() != "tamilnadu":
        raise HTTPException(status_code=403, detail="Invalid State")

    # Validate GUID
    if guid not in guid_map:
        raise HTTPException(status_code=404, detail="GUID not found")

    record   = guid_map[guid]
    filename = f"{record['patta_no']}.pdf"

    file_path = safe_path(
        PDF_ROOT,
        record["district"],
        record["taluk"],
        record["village"],
        filename,
    )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
    )