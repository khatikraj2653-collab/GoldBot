import io
import zipfile
import requests
import pandas as pd

GKG_COLUMNS = [
    "GKGRECORDID", "DATE", "SourceCollectionIdentifier", "SourceCommonName",
    "DocumentIdentifier", "Counts", "V2Counts", "Themes", "V2Themes",
    "Locations", "V2Locations", "Persons", "V2Persons", "Organizations",
    "V2Organizations", "V2Tone", "Dates", "GCAM", "SharingImage",
    "RelatedImages", "SocialImageEmbeds", "SocialVideoEmbeds", "Quotations",
    "AllNames", "Amounts", "TranslationInfo", "Extras"
]

url = "http://data.gdeltproject.org/gkg/20260228.gkg.csv.zip"
resp = requests.get(url, timeout=20)

with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
    inner_name = z.namelist()[0]
    with z.open(inner_name) as f:
        first_line = f.readline().decode("utf-8", errors="replace")

    with z.open(inner_name) as f:
        df = pd.read_csv(f, sep="\t", header=None, names=GKG_COLUMNS, dtype=str, on_bad_lines="skip", low_memory=False)

print("Tab count in first raw line:", first_line.count(chr(9)))
print("Expected tab count (26 for 27 cols):", len(GKG_COLUMNS) - 1)

print("\nSample row - V2Themes column:")
print(repr(df["V2Themes"].iloc[0]))
print("\nSample row - Organizations column:")
print(repr(df["Organizations"].iloc[0]))
print("\nSample row - DocumentIdentifier column:")
print(repr(df["DocumentIdentifier"].iloc[0]))
print("\nSample row - SourceCommonName column:")
print(repr(df["SourceCommonName"].iloc[0]))
