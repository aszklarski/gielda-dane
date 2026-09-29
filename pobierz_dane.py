"""Świece MID Dukascopy; jawny klient, bez ponawiania i obchodzenia blokad."""

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

WERSJA = "0.0.7"
LIMIT_CZASU = 30
BUDZET_PRZEBIEGU = 600
MAPA_INTERWALOW = {
    "1m": ("1MIN", 60), "5m": ("5MIN", 300), "15m": ("15MIN", 900),
    "30m": ("30MIN", 1800), "1H": ("1HOUR", 3600), "4H": ("4HOUR", 14400),
    "1D": ("1DAY", 86400), "1W": ("1WEEK", 604800), "1M": ("1MONTH", "M"),
}
INSTRUMENT = r"[A-Z0-9]+(?:\.[A-Z0-9]+)*/[A-Z0-9]+(?:\.[A-Z0-9]+)*"
ZNAKI = re.compile(r"[A-Za-z0-9 \n:.,/=()+_?\-]*\Z")
BRAK = "brak danych (zly instrument lub interwal?)"


def poprawny_adres(wartosc):
    if not isinstance(wartosc, str) or not wartosc or any(
            ord(c) < 33 or ord(c) > 126 or c in "\\%?#" for c in wartosc):
        return False
    try:
        a = urlsplit(wartosc)
        host = a.hostname or ""
        return (a.scheme == "https" and re.fullmatch(r"[a-z0-9-]+\.github\.io", host) is not None
                and a.netloc.lower() == host and not a.query and not a.fragment
                and re.fullmatch(r"/(?:[A-Za-z0-9._-]+/)?", a.path) is not None
                and a.path not in ("/./", "/../"))
    except ValueError:
        return False


def adres_repo(adres_strony):
    a = urlsplit(adres_strony)
    login = a.hostname.split(".")[0]
    return "https://github.com/" + login + "/" + (a.path.strip("/") or login + ".github.io")


def nazwa_pliku(instrument, interwal):
    return "dane/" + instrument.replace("/", "") + "_" + MAPA_INTERWALOW[interwal][0] + ".txt"


def wczytaj_konfiguracje(tekst):
    konf, bledy = {}, []
    for linia in tekst.splitlines():
        if not linia.strip() or linia.lstrip().startswith("#"):
            continue
        if ": " not in linia:
            bledy.append("konfiguracja: oczekiwano klucz: wartość")
            continue
        k, v = linia.split(": ", 1)
        if k not in ("adres_strony", "swiece", "instrumenty", "interwaly"):
            bledy.append(k + ": nieznany klucz")
        if k in konf:
            bledy.append(k + ": powtórzony klucz")
        konf[k] = v
    for k in ("adres_strony", "swiece", "instrumenty", "interwaly"):
        if k not in konf:
            bledy.append(k + ": brak klucza")
    if not poprawny_adres(konf.get("adres_strony")):
        bledy.append("adres_strony: adres niezgodny z regułą D39")
    v = konf.get("swiece", "")
    cyfry = v.lstrip("0")
    if not re.fullmatch(r"[0-9]+", v) or not 1 <= len(cyfry) <= 3 or not 50 <= int(cyfry) <= 300:
        bledy.append("swiece: wymagana liczba całkowita 50–300")
    else:
        konf["swiece"] = int(cyfry)
    for k in ("instrumenty", "interwaly"):
        vs = [v.strip() for v in konf.get(k, "").split(",")]
        konf[k] = vs
        if not all(vs):
            bledy.append(k + ": wymagana niepusta lista")
        if len(set(vs)) != len(vs):
            bledy.append(k + ": powtórzona wartość")
        for v in vs:
            if k == "instrumenty" and not re.fullmatch(INSTRUMENT, v):
                bledy.append(k + ": niepoprawny instrument " + v)
            if k == "interwaly" and v not in MAPA_INTERWALOW:
                bledy.append(k + ": niedozwolony interwał " + v + (" (brak w Dukascopy)" if v == "2H" else ""))
    nazwy = [v.replace("/", "").casefold() for v in konf["instrumenty"]]
    if len(set(nazwy)) != len(nazwy):
        bledy.append("instrumenty: powtórzona nazwa pliku")
    if len(konf["instrumenty"]) * len(konf["interwaly"]) > 90:
        bledy.append("instrumenty: liczba par przekracza 90")
    return konf, bledy


