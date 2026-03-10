const express = require("express");
const cors = require("cors");
const path = require("path");
const fs = require("fs");
const XLSX = require("xlsx");
require("dotenv").config();

const app = express();
const PORT = 8000;

app.use(cors());

// ======================
// PATH CONFIG
// ======================

const BASE_DIR = __dirname;
const PDF_ROOT = path.join(BASE_DIR, "out");
const DATA_FILE = path.join(BASE_DIR, "Magananthapuram_Master.xlsx");

const API_KEY = process.env.API_KEY || "123456";

// ======================
// HELPER FUNCTIONS
// ======================

function normalize(text) {
    return String(text || "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, " ");
}

function findFolder(parent, target) {

    if (!fs.existsSync(parent)) return null;

    const folders = fs.readdirSync(parent);

    return folders.find(f => normalize(f) === normalize(target));
}

// ======================
// LOAD EXCEL DATA
// ======================

if (!fs.existsSync(DATA_FILE)) {
    console.error("Excel file missing:", DATA_FILE);
    process.exit(1);
}

const workbook = XLSX.readFile(DATA_FILE);
const sheet = workbook.Sheets[workbook.SheetNames[0]];
const rows = XLSX.utils.sheet_to_json(sheet);

let ouidMap = {};

rows.forEach(row => {

    const ouid = String(row.guid || "").trim();

    if (!ouid) return;

    ouidMap[ouid] = {
        district: row.dname,
        taluk: row.taluk_english_name,
        village: row.village_english_name,
        patta: String(row.patta_no || "").trim()
    };

});

console.log("OUID loaded:", Object.keys(ouidMap).length);

// ======================
// ROOT ROUTE
// ======================

app.get("/", (req, res) => {
    res.json({
        status: "Tamil Nadu PDF API running",
        total_ouid: Object.keys(ouidMap).length
    });
});

// ======================
// PDF API
// ======================

app.get("/pdf", (req, res) => {

    try {

        const { state, ouid, api_key } = req.query;

        if (api_key !== API_KEY) {
            return res.status(401).json({ error: "Invalid API Key" });
        }

        if (!state || state.toLowerCase() !== "tamilnadu") {
            return res.status(403).json({ error: "Invalid State" });
        }

        if (!ouidMap[ouid]) {
            return res.status(404).json({ error: "OUID not found" });
        }

        const record = ouidMap[ouid];

        // ===== FIND DISTRICT =====

        const districtFolder = findFolder(PDF_ROOT, record.district);

        if (!districtFolder) {
            return res.status(404).json({
                error: "District folder not found",
                expected: record.district
            });
        }

        const districtPath = path.join(PDF_ROOT, districtFolder);

        // ===== FIND TALUK =====

        const talukFolder = findFolder(districtPath, record.taluk);

        if (!talukFolder) {
            return res.status(404).json({
                error: "Taluk folder not found",
                expected: record.taluk
            });
        }

        const talukPath = path.join(districtPath, talukFolder);

        // ===== FIND VILLAGE =====

        const villageFolder = findFolder(talukPath, record.village);

        if (!villageFolder) {
            return res.status(404).json({
                error: "Village folder not found",
                expected: record.village
            });
        }

        const villagePath = path.join(talukPath, villageFolder);

        // ===== FIND PDF =====

        const files = fs.readdirSync(villagePath);

        let pdfFile = files.find(f =>
            normalize(f).startsWith(normalize(record.patta)) &&
            f.toLowerCase().endsWith(".pdf")
        );

        // numeric fix (721 -> 721.0.pdf)
        if (!pdfFile) {

            const pattaNum = parseFloat(record.patta);

            if (!isNaN(pattaNum)) {

                pdfFile = files.find(f =>
                    normalize(f).startsWith(normalize(pattaNum.toFixed(1)))
                );

            }

        }

        if (!pdfFile) {
            return res.status(404).json({
                error: "PDF file not found",
                patta_no: record.patta
            });
        }

        const pdfPath = path.join(villagePath, pdfFile);

        console.log("Serving:", pdfPath);

        res.sendFile(pdfPath);

    } catch (err) {

        console.error("Server error:", err);

        res.status(500).json({
            error: "Internal Server Error"
        });

    }

});

// ======================
// START SERVER
// ======================

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});