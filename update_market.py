#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US Market Intelligence — 로컬 자동 업데이트 스크립트
실행: run_market_update.bat (PC 켤 때 작업 스케줄러 자동 실행)
기능: Claude Code CLI로 6개 섹터 + 전체 개요 수집 → HTML 주입 → GitHub push
"""

import subprocess, json, re, sys, os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ── 설정 ─────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
TEMPLATE   = BASE_DIR / "us_market_dashboard.html"
INDEX_HTML = BASE_DIR / "index.html"
DATA_DIR   = BASE_DIR / "reports"
KST        = ZoneInfo("Asia/Seoul")
TODAY      = datetime.now(KST).strftime("%Y-%m-%d")
NOW_KST    = datetime.now(KST).strftime("%H:%M KST")
TIMEOUT    = 300  # 5분
AUTO_PUSH  = True

DATA_DIR.mkdir(exist_ok=True)

def log(msg):
    print(f"[{datetime.now(KST).strftime('%H:%M:%S')}] {msg}", flush=True)

def call_claude(prompt: str, label: str) -> str:
    log(f"  → {label} 수집 중...")
    try:
        result = subprocess.run(
            ["claude", "--print", "-p", prompt, "--output-format", "text"],
            capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT
        )
        if result.returncode != 0:
            log(f"  ⚠ {label} 오류: {result.stderr[:100]}")
        return result.stdout
    except subprocess.TimeoutExpired:
        log(f"  ⏱ {label} 타임아웃")
        return ""
    except FileNotFoundError:
        log("❌ claude 명령어를 찾을 수 없습니다. 'claude login'을 먼저 실행하세요.")
        sys.exit(1)

def extract_json(text: str) -> dict | None:
    text = re.sub(r'```json\s*', '', text).replace('```', '').strip()
    s, e = text.find('{'), text.rfind('}')
    if s == -1 or e == -1:
        return None
    try:
        return json.loads(text[s:e+1])
    except:
        return None

def validate_urls(data: dict) -> dict:
    """뉴스 URL 유효성 검증 - 빈 문자열이나 잘못된 URL 제거"""
    if 'top_news' in data:
        for n in data['top_news']:
            url = n.get('url', '')
            if url and not url.startswith('http'):
                n['url'] = ''
    return data

# ── 프롬프트 ─────────────────────────────────────────────────────
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
  "aiInsight": {{
    "marketStory": "오늘 시장을 한 문장으로 — 수치보다 왜 움직였는지 중심으로",
    "marketBias": "risk-off 또는 risk-on 또는 neutral",
    "confidenceScore": 75,
    "drivers": [
      {{"label": "핵심 드라이버 설명", "direction": "neg 또는 pos 또는 warn", "icon": "이모지"}},
      {{"label": "", "direction": "neg", "icon": ""}},
      {{"label": "", "direction": "pos", "icon": ""}},
      {{"label": "", "direction": "warn", "icon": ""}},
      {{"label": "", "direction": "neg", "icon": ""}}
    ],
    "actionableInsights": {{
      "equityBias": "bullish 또는 bearish 또는 neutral",
      "sectorRotation": "섹터 로테이션 방향 설명",
      "riskLevel": "high 또는 medium 또는 low",
      "watchList": ["티커 또는 이벤트"],
      "strategy": ["구체적 액션 아이템 1", "구체적 액션 아이템 2", "구체적 액션 아이템 3"]
    }},
    "scenarios": {{
      "bullish": {{"desc": "강세 시나리오 2~3문장", "condition": "조건: 구체적 수치나 이벤트"}},
      "bearish": {{"desc": "약세 시나리오 2~3문장", "condition": "조건: 구체적 수치나 이벤트"}},
      "keyTriggers": ["핵심 트리거 1", "핵심 트리거 2", "핵심 트리거 3"],
      "watchNext": ["다음 주목 이벤트 1", "다음 주목 이벤트 2", "다음 주목 이벤트 3"]
    }},
    "newsCorrelation": {{
      "summary": "오늘 주요 뉴스들이 서로 어떻게 연결되어 시장에 영향을 미쳤는지 2~3문장",
      "chains": [
        {{"nodes": [{{"label": "원인", "type": "cause"}}, {{"label": "결과", "type": "effect"}}], "impact": "트레이더 관점 시사점"}},
        {{"nodes": [{{"label": "원인2", "type": "cause"}}, {{"label": "중간", "type": "mixed"}}, {{"label": "결과2", "type": "effect"}}], "impact": "시사점"}},
        {{"nodes": [{{"label": "원인3", "type": "cause"}}, {{"label": "결과3", "type": "effect"}}], "impact": "시사점"}}
      ]
    }}
  }},
  "market_mood": {{"score": 50, "label": "", "vix_signal": "", "summary": ""}},
  "top_news": [
    {{"rank":1,"headline":"","summary":"2~3문장","source":"","time":"","importance":"high","category":"MACRO 또는 EARNINGS 또는 SECTOR 또는 POLICY 또는 GEOPOLITICAL","impact":"","url":"실제 기사 URL (없으면 빈 문자열)"}},
    {{"rank":2,"headline":"","summary":"","source":"","time":"","importance":"high","category":"","impact":"","url":""}},
    {{"rank":3,"headline":"","summary":"","source":"","time":"","importance":"mid","category":"","impact":"","url":""}},
    {{"rank":4,"headline":"","summary":"","source":"","time":"","importance":"mid","category":"","impact":"","url":""}},
    {{"rank":5,"headline":"","summary":"","source":"","time":"","importance":"low","category":"","impact":"","url":""}}
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
    {{"name":"10Y 국채금리","value":0,"change":0,"unit":"%"}},
    {{"name":"2Y 국채금리","value":0,"change":0,"unit":"%"}},
    {{"name":"DXY 달러인덱스","value":0,"change":0,"unit":""}},
    {{"name":"WTI 원유","value":0,"change":0,"unit":"$/bbl"}},
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
  ]
}}

빈 값들을 실제 오늘 최신 데이터로 채워주세요.
"""

SECTORS = {
    "tech":       ("기술(Technology)",     "XLK",  "NVDA,AAPL,MSFT,META,GOOGL,AMZN,AMD,TSLA,ORCL,ADBE"),
    "energy":     ("에너지(Energy)",        "XLE",  "XOM,CVX,COP,SLB,MPC,PSX,VLO,OXY,HAL,DVN"),
    "finance":    ("금융(Financials)",      "XLF",  "JPM,BAC,GS,MS,WFC,BLK,C,AXP,V,MA"),
    "consumer":   ("소비재(Consumer Disc)", "XLY",  "AMZN,TSLA,HD,MCD,NKE,SBUX,TGT,COST,WMT,PG"),
    "realestate": ("부동산(Real Estate)",   "XLRE", "PLD,AMT,EQIX,SPG,O,DLR,PSA,EQR,AVB,VNQ"),
    "crypto":     ("코인/블록체인",          "IBIT", "COIN,MSTR,MARA,RIOT,CLSK,HUT,IBIT,BITB,FBTC,GBTC"),
}

def sector_prompt(sector_name: str, etf: str, tickers: str) -> str:
    return f"""
오늘({TODAY} {NOW_KST}) 미국 {sector_name} 섹터 최신 데이터를 웹에서 검색하여
아래 JSON 형식으로만 응답하세요. 순수 JSON만 출력하세요.

{{
  "sector_perf": {{"pct": "", "direction": "up", "etf": "{etf}", "etf_val": "", "etf_chg": ""}},
  "top_news": [
    {{"rank":1,"headline":"","summary":"2~3문장","source":"","time":"","importance":"high","impact":"","url":"실제 기사 URL (없으면 빈 문자열)"}},
    {{"rank":2,"headline":"","summary":"","source":"","time":"","importance":"high","impact":"","url":""}},
    {{"rank":3,"headline":"","summary":"","source":"","time":"","importance":"mid","impact":"","url":""}},
    {{"rank":4,"headline":"","summary":"","source":"","time":"","importance":"mid","impact":"","url":""}},
    {{"rank":5,"headline":"","summary":"","source":"","time":"","importance":"low","impact":"","url":""}}
  ],
  "stocks": [
    {{"ticker":"T1","name":"","price":"","change":"","mktcap":"","pe":"","signal":"매수","issue":"오늘 해당 종목의 핵심 이슈 1줄"}}
  ],
  "weekly_watch": [
    {{"title":"","body":"구체적 수치·레벨 포함 2~3문장","tag":"bull"}},
    {{"title":"","body":"","tag":"bear"}},
    {{"title":"","body":"","tag":"watch"}}
  ],
  "recommendations": [
    {{"rank":1,"ticker":"","name":"","price":"","change_pct":0,"signal":"매수","reason":"뉴스·섹터 흐름과 연결된 추천 이유. 증권 전문가 관점 2~3문장."}},
    {{"rank":2,"ticker":"","name":"","price":"","change_pct":0,"signal":"매수","reason":""}},
    {{"rank":3,"ticker":"","name":"","price":"","change_pct":0,"signal":"매수","reason":""}}
  ],
  "sector_schedule": [
    {{"date_kst":"","time_kst":"","title":"섹터 관련 주요 일정","importance":"high","insight":"이 일정이 섹터에 미칠 영향과 예상 여파 2문장"}}
  ]
}}

검색 대상 종목: {tickers}
- 빈 값을 실제 오늘 최신 데이터로 채우세요
- stocks는 위 종목 전체를 작성하세요 (signal: 매수/중립/매도)
- recommendations는 오늘 뉴스·섹터 흐름과 연결하여 증권 전문가 관점으로 작성
- sector_schedule은 이 섹터와 직접 관련된 향후 5거래일 내 주요 일정 (KST 기준)
- url은 실제 검색된 기사의 URL을 넣고, 없으면 빈 문자열("")로 두세요
"""

# ── HTML 주입 ─────────────────────────────────────────────────────
def inject_html(overview: dict, sectors: dict) -> bool:
    if not TEMPLATE.exists():
        log(f"❌ 템플릿 없음: {TEMPLATE}")
        return False
    html = TEMPLATE.read_text(encoding='utf-8')

    # SECTOR_PRELOAD 교체
    sector_json = json.dumps(sectors, ensure_ascii=False, separators=(',', ':'))
    sector_block = f"/* ── SECTOR PRELOADED DATA ({TODAY}) ── */\nwindow.SECTOR_PRELOAD = {sector_json};"
    html = re.sub(
        r'/\* ── SECTOR PRELOADED DATA \([^)]+\) ── \*/\nwindow\.SECTOR_PRELOAD = \{.*?\};',
        sector_block, html, flags=re.DOTALL
    )

    # MARKET_DATA 교체
    overview_json = json.dumps(overview, ensure_ascii=False, indent=2)
    market_block = f"/* ── PRELOADED DATA ({TODAY}) ── */\nwindow.MARKET_DATA = {overview_json};"
    html = re.sub(
        r'/\* ── PRELOADED DATA \([^)]+\) ── \*/\nwindow\.MARKET_DATA = \{.*?\};',
        market_block, html, flags=re.DOTALL
    )

    TEMPLATE.write_text(html, encoding='utf-8')
    INDEX_HTML.write_text(html, encoding='utf-8')
    log("✅ index.html 생성 완료")
    return True

# ── GitHub Push ───────────────────────────────────────────────────
def git_push():
    if not (BASE_DIR / ".git").exists():
        log("⚠ Git 미초기화 — push 건너뜀")
        return
    try:
        subprocess.run(["git","add","index.html","us_market_dashboard.html"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        diff = subprocess.run(["git","diff","--cached","--quiet"],
                              cwd=BASE_DIR, capture_output=True)
        if diff.returncode == 0:
            log("ℹ 변경사항 없음 — push 건너뜀")
            return
        subprocess.run(["git","commit","-m",f"📊 {TODAY} 시장 리포트 자동 업데이트"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        subprocess.run(["git","push","origin","main"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        log("✅ GitHub Pages 업데이트 완료!")
    except subprocess.CalledProcessError as e:
        log(f"⚠ Git 오류: {e}")

# ── 메인 ─────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 54)
    print(f"  US Market Intelligence — 자동 업데이트")
    print(f"  {TODAY}  {NOW_KST}")
    print("=" * 54)

    # 오늘 이미 수집한 데이터 있으면 재사용 여부 확인
    overview_path = DATA_DIR / f"market_data_{TODAY}.json"
    if overview_path.exists():
        size = overview_path.stat().st_size
        if size > 500:
            log(f"ℹ 오늘 데이터 이미 존재 ({size} bytes) — 재수집 건너뜀")
            overview = json.loads(overview_path.read_text(encoding='utf-8'))
        else:
            overview = None
    else:
        overview = None

    # 1. 전체 개요 수집
    if overview is None:
        log("[1/7] 전체 개요 수집...")
        raw = call_claude(OVERVIEW_PROMPT, "전체 개요")
        overview = extract_json(raw)
        if overview:
            overview = validate_urls(overview)
            overview_path.write_text(json.dumps(overview, ensure_ascii=False, indent=2), encoding='utf-8')
            log(f"  ✅ 전체 개요 저장 완료")
        else:
            log("  ❌ 전체 개요 파싱 실패 — 종료")
            sys.exit(1)
    else:
        log("[1/7] 전체 개요 — 기존 데이터 재사용")

    # 2~7. 섹터별 수집
    sector_data = {}
    sector_list = list(SECTORS.items())
    for i, (key, (name, etf, tickers)) in enumerate(sector_list, 2):
        log(f"[{i}/7] {name} 섹터...")
        sec_path = DATA_DIR / f"sector_{key}_{TODAY}.json"

        if sec_path.exists() and sec_path.stat().st_size > 200:
            log(f"  ℹ 기존 데이터 재사용")
            sector_data[key] = json.loads(sec_path.read_text(encoding='utf-8'))
            continue

        raw = call_claude(sector_prompt(name, etf, tickers), name)
        data = extract_json(raw)
        if data:
            data = validate_urls(data)
            sec_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            sector_data[key] = data
            log(f"  ✅ 저장 완료")
        else:
            log(f"  ⚠ 파싱 실패 — 빈 데이터로 진행")
            sector_data[key] = {}

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
    print("=" * 54)
    print("  ✅ 완료!")
    print(f"  대시보드: {INDEX_HTML}")
    print(f"  URL: https://BossMolly.github.io/market-dashboard/")
    print("=" * 54)
    print()

if __name__ == "__main__":
    main()