def zapytanie(instrument, kod, strona, limit, teraz_ms, adres_strony):
    url = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument="
           + quote(instrument, safe="") + f"&offer_side={strona}&interval={kod}&limit={limit}"
           + f"&time_direction=P&timestamp={teraz_ms}&jsonp=_gielda")
    return Request(url, headers={"User-Agent": f"gielda-dane/{WERSJA} (+{adres_repo(adres_strony)})",
                                 "Referer": adres_strony, "Accept": "*/*"})


def odpowiedz_na_wiersze(tekst):
    try:
        m = re.fullmatch(r"\s*_gielda\((.*)\);?\s*", tekst, re.S)
        if not m:
            return "niepoprawna odpowiedz"
        wiersze = json.loads(m[1], parse_float=Decimal, parse_int=Decimal)
        if wiersze == [] or wiersze == [None]:
            return BRAK
        if not isinstance(wiersze, list):
            return "niepoprawna odpowiedz"
        poprzedni = None
        for w in wiersze:
            if not isinstance(w, list) or len(w) != 6 or not all(
                    isinstance(v, Decimal) and v.is_finite() for v in w):
                return "niepoprawna odpowiedz"
            t, o, h, l, c, _ = w
            if (t != int(t) or (poprzedni is not None and t >= poprzedni)
                    or min(o, h, l, c) <= 0 or h < max(o, c, l) or l > min(o, c)):
                return "niepoprawna odpowiedz"
            poprzedni = t
        return list(reversed(wiersze))
    except (ValueError, TypeError, ArithmeticError):
        return "niepoprawna odpowiedz"


