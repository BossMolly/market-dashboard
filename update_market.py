\#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US Market Dashboard 자동 업데이트 스크립트
Claude Code CLI로 데이터 수집 → index.html 주입 → GitHub push
"""

import subprocess, json, re, sys, os, shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ── 설정 ────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
TEMPLATE    = BASE_DIR / "us_market_dashboard.html"
INDEX_HTML  = BASE_DIR / "index.html"
DATA_DIR    = BASE_DIR / "reports"
KST         = ZoneInfo("Asia/Seoul")
TODAY       = datetime.now(KST).strftime("%Y-%m-%d")
NOW_KST     = datetime.now(KST).strftime("%H:%M KST")
TIMEOUT     = 300  # 5분 (Claude Code 웹검색 포함)
AUTO_PUSH   = True  # GitHub 자동 push 여부

DATA_DIR.mkdir(exist_ok=True)

# ── 로그 ─────────────────────────────────────────────────────────
def log(msg): print(f"[{datetime.now(KST).strftime('%H:%M:%S')}] {msg}", flush=True)

# ── Claude Code CLI 호출 ─────────────────────────────────────────
def call_claude(prompt: str, label: str) -> str:
    log(f"📡 Claude Code 호출: {label} ...")
    try:
        result = subprocess.run(
            ["claude", "--no-interactive", "-p", prompt, "--output-format", "text"],
            capture_output=True, text=True, encoding="utf-8",
            timeout=TIMEOUT
        )
        if result.returncode != 0:
            log(f"⚠️  {label} 오류: {result.stderr[:200]}")
        return result.stdout
    except subprocess.TimeoutExpired:
        log(f"⏱  {label} 타임아웃 ({TIMEOUT}초)")
        return ""
    except FileNotFoundError:
        log("❌ claude 명령어를 찾을 수 없습니다. Claude Code가 설치됐는지 확인하세요.")
        sys.exit(1)

# ── JSON 추출 ────────────────────────────────────────────────────
def extract_json(text: str) -> dict | None:
    text = re.sub(r"```json\s*", "", text).replace("```", "").strip()
    # { ... } 블록 추출
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end+1])
    except json.JSONDecodeError:
        return None

# ── 프롬프트 정의 ────────────────────────────────────────────────
OVERVIEW_PROMPT = f"""
오늘({TODAY} {NOW_KST}) 미국 주식 시장 최신 데이터를 웹에서 검색하여
아래 JSON 형식으로만 응답하세요. 반드시 {{ 로 시작하고 }} 로 끝내세요.
Markdown, 코드블록, 설명 없이 순수 JSON만 출력하세요.

{{
  "date": "{TODAY}",
  "updated_at": "{NOW_KST}",
  "indices": {{
    "sp500":  {{"value": 0, "change": 0, "change_pct": 0}},
    "nasdaq": {{"value": 0, "change": 0, "change_pct": 0}},
    "dow":    {{"value": 0, "change": 0, "change_pct": 0}},
    "vix":    {{"value": 0, "change": 0}}
  }},
  "market_mood": {{"score": 50, "label": "", "vix_signal": "", "summary": ""}},
  "top_news": [
    {{"rank":1,"headline":"","summary":"","source":"","time":"","importance":"high","impact":""}},
    {{"rank":2,"headline":"","summary":"","source":"","time":"","importance":"high","impact":""}},
    {{"rank":3,"headline":"","summary":"","source":"","time":"","importance":"mid","impact":""}},
    {{"rank":4,"headline":"","summary":"","source":"","time":"","importance":"mid","impact":""}},
    {{"rank":5,"headline":"","summary":"","source":"","time":"","importance":"low","impact":""}}
  ],
  "sectors": [
    {{"name":"기술","en":"Technology","change_pct":0}},
    {{"name":"에너지","en":"Energy","change_pct":0}},
    {{"name":"금융","en":"Financials","change_pct":0}},
    {{"name":"헬스케어","en":"Healthcare","change_pct":0}},
    {{"name":"소비재","en":"Consumer Discretionary","change_pct":0}},
    {{"name":"산업재","en":"Industrials","change_pct":0}},
    {{"name":"필수소비재","en":"Consumer Staples","change_pct":0}},
    {{"name":"유틸리티","en":"Utilities","change_pct":0}},
    {{"name":"부동산","en":"Real Estate","change_pct":0}},
    {{"name":"소재","en":"Materials","change_pct":0}},
    {{"name":"통신서비스","en":"Communication Services","change_pct":0}}
  ],
  "economic_indicators": [
    {{"name":"미국 10년물 국채금리","value":0,"change":0,"unit":"%"}},
    {{"name":"미국 2년물 국채금리","value":0,"change":0,"unit":"%"}},
    {{"name":"DXY 달러인덱스","value":0,"change":0,"unit":""}},
    {{"name":"WTI 원유","value":0,"change":0,"unit":"$/배럴"}},
    {{"name":"금 현물","value":0,"change":0,"unit":"$/oz"}},
    {{"name":"연준 기준금리","value":0,"change":0,"unit":"%"}}
  ],
  "buzz_stocks": [
    {{"rank":1,"ticker":"","name":"","heat":5,"change_pct":0,"reason":""}},
    {{"rank":2,"ticker":"","name":"","heat":4,"change_pct":0,"reason":""}},
    {{"rank":3,"ticker":"","name":"","heat":3,"change_pct":0,"reason":""}},
    {{"rank":4,"ticker":"","name":"","heat":3,"change_pct":0,"reason":""}},
    {{"rank":5,"ticker":"","name":"","heat":2,"change_pct":0,"reason":""}}
  ],
  "schedule": [
    {{"date_kst":"","time_kst":"","title":"","description":"","type":"econ","importance":"high"}},
    {{"date_kst":"","time_kst":"","title":"","description":"","type":"fed","importance":"high"}},
    {{"date_kst":"","time_kst":"","title":"","description":"","type":"earnings","importance":"high"}},
    {{"date_kst":"","time_kst":"","title":"","description":"","type":"econ","importance":"mid"}},
    {{"date_kst":"","time_kst":"","title":"","description":"","type":"econ","importance":"mid"}}
  ],
  "market_outlook": {{
    "summary": "",
    "key_risks": ["", "", ""],
    "strategy": ["", "", ""],
    "overall_sentiment": "neutral"
  }}
}}

