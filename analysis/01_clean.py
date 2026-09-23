"""
Stage 1: Data loading & cleaning
Dataset: NYC DOHMH Restaurant Inspection Results (1,000-row extract)
"""
import pandas as pd
import numpy as np

RAW = "/workspaces/nyc-restaurant-inspection-analysis/uploads/43nn-pn8j.csv"
OUT = "/workspaces/nyc-restaurant-inspection-analysis/analysis_output"

log = []

def logit(msg):
    log.append(msg)
    print(msg)

# ------------------------------------------------------------------ load
df = pd.read_csv(RAW, dtype=str, keep_default_na=False, na_values=[""])
logit(f"RAW SHAPE: {df.shape[0]} rows x {df.shape[1]} cols")
logit(f"COLUMNS: {list(df.columns)}")

# ------------------------------------------------------------------ strip whitespace everywhere
for c in df.columns:
    df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan})

# ------------------------------------------------------------------ sentinel / placeholder values
# NYC DOHMH uses 1900-01-01 inspection_date for establishments not yet inspected
n_sentinel = (df["inspection_date"] == "1900-01-01T00:00:00.000").sum()
logit(f"\nSENTINEL inspection_date=1900-01-01 (not yet inspected): {n_sentinel} rows")
df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
df.loc[df["inspection_date"] == pd.Timestamp("1900-01-01"), "inspection_date"] = pd.NaT
df["grade_date"] = pd.to_datetime(df["grade_date"], errors="coerce")
df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")

# "N/A" placeholders in address fields
for c in ["zipcode", "building", "street", "boro"]:
    n = df[c].isin(["N/A", "0", "Missing", "MISSING"]).sum()
    if n:
        logit(f"Placeholder 'N/A'/'0' in {c}: {n}")
    df[c] = df[c].replace({"N/A": np.nan, "Missing": np.nan, "MISSING": np.nan})

# ------------------------------------------------------------------ numeric conversions
for c in ["score", "latitude", "longitude", "zipcode"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# lat/long of 0,0 are placeholders (Gulf of Guinea) -> NaN
bad_geo = ((df["latitude"] == 0) & (df["longitude"] == 0)) | df["latitude"].isna()
logit(f"Invalid/missing (0,0) geocoordinates: {bad_geo.sum()}")
df.loc[(df["latitude"] == 0) & (df["longitude"] == 0), ["latitude", "longitude"]] = np.nan

# basic plausibility bounds for NYC
in_nyc = df["latitude"].between(40.4, 41.0) & df["longitude"].between(-74.3, -73.6)
n_out = (~in_nyc & df["latitude"].notna()).sum()
logit(f"Coordinates outside NYC bounding box: {n_out}")

# ------------------------------------------------------------------ categorical standardisation
df["boro"] = df["boro"].str.title()
df["boro"] = df["boro"].replace({"0": np.nan})
logit(f"Boro values: {df['boro'].value_counts(dropna=False).to_dict()}")

df["critical_flag"] = df["critical_flag"].str.strip()
# normalize grade: keep only valid grades
valid_grades = {"A", "B", "C", "Z", "P", "N"}
n_bad_grade = (~df["grade"].isin(valid_grades) & df["grade"].notna()).sum()
logit(f"Unexpected grade values: {n_bad_grade} ({df.loc[~df['grade'].isin(valid_grades) & df['grade'].notna(),'grade'].unique()})")

# cuisine missing -> 'Unknown'
df["cuisine_description"] = df["cuisine_description"].fillna("Unknown")

# phone contains artifacts (e.g. trailing underscore); extract digits
df["phone"] = df["phone"].astype(str).str.replace(r"\D", "", regex=True).replace({"": np.nan, "nan": np.nan})

# ------------------------------------------------------------------ duplicates
n_exact = df.duplicated().sum()
logit(f"\nExact duplicate rows: {n_exact}")
df = df.drop_duplicates().copy()

# duplicates at inspection-violation grain
key = ["camis", "inspection_date", "violation_code"]
n_kv = df.duplicated(subset=key).sum()
logit(f"Duplicate (camis, inspection_date, violation_code) rows: {n_kv}")

# ------------------------------------------------------------------ derived fields
df["inspection_year"] = df["inspection_date"].dt.year
df["has_critical_violation"] = (df["critical_flag"] == "Critical")
df["violations_cited"] = df["action"].str.contains("Violations were cited", na=False)

# inspection-level frame: one row per (camis, inspection_date) inspection
insp = (
    df[df["inspection_date"].notna()]
    .groupby(["camis", "inspection_date"], as_index=False)
    .agg(
        dba=("dba", "first"),
        boro=("boro", "first"),
        cuisine=("cuisine_description", "first"),
        zipcode=("zipcode", "first"),
        score=("score", "max"),          # score is repeated per inspection; max is safe
        grade=("grade", "first"),
        action=("action", "first"),
        inspection_type=("inspection_type", "first"),
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
        n_violations=("violation_code", lambda s: s.notna().sum()),
        n_critical=("has_critical_violation", "sum"),
        year=("inspection_year", "first"),
    )
)
logit(f"\nINSPECTION-LEVEL FRAME: {insp.shape[0]} unique inspections of {insp['camis'].nunique()} establishments")
logit(f"Date range of inspections: {insp['inspection_date'].min()} -> {insp['inspection_date'].max()}")
logit(f"Inspections with numeric score: {insp['score'].notna().sum()}")

# ------------------------------------------------------------------ missingness summary
miss = df.isna().mean().sort_values(ascending=False) * 100
logit("\nMISSINGNESS (violation-level, % of rows):")
logit(miss[miss > 0].round(1).to_string())

# ------------------------------------------------------------------ save
df.to_csv(f"{OUT}/cleaned_violations.csv", index=False)
insp.to_csv(f"{OUT}/cleaned_inspections.csv", index=False)
logit(f"\nSaved: cleaned_violations.csv ({df.shape}), cleaned_inspections.csv ({insp.shape})")

with open(f"{OUT}/cleaning_log.txt", "w") as f:
    f.write("\n".join(str(m) for m in log))
