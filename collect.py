import requests, os, zipfile, datetime
import pandas as pd

save_dir = "data"
output = "BTCUSDT_1m_combined.csv"
os.makedirs(save_dir, exist_ok=True)

cols = ["timestamp","open","high","low","close","volume",
        "close_time","quote_volume","trades",
        "taker_buy_base","taker_buy_quote","ignore"]

def download(url):
    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        return False
    fname = url.split("/")[-1]
    zpath = os.path.join(save_dir, fname)
    with open(zpath, "wb") as f:
        f.write(r.content)
    with zipfile.ZipFile(zpath, "r") as z:
        z.extractall(save_dir)
    os.remove(zpath)
    return True

# 기존 CSV가 없으면 → 초기 수집 (2024.11 ~ 어제)
# 있으면 → 마지막 날짜 이후만 수집
if os.path.exists(output):
    existing = pd.read_csv(output)
    existing["timestamp"] = pd.to_datetime(existing["timestamp"])
    last_date = existing["timestamp"].iloc[-1].date()
    start_date = last_date + datetime.timedelta(days=1)
    print(f"기존 데이터 발견. {start_date}부터 수집 시작")
else:
    existing = None
    start_date = datetime.date(2024, 11, 1)
    print(f"초기 수집 시작: {start_date}부터")

end_date = datetime.date.today() - datetime.timedelta(days=1)

# Monthly 우선 시도
current = start_date.replace(day=1)
while current <= end_date:
    m = current.strftime("%Y-%m")
    url = f"https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-{m}.zip"
    if download(url):
        print(f"Monthly {m} 다운완료")
    if current.month == 12:
        current = current.replace(year=current.year+1, month=1)
    else:
        current = current.replace(month=current.month+1)

# Daily로 빈 날짜 채우기
d = start_date
while d <= end_date:
    ds = d.strftime("%Y-%m-%d")
    url = f"https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1m/BTCUSDT-1m-{ds}.zip"
    if download(url):
        print(f"Daily {ds} 다운완료")
    d += datetime.timedelta(days=1)

# 모든 CSV 합치기
print("CSV 병합 중...")
all_files = sorted([f for f in os.listdir(save_dir) if f.endswith(".csv")])
df_list = []
if existing is not None:
    df_list.append(existing)

for f in all_files:
    tmp = pd.read_csv(os.path.join(save_dir, f), header=None, names=cols)
    tmp = tmp[pd.to_numeric(tmp["timestamp"], errors="coerce").notna()]
    tmp["timestamp"] = pd.to_datetime(tmp["timestamp"].astype(float), unit="ms")
    df_list.append(tmp)

df = pd.concat(df_list, ignore_index=True)
df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
df.to_csv(output, index=False)

print(f"완료! 총 {len(df):,}개 캔들")
print(f"기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

# 임시 파일 삭제
import shutil
shutil.rmtree(save_dir)