빈 값들을 실제 오늘 최신 데이터로 채워주세요.

추가로 aiInsight 블록을 반드시 포함하세요:
"aiInsight": {{
  "marketStory": "오늘 시장을 한 문장으로 요약 (왜 움직였는지 중심으로)",
  "marketBias": "risk-off 또는 risk-on 또는 neutral",
  "confidenceScore": 0~100 숫자,
  "drivers": [
    {{"label": "핵심 드라이버 설명", "direction": "neg 또는 pos 또는 warn", "icon": "이모지"}}
  ],
  "actionableInsights": {{
    "equityBias": "bullish 또는 bearish 또는 neutral",
    "sectorRotation": "섹터 로테이션 방향 설명",
    "riskLevel": "high 또는 medium 또는 low",
    "watchList": ["티커 또는 이벤트"],
    "strategy": ["구체적 액션 아이템"]
  }},
  "scenarios": {{
    "bullish": {{"desc": "강세 시나리오 설명", "condition": "조건"}},
    "bearish": {{"desc": "약세 시나리오 설명", "condition": "조건"}},
    "keyTriggers": ["핵심 트리거 1", "핵심 트리거 2", "핵심 트리거 3"],
    "watchNext": ["다음에 주목할 이벤트"]
  }}
}}
"""

def sector_prompt(sector_name: str, etf: str, tickers: str) -> str:
    return f"""
오늘({TODAY} {NOW_KST}) 미국 {sector_name} 섹터 최신 데이터를 웹에서 검색하여
아래 JSON 형식으로만 응답하세요. 순수 JSON만 출력하세요.

{{
  "sector_perf": {{"pct": "", "direction": "up", "etf": "{etf}", "etf_val": "", "etf_chg": ""}},
  "top_news": [
    {{"rank":1,"headline":"","summary":"","source":"","time":"","importance":"high","impact":""}},
    {{"rank":2,"headline":"","summary":"","source":"","time":"","importance":"high","impact":""}},
    {{"rank":3,"headline":"","summary":"","source":"","time":"","importance":"mid","impact":""}},
    {{"rank":4,"headline":"","summary":"","source":"","time":"","importance":"mid","impact":""}},
    {{"rank":5,"headline":"","summary":"","source":"","time":"","importance":"low","impact":""}}
  ],
  "stocks": [
    {{"ticker":"T1","name":"","price":"","change":"","mktcap":"","pe":"","signal":"매수"}}
  ],
  "weekly_watch": [
    {{"title":"","body":"","tag":"bull"}},
    {{"title":"","body":"","tag":"bear"}},
    {{"title":"","body":"","tag":"watch"}}
  ]
}}

