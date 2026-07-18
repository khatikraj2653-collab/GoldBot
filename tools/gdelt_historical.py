import io
import re
import zipfile
import requests
import pandas as pd
import trafilatura
from datetime import datetime, timedelta

GKG_COLUMNS = [
    "DATE", "NUMARTS", "COUNTS", "THEMES", "LOCATIONS",
    "PERSONS", "ORGANIZATIONS", "TONE", "CAMEOEVENTIDS",
    "SOURCES", "SOURCEURLS"
]

CONFLICT_ACTORS = r"IRAN|ISRAEL|RUSSIA|UKRAINE|CHINA|TAIWAN|NORTH KOREA|HOUTHI|HEZBOLLAH|GAZA|HORMUZ"
CONFLICT_ACTIONS = r"WAR|STRIKE|MISSILE|ATTACK|CONFLICT|MILITARY|SANCTIONS|BLOCKADE|AIRSTRIKE"

CENTRAL_BANK_ORGS = r"FEDERAL RESERVE|CENTRAL BANK|PEOPLE'S BANK|BANK OF CHINA|BANK OF JAPAN|BANK OF ENGLAND|BANK OF RUSSIA|WORLD GOLD COUNCIL|IMF|BUNDESBANK"


def fetch_gkg_day(as_of_date, max_lookback=3):
    for offset in range(max_lookback):
        d = as_of_date - timedelta(days=offset)
        date_str = d.strftime("%Y%m%d")
        url = f"http://data.gdeltproject.org/gkg/{date_str}.gkg.csv.zip"
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code != 200 or len(resp.content) < 1000:
                continue
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                inner_name = z.namelist()[0]
                with z.open(inner_name) as f:
                    df = pd.read_csv(
                        f, sep="\t", header=0, names=GKG_COLUMNS,
                        dtype=str, on_bad_lines="skip", low_memory=False
                    )
            print(f"[GDELT] Loaded {date_str}.gkg.csv.zip � {len(df)} rows")
            return df
        except Exception as e:
            print(f"[GDELT] Failed {date_str}: {e}")
            continue
    return None


def extract_geopolitical_articles(df, max_articles=6):
    if df is None or df.empty:
        return [], None

    combined_text = df["THEMES"].fillna("") + " " + df["ORGANIZATIONS"].fillna("") + " " + df["LOCATIONS"].fillna("")
    has_actor = combined_text.str.contains(CONFLICT_ACTORS, case=False, regex=True)
    has_action = combined_text.str.contains(CONFLICT_ACTIONS, case=False, regex=True)
    matched = df[has_actor & has_action]

    if matched.empty:
        return [], None

    tones = []
    for t in matched["TONE"].dropna():
        try:
            tones.append(float(t.split(",")[0]))
        except Exception:
            pass
    avg_tone = round(sum(tones) / len(tones), 2) if tones else None

    all_urls = []
    for src_urls in matched["SOURCEURLS"].dropna():
        all_urls.extend([u.strip() for u in src_urls.split(";") if u.strip()])
        if len(all_urls) >= max_articles * 4:
            break

    return all_urls, avg_tone


def extract_central_bank_articles(df, max_articles=6):
    if df is None or df.empty:
        return [], None

    combined_text = df["ORGANIZATIONS"].fillna("") + " " + df["THEMES"].fillna("")
    has_bank = combined_text.str.contains(CENTRAL_BANK_ORGS, case=False, regex=True)
    matched = df[has_bank]

    if matched.empty:
        return [], None

    tones = []
    for t in matched["TONE"].dropna():
        try:
            tones.append(float(t.split(",")[0]))
        except Exception:
            pass
    avg_tone = round(sum(tones) / len(tones), 2) if tones else None

    all_urls = []
    for src_urls in matched["SOURCEURLS"].dropna():
        all_urls.extend([u.strip() for u in src_urls.split(";") if u.strip()])
        if len(all_urls) >= max_articles * 4:
            break

    return all_urls, avg_tone


def fetch_relevant_article_texts(urls, relevance_keywords, max_articles=3, char_limit=400, window=200):
    """Fetches article text, discards articles that don't mention the relevance
    keywords anywhere, and extracts a window of text CENTERED on the match
    instead of always taking the article's opening paragraph."""
    texts = []
    pattern = re.compile(relevance_keywords, re.IGNORECASE)
    for url in urls:
        if len(texts) >= max_articles:
            break
        try:
            downloaded = trafilatura.fetch_url(url, no_ssl=True)
            if not downloaded:
                continue
            text = trafilatura.extract(downloaded)
            if not text or len(text) < 50:
                continue
            match = pattern.search(text)
            if not match:
                continue
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            snippet = text[start:end].strip()
            texts.append(snippet)
        except Exception:
            continue
    return texts


def get_geopolitical_risk_historical(as_of_date):
    df = fetch_gkg_day(as_of_date)
    urls, avg_tone = extract_geopolitical_articles(df)

    if not urls:
        return "Geopolitical Risk: Data unavailable (no GDELT matches for this date)"

    relevance_check = f"({CONFLICT_ACTORS})"
    article_texts = fetch_relevant_article_texts(urls, relevance_check)

    tone_note = f"Average news sentiment on this date: {avg_tone} (scale -100 to +100). " if avg_tone is not None else ""

    if not article_texts:
        return f"Geopolitical Risk: {tone_note}{len(urls)} candidate articles found but none passed relevance check."

    combined = " ".join(article_texts).replace("\n", " ").strip()
    return f"Geopolitical Risk: {tone_note}{combined[:1000]}"


def get_central_bank_buying_historical(as_of_date):
    df = fetch_gkg_day(as_of_date)
    urls, avg_tone = extract_central_bank_articles(df)

    if not urls:
        return "Central Bank Gold Buying: Data unavailable (no GDELT matches for this date)"

    relevance_check = r"\bGOLD\b"
    article_texts = fetch_relevant_article_texts(urls, relevance_check)

    tone_note = f"Average news sentiment on this date: {avg_tone} (scale -100 to +100). " if avg_tone is not None else ""

    if not article_texts:
        return f"Central Bank Gold Buying: {tone_note}{len(urls)} candidate articles found but none passed relevance check."

    combined = " ".join(article_texts).replace("\n", " ").strip()
    return f"Central Bank Gold Buying: {tone_note}{combined[:1000]}"


if __name__ == "__main__":
    test_date = datetime(2026, 2, 28)
    print("\n--- Testing Geopolitical Risk ---")
    print(get_geopolitical_risk_historical(test_date))
    print("\n--- Testing Central Bank Buying ---")
    print(get_central_bank_buying_historical(test_date))