def policz_mid(bid, ask, interwal):
    if not bid or [w[0] for w in bid] != [w[0] for w in ask]:
        return "niespojne dane BID/ASK"
    krok = MAPA_INTERWALOW[interwal][1]
    czasy = []
    try:
        for w in bid:
            ms = w[0]
            if ms % 60000:
                return "niewyrownane swiece"
            dt = datetime.fromtimestamp(int(ms) // 1000, timezone.utc)
            if ((interwal == "1W" and (dt.weekday() != 0 or dt.hour or dt.minute))
                    or (interwal == "1M" and (dt.day != 1 or dt.hour or dt.minute))
                    or (interwal not in ("1W", "1M") and int(ms) // 1000 % krok)):
                return "niewyrownane swiece"
            czasy.append(dt)
        if any(a >= b for a, b in zip(czasy, czasy[1:])):
            return "niespojne dane BID/ASK"
        start = czasy[0]
        n = [(t.year - start.year) * 12 + t.month - start.month if krok == "M"
             else int((t - start).total_seconds()) // krok for t in czasy]
        for t, indeks in zip(czasy, n):
            if krok == "M":
                y, m = divmod(start.year * 12 + start.month - 1 + indeks, 12)
                assert t == datetime(y, m + 1, 1, tzinfo=timezone.utc)
            else:
                assert int((t - start).total_seconds()) == indeks * krok
        # Precyzja obejmuje pełną rozpiętość wykładników obu stron i dzielenie przez 2.
        liczby = [v for w in bid + ask for v in w[1:5]]
        precyzja = max(v.adjusted() for v in liczby) - min(v.as_tuple().exponent for v in liczby) + 4
        with localcontext() as ctx:
            ctx.prec = max(28, precyzja)
            mid = [[(b + a) / 2 for b, a in zip(bw[1:5], aw[1:5])] for bw, aw in zip(bid, ask)]
            d = max(0, max(-v.normalize().as_tuple().exponent for w in mid for v in w))
            kolumny = [[int(w[j] * 10 ** d) for w in mid] for j in range(4)]
        return (start, n, *kolumny, d)
    except (ValueError, OverflowError, ArithmeticError):
        return "niewyrownane swiece"


def czas_utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else "brak"


def bezpieczny_tekst(tekst):
    if not ZNAKI.fullmatch(tekst):
        raise ValueError("niedozwolone znaki w pliku danych")
    return tekst


def plik_danych(instrument, interwal, mid, aktualizacja, ostatni_commit=None):
    start, n, o, h, l, c, d = mid
    punkt = "1" if d == 0 else "0." + "0" * (d - 1) + "1"
    linie = ["GIELDA-DANE 1", f"instrument: {instrument}", f"interwal: {interwal}",
             f"dukascopy: {MAPA_INTERWALOW[interwal][0]}", "cena: MID=(BID+ASK)/2", f"punkt: {punkt}",
             f"start_utc: {start:%Y-%m-%dT%H:%MZ}", f"krok: {interwal}",
             f"aktualizacja_utc: {czas_utc(aktualizacja)}", f"ostatni_commit_utc: {czas_utc(ostatni_commit)}",
             "zrodlo: Dukascopy freeserv chart/json3", "kolumny: n,o,h,l,c"]
    linie += [",".join(map(str, w)) for w in zip(n, o, h, l, c)]
    kanon = "\n".join(linie) + "\n"
    skrot = hashlib.sha256(kanon.encode("ascii")).hexdigest()[:16]
    return bezpieczny_tekst(kanon + f"kontrola: wiersze={len(n)} suma_o={sum(o)} suma_h={sum(h)} "
                           + f"suma_l={sum(l)} suma_c={sum(c)} skrot={skrot}\nstatus: GOTOWE\n")


def plik_bledu(instrument, interwal, powod, aktualizacja, ostatni_commit=None):
    return bezpieczny_tekst("\n".join(["GIELDA-DANE 1", f"instrument: {instrument}",
        f"interwal: {interwal}", f"dukascopy: {MAPA_INTERWALOW[interwal][0]}",
        f"aktualizacja_utc: {czas_utc(aktualizacja)}", f"ostatni_commit_utc: {czas_utc(ostatni_commit)}",
        "zrodlo: Dukascopy freeserv chart/json3", f"status: BLAD: {powod}", ""]))


def output_github(klucz, wartosc):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"{klucz}={wartosc}\n")


def main(argv=None, otworz=urlopen, spij=time.sleep, teraz=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--konfiguracja", default="konfiguracja.txt")
    parser.add_argument("--wyjscie", default="_site")
    parser.add_argument("--ostatni-commit", default="")
    parser.add_argument("--blokada", help="plik znacznika blokady HTTP 403/429")
    args = parser.parse_args(argv)
    output_github("publikuj", "nie")
    aktualizacja = teraz or datetime.now(timezone.utc)
    if args.blokada and Path(args.blokada).exists():
        try:
            znacznik = json.loads(Path(args.blokada).read_text(encoding="utf-8"))
            czas = datetime.fromisoformat(znacznik["czas_utc"].replace("Z", "+00:00"))
            if czas.tzinfo is None or znacznik["kod"] not in (403, 429):
                raise ValueError("niepoprawny znacznik")
            if aktualizacja < czas + timedelta(minutes=60):
                print(f"PRZERWA po blokadzie Dukascopy (HTTP {znacznik['kod']}, {czas_utc(czas)} UTC): "
                      f"bez zapytań do {czas_utc(czas + timedelta(minutes=60))} UTC")
                return 0
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            prefiks = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "UWAGA: "
            print(prefiks + "niepoprawny znacznik blokady — pomijam")
    try:
        konf, bledy = wczytaj_konfiguracje(Path(args.konfiguracja).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        konf, bledy = {}, ["konfiguracja: nie można odczytać pliku UTF-8"]
    commit = None
    if args.ostatni_commit:
        try:
            commit = datetime.fromisoformat(args.ostatni_commit.replace("Z", "+00:00"))
            if commit.tzinfo is None:
                raise ValueError("brak strefy")
            commit = commit.astimezone(timezone.utc)
        except ValueError:
            bledy.append("ostatni_commit: wymagany czas ISO 8601 z przesunięciem")
    if bledy:
        for blad in bledy:
            print("BŁĄD konfiguracji: " + blad)
        return 2
    wyjscie = Path(args.wyjscie)
    (wyjscie / "dane").mkdir(parents=True, exist_ok=True)
    blokada, zapytan, udane, indeks = None, 0, 0, []
    aktualizacja = teraz or datetime.now(timezone.utc)
    start = time.monotonic()
    for instrument in konf["instrumenty"]:
        for interwal in konf["interwaly"]:
            aktualizacja = teraz or datetime.now(timezone.utc)
            powod = f"przerwano po blokadzie zrodla (HTTP {blokada})" if blokada else None
            strony = []
            if not powod:
                for strona in ("B", "A"):
                    if time.monotonic() - start >= BUDZET_PRZEBIEGU:
                        powod = "przerwano: limit czasu przebiegu"
                        break
                    if zapytan:
                        spij(1)
                    if time.monotonic() - start >= BUDZET_PRZEBIEGU:
                        powod = "przerwano: limit czasu przebiegu"
                        break
                    zapytan += 1
                    req = zapytanie(instrument, MAPA_INTERWALOW[interwal][0], strona,
                                    konf["swiece"], int(aktualizacja.timestamp() * 1000), konf["adres_strony"])
                    try:
                        with otworz(req, timeout=LIMIT_CZASU) as response:
                            wiersze = odpowiedz_na_wiersze(response.read().decode("ascii"))
                        if isinstance(wiersze, str):
                            powod = wiersze
                        else:
                            strony.append(wiersze[-konf['swiece']:])
                    except HTTPError as exc:
                        powod = {403: "odmowa dostepu (HTTP 403)", 429: "blokada lub limit zapytan (HTTP 429)"}.get(exc.code, f"HTTP {exc.code}")
                        if exc.code in (403, 429):
                            blokada = exc.code
                            if args.blokada:
                                plik = Path(args.blokada)
                                plik.parent.mkdir(parents=True, exist_ok=True)
                                plik.write_text(json.dumps({"czas_utc": czas_utc(teraz or datetime.now(timezone.utc)),
                                                           "kod": exc.code}) + "\n", encoding="utf-8")
                                output_github("blokada", "tak")
                        exc.close()
                    except TimeoutError:
                        powod = "przekroczony czas"
                    except URLError as exc:
                        powod = "przekroczony czas" if isinstance(exc.reason, TimeoutError) else "blad sieci"
                    except OSError:
                        powod = "blad sieci"
                    except (UnicodeError, ValueError):
                        powod = "niepoprawna odpowiedz"
                    if powod:
                        break
            if not powod:
                mid = policz_mid(*strony, interwal)
                if isinstance(mid, str):
                    powod = mid
            nazwa = nazwa_pliku(instrument, interwal)
            if powod:
                tekst = plik_bledu(instrument, interwal, powod, aktualizacja, commit)
                print(f"BLAD {nazwa}: {powod}")
                if os.environ.get("GITHUB_ACTIONS") == "true":
                    print(f"::warning::{nazwa}: {powod}")
            else:
                tekst = plik_danych(instrument, interwal, mid, aktualizacja, commit)
                udane += 1
                print(f"OK {nazwa} {len(mid[1])} swiec")
            (wyjscie / nazwa).write_bytes(tekst.encode("ascii"))
            status = "BLAD: " + powod if powod else "GOTOWE"
            indeks.append(f'<tr><td><a href="{html.escape(nazwa)}">{html.escape(nazwa)}</a></td><td>{html.escape(status)}</td></tr>')
    strona = ('<!doctype html>\n<html lang="pl"><meta charset="ascii"><title>Gielda - dane</title>'
              + '<h1>Gielda - dane</h1><p>aktualizacja_utc: ' + czas_utc(aktualizacja) + '</p><table>'
              + '<tr><th>Plik</th><th>Status</th></tr>' + "\n".join(indeks) + '</table></html>\n')
    (wyjscie / "index.html").write_bytes(strona.encode("ascii"))
    if udane:
        output_github("publikuj", "tak")
    return 0 if udane else 1


if __name__ == "__main__":
    sys.exit(main())
