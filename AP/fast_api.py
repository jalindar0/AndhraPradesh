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

app = FastAPI(title="PDF Access API")

# =========================
# CONFIGURATION (RELATIVE)
# =========================

BASE_DIR = Path(__file__).resolve().parent

PDF_ROOT = BASE_DIR / "pdf_out"
DATA_FILE = BASE_DIR / "excel" / "Addateegala.xlsx"

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

guid_map = {}

for _, row in df.iterrows():
    guid_map[row["guid"]] = {
        "district": row["DistrictName"],
        "mandal": row["MandalName"],
        "village": row["VillageName"],
        "survey": str(row["Survey_No"])
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
    return {
        "status": "API running"
    }


@app.get("/pdf")
def get_pdf_by_guid(
    state: str = Query(...),
    guid: str = Query(...),
    api_key: str = Query(...)
):

    # Validate API key
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # Validate state
    if state.lower() != "andhrapradesh":
        raise HTTPException(status_code=403, detail="Invalid State")

    # Validate GUID
    if guid not in guid_map:
        raise HTTPException(status_code=404, detail="GUID not found")

    record = guid_map[guid]

    # Handle survey number formatting
    safe_survey = record["survey"].replace("/", "-")
    filename = f"{safe_survey}.pdf"

    file_path = safe_path(
        PDF_ROOT,
        record["district"],
        record["mandal"],
        record["village"],
        filename
    )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )
