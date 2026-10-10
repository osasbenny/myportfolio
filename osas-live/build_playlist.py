#!/usr/bin/env python3
"""Build a cross-device OSAS LIVE M3U from publicly listed English streams.
Only metadata and stream addresses are indexed. Content remains with broadcasters.
"""
from __future__ import annotations
import concurrent.futures
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
IPTV = "https://iptv-org.github.io/iptv"
# Popular genres first so no category vanishes when the total limit is reached.
CATEGORIES = [
    ("News & Current Affairs", "news", 65),
    ("Movies", "movies", 65),
    ("Documentaries & History", "documentary", 65),
    ("Music TV", "music", 60),
    ("Science & Technology", "science", 38),
    ("Sports", "sports", 40),
    ("Wildlife & Outdoors", "outdoor", 38),
    ("Classic Movies & TV", "classic", 36),
    ("TV Series", "series", 35),
    ("Business & Financial News", "business", 30),
    ("Education", "education", 25),
    ("Weather TV", "weather", 15),
    ("Travel & Exploration", "travel", 20),
    ("Culture", "culture", 20),
    ("Entertainment", "entertainment", 25),
]
FAVES = ("bbc","al jazeera","dw english","sky news","history","smithsonian",
         "wildlife","nature","earth","science","nasa","trace","xite","vevo",
         "music","orchestra","classic","pluto","filmrise","rakuten","movie")
ATTR = re.compile(r'([\w-]+)="([^"]*)"')
BAD = re.compile(r"\b(adult|xxx|porn|betting|gambling)\b", re.I)
MAX_TV, MAX_RADIO = 450, 35

def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "OSAS-LIVE/2.0 (public streams playlist aggregator)",
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(20_000_000).decode("utf-8-sig", errors="replace")

def parse(data: str, category: str = "") -> list[dict]:
    result, info = [], None
    for raw in data.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR.findall(line))
            info = {
                "name": line.rsplit(",", 1)[-1].strip(),
                "id": attrs.get("tvg-id","").lower().strip(),
                "group": attrs.get("group-title") or category,
            }
        elif info and line and not line.startswith("#"):
            if line.startswith(("https://","http://")):
                result.append({**info,"url":line})
            info = None
    return result

def priority(item: dict) -> tuple:
    name = item["name"].lower()
    fav = sum(1 for term in FAVES if term in name)
    # HTTPS streams have a better chance of working on iOS than plain HTTP.
    return (-fav, not item["url"].startswith("https://"), len(name), name)

def radio(max_items: int) -> list[dict]:
    for base in ("https://de1.api.radio-browser.info","https://nl1.api.radio-browser.info"):
        try:
            query = urllib.parse.urlencode({"language":"english","hidebroken":"true",
                "order":"votes","reverse":"true","limit":"500"})
            stations = json.loads(fetch(f"{base}/json/stations/search?{query}",20))
            if stations: break
        except Exception as exc:
            print("Radio source unavailable:",str(exc)[:100])
    else:
        return []
    scored=[]
    for s in stations:
        country=(s.get("countrycode") or "").upper()
        url=s.get("url_resolved") or s.get("url") or ""
        name=(s.get("name") or "").strip()
        if country not in {"NG","US","GB","CA","AU","IE","NZ"}: continue
        if not url.startswith("https://") or not name or BAD.search(name): continue
        score=int(s.get("votes") or 0)
        if any(x in (name+" "+(s.get("tags") or "")).lower() for x in ("news","talk","jazz","classical","afro","pop","hip hop")):
            score+=200
        scored.append((score,{"name":name,"id":"","group":"English Internet Radio","url":url}))
    seen=set(); output=[]
    for _,item in sorted(scored,key=lambda x:-x[0]):
        if item["url"] in seen:continue
        seen.add(item["url"])
        output.append(item)
        if len(output)>=max_items:break
    return output

def clean(text: str) -> str:
    return re.sub(r'[\r\n\t\x00-\x1f]+'," ",text).replace('"',"'").strip()

def build() -> None:
    # Preserve custom favorites (Afrobeats, classical, action, and global news).
    seed = parse((ROOT/"favorites.m3u").read_text(encoding="utf-8"))
    english = parse(fetch(f"{IPTV}/languages/eng.m3u"))
    if len(english)<50:
        raise RuntimeError("English playlist source returned too few channels; existing playlist preserved")
    english_urls={c["url"] for c in english}
    english_ids={c["id"] for c in english if c["id"]}
    category_feeds={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fetch,f"{IPTV}/categories/{code}.m3u"):(label,code)
                 for label,code,_ in CATEGORIES}
        for future in concurrent.futures.as_completed(futures):
            label,code=futures[future]
            try:
                category_feeds[code]=parse(future.result(),label)
            except Exception as exc:
                print("Category unavailable:",code,str(exc)[:130])
                category_feeds[code]=[]
    result=[]; seen_urls=set(); seen_ids=set()
    def add(item, group=None):
        url=item["url"]
        if url in seen_urls or (item["id"] and item["id"] in seen_ids):return False
        if not url.startswith(("https://","http://")) or BAD.search(item["name"]):return False
        obj=dict(item)
        if group: obj["group"]=group
        result.append(obj)
        seen_urls.add(url)
        if item["id"]: seen_ids.add(item["id"])
        return True
    for item in seed:add(item)
    candidates={}
    cat_counts={label:0 for label,_,_ in CATEGORIES}
    for label,code,cap in CATEGORIES:
        matches=[x for x in category_feeds[code] if x["url"] in english_urls or (x["id"] and x["id"] in english_ids)]
        matches.sort(key=priority)
        candidates[label]=matches
    # Give later categories a fair chance before the overall TV cap is filled.
    for label,code,cap in CATEGORIES:
        for item in candidates[label]:
            if cat_counts[label]>=min(8,cap) or len(result)>=MAX_TV:break
            if add(item,label):cat_counts[label]+=1
    for label,code,cap in CATEGORIES:
        for item in candidates[label]:
            if len(result)>=MAX_TV or cat_counts[label]>=cap:break
            if add(item,label):cat_counts[label]+=1
    if len(result)<60:
        raise RuntimeError("Too few TV channels produced; preserving previous playlist")
    radios=radio(MAX_RADIO)
    for item in radios:add(item)
    out=["#EXTM3U",f"# OSAS LIVE | Updated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
         "# Publicly indexed streams; geo restrictions, codec limitations, and availability vary."]
    for item in result:
        out.append(f'#EXTINF:-1 tvg-id="{clean(item["id"])}" group-title="{clean(item["group"])}",{clean(item["name"])}')
        out.append(item["url"])
    (ROOT/"playlist.m3u").write_text("\n".join(out)+"\n",encoding="utf-8")
    report={"generated_utc":datetime.now(timezone.utc).isoformat(),
        "total":len(result),"seeded_favorites":len(seed),
        "new_tv_by_category":cat_counts,"radio_added":len(radios),
        "source":"iptv-org English/category playlists + Radio Browser"}
    (ROOT/"status.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("OSAS LIVE entries:",len(result),"radio:",len(radios))

if __name__=="__main__":
    build()