검색 대상 종목: {tickers}
빈 값을 실제 오늘 데이터로 채우고, stocks는 위 종목 전체로 작성하세요.
signal은 매수/중립/매도 중 하나.
"""

SECTORS = {
    "tech":       ("기술",    "XLK",  "NVDA,AAPL,MSFT,META,GOOGL,AMZN,AMD,TSLA,ORCL,ADBE"),
    "energy":     ("에너지",  "XLE",  "XOM,CVX,COP,SLB,MPC,PSX,VLO,OXY,HAL,DVN"),
    "finance":    ("금융",    "XLF",  "JPM,BAC,GS,MS,WFC,BLK,C,AXP,V,MA"),
    "consumer":   ("소비재",  "XLY",  "AMZN,TSLA,HD,MCD,NKE,SBUX,TGT,COST,WMT,PG"),
    "realestate": ("부동산",  "XLRE", "PLD,AMT,EQIX,SPG,O,DLR,PSA,EQR,AVB,VNQ"),
    "crypto":     ("코인",    "IBIT", "COIN,MSTR,MARA,RIOT,CLSK,HUT,IBIT,BITB,FBTC,GBTC"),
}

# ── HTML 주입 ────────────────────────────────────────────────────
def inject_html(overview: dict, sectors: dict) -> bool:
    if not TEMPLATE.exists():
        log(f"❌ 템플릿 파일 없음: {TEMPLATE}")
        return False

    html = TEMPLATE.read_text(encoding="utf-8")

    # SECTOR_PRELOAD 교체
    sector_json = json.dumps(sectors, ensure_ascii=False, separators=(",", ":"))
    sector_block = f"/* ── SECTOR PRELOADED DATA ({TODAY}) ── */\nwindow.SECTOR_PRELOAD = {sector_json};"

    html = re.sub(
        r"/\* ── SECTOR PRELOADED DATA \([^)]+\) ── \*/\nwindow\.SECTOR_PRELOAD = \{.*?\};",
        sector_block, html, flags=re.DOTALL
    )

    # MARKET_DATA 교체
    overview_json = json.dumps(overview, ensure_ascii=False, indent=2)
    market_block = f"/* ── PRELOADED DATA ({TODAY}) ── */\nwindow.MARKET_DATA = {overview_json};"

    html = re.sub(
        r"/\* ── PRELOADED DATA \([^)]+\) ── \*/\nwindow\.MARKET_DATA = \{.*?\};",
        market_block, html, flags=re.DOTALL
    )

    # 업데이트된 HTML을 템플릿과 index.html 둘 다 저장
    TEMPLATE.write_text(html, encoding="utf-8")
    INDEX_HTML.write_text(html, encoding="utf-8")
    log(f"✅ HTML 주입 완료 → index.html")
    return True

# ── GitHub Push ──────────────────────────────────────────────────
def git_push():
    if not (BASE_DIR / ".git").exists():
        log("⚠️  Git 저장소 미초기화 — push 건너뜀")
        return
    try:
        subprocess.run(["git", "add", "index.html", "us_market_dashboard.html"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                              cwd=BASE_DIR, capture_output=True)
        if diff.returncode == 0:
            log("ℹ️  변경사항 없음 — push 건너뜀")
            return
        subprocess.run(
            ["git", "commit", "-m", f"📊 {TODAY} 시장 리포트 자동 업데이트"],
            cwd=BASE_DIR, check=True, capture_output=True
        )
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        log("✅ GitHub Pages 업데이트 완료!")
    except subprocess.CalledProcessError as e:
        log(f"⚠️  Git 오류: {e.stderr.decode() if e.stderr else e}")

# ── 메인 ─────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 52)
    print(f"  US Market Dashboard 자동 업데이트")
    print(f"  {TODAY}  {NOW_KST}")
    print("=" * 52)
    print()

    # 1. 전체 개요 수집
    log("[1/5] 전체 개요 데이터 수집 중...")
    overview_raw = call_claude(OVERVIEW_PROMPT, "전체 개요")
    overview = extract_json(overview_raw)
    if overview:
        path = DATA_DIR / f"market_data_{TODAY}.json"
        path.write_text(json.dumps(overview, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"✅ 전체 개요 저장: {path.name}")
    else:
        log("⚠️  전체 개요 JSON 파싱 실패 — 기존 데이터 유지")
        prev = DATA_DIR / f"market_data_{TODAY}.json"
        if prev.exists():
            overview = json.loads(prev.read_text(encoding="utf-8"))
        else:
            log("❌ 이전 데이터도 없음 — 종료")
            sys.exit(1)

    # 2~5. 섹터별 수집
    sector_data = {}
    for i, (key, (name, etf, tickers)) in enumerate(SECTORS.items(), 2):
        log(f"[{i}/5] {name} 섹터 데이터 수집 중...")
        raw = call_claude(sector_prompt(name, etf, tickers), name)
        data = extract_json(raw)
        if data:
            path = DATA_DIR / f"sector_{key}_{TODAY}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            sector_data[key] = data
            log(f"✅ {name} 섹터 저장: {path.name}")
        else:
            log(f"⚠️  {name} 섹터 파싱 실패 — 이전 데이터 사용 시도")
            prev = DATA_DIR / f"sector_{key}_{TODAY}.json"
            if prev.exists():
                sector_data[key] = json.loads(prev.read_text(encoding="utf-8"))

    # HTML 주입
    log("[주입] index.html 생성 중...")
    if not inject_html(overview, sector_data):
        log("❌ HTML 주입 실패")
        sys.exit(1)

    # GitHub Push
    if AUTO_PUSH:
        log("[Push] GitHub에 업로드 중...")
        git_push()

    # 브라우저 열기 (Windows)
    if sys.platform == "win32":
        os.startfile(str(INDEX_HTML))

    print()
    print("=" * 52)
    print("  ✅ 완료!")
    print(f"  대시보드: {INDEX_HTML}")
    print(f"  URL: https://BossMolly.github.io/market-dashboard/")
    print("=" * 52)
    print()

if __name__ == "__main__":
    main()
