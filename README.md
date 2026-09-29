# Dane Giełda v0.0.7

Pliki świec MID (średnia BID i ASK) z Dukascopy dla projektu Giełda, aktualizowane przez budzik co 15 minut z harmonogramem GitHuba `*/5` jako zapasem (w praktyce co kilka godzin) i publikowane przez GitHub Pages. Dane nie są commitowane. Samo pobieranie nie wymaga kluczy; budzik używa tokenu Actions opisanego poniżej. W repozytorium są tylko cztery pliki: `pobierz_dane.py`, `konfiguracja.txt`, `README.md`, `.github/workflows/dane.yml`.

Źródło: Dukascopy freeserv chart/json3. Dane są udostępniane bez gwarancji; to nie jest porada inwestycyjna. Dukascopy blokuje boty i może w każdej chwili zablokować pobieranie z GitHuba. Dane publikowane przez to repozytorium są publiczne; decyzja o publikacji, zgodności z warunkami źródła i ryzyko należą do właściciela. Skrypt przedstawia się uczciwie nazwą projektu i adresem repozytorium, pobiera raz na przebieg bez ponownych prób i nie obchodzi blokad. HTTP 403/429 kończy zapytania; dane przestają się aktualizować.

Dukascopy bywa wolny (zaobserwowano około 16 s na odpowiedź); skrypt czeka najwyżej 30 s na zapytanie i nie ponawia. Para, która nie zdąży, ma plik `BLAD: przekroczony czas` do następnego przebiegu harmonogramu albo ręcznego uruchomienia.

Instrumenty, interwały i liczbę świec zmieniaj w `konfiguracja.txt`. Adres strony musi być równy `adres_danych` w Projekcie. Częstotliwość zmieniaj w `.github/workflows/dane.yml`: domyślnie `*/5 * * * *` (co 5 minut; GitHub uruchamia harmonogram z opóźnieniami i czasem pomija przebiegi, a minimum to 5 minut). Ręczne uruchomienie: Actions → Dane Giełda → Run workflow.

GitHub wyłącza harmonogram publicznego repozytorium po 60 dniach bez aktywności. Co około 50 dni wykonaj dowolny commit, np. edytuj ten README. Po wyłączeniu otwórz Actions → Enable workflow. Nie ma sztucznych commitów ani automatycznego podtrzymania.

**Ostrzeżenie:** 168 zapytań na przebieg; budzik co 15 min to około 16 tys. na dobę, a harmonogram `*/5` teoretycznie do około 48 tys. na dobę to duże obciążenie serwisu, który blokuje boty; ryzyko blokady ponosi użytkownik.

Bezpiecznik 1: job `sprawdz` pyta API Actions o starsze, niezakończone przebiegi `dane.yml`. Gdy poprzedni przebieg jeszcze trwa, nowy kończy się bez pobierania, bez kolejki. Ponowienia są wyłączone zarówno w `sprawdz`, jak i niezależnie w pierwszym kroku jobu `dane`; uruchom nowy przebieg przez Run workflow.

Bezpiecznik 2: po HTTP 403/429 skrypt zapisuje czas UTC i kod w `blokada/czas.txt`, zachowywanym w cache Actions. Przez 60 minut od znacznika nie wykonuje zapytań, nie tworzy plików danych i nie publikuje (`publikuj=nie`, kod 0). Po tym czasie zwykły przebieg może wznowić pobieranie. Co najmniej jedna udana para pozwala opublikować częściowy wynik; bez udanych par kod 1 i brak publikacji.
Uszkodzony znacznik blokady jest pomijany z ostrzeżeniem, a pobieranie odbywa się normalnie.

Budżet przebiegu to 600 s, timeout zapytania 30 s, przerwa 1 s; brak ponowień. Po wyczerpaniu budżetu pozostałe pary dostają `BLAD: przerwano: limit czasu przebiegu` bez zapytań. Limit jobu: 15 minut. Przy stale wolnym źródle (> ok. 2,5 s na odpowiedź: 600 s budżetu na 168 zapytań minus 1 s przerwy) końcowe pary mogą stale mieć BLAD: skróć listę albo zmniejsz liczbę interwałów. Rotacja i przenoszenie ostatnich poprawnych plików pozostają poza zakresem.

Konfiguracja: 28 instrumentów × 1D, 4H, 15m = 84 pliki, po 150 świec; maksymalnie 90 par. Przykłady: `dane/EURUSD_4HOUR.txt`, `dane/EURUSD_15MIN.txt`.

Budzik tworzy nowy przebieg REST API (`workflow_dispatch`, `run_attempt = 1`), więc przechodzi obie blokady ponowień. Przy nakładaniu nowy przebieg kończy się bez pobierania, a starszy trwający dostarcza dane, bez kolejki. Job `sprawdz` ma limit 2 minut, job `dane` 15 minut. Przebieg wiszący w kolejce GitHuba na maszynę nadal blokuje następców aż do startu (GitHub anuluje go po 24 h): anuluj go ręcznie w Actions. Bezpiecznik 60 minut po 403/429 obowiązuje także budzik.

## Budzik (cron-job.org)
1. Utwórz token fine-grained w GitHub: Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token. Wpisz nazwę i ważność około roku. Repository access: Only select repositories → `aszklarski/gielda-dane`. Permissions: Actions = Read and write, pozostałe brak; GitHub obowiązkowo dodaje Metadata: Read-only. Skopiuj token teraz — jest pokazywany tylko raz.
2. Samodzielnie załóż konto w cron-job.org. Wybierz Create cronjob. URL: `https://api.github.com/repos/aszklarski/gielda-dane/actions/workflows/dane.yml/dispatches`. Ustaw własny harmonogram: minuty **1, 16, 31, 46** każdej godziny, każdego dnia.
3. W Advanced ustaw metodę POST i nagłówki:
   - `Authorization: Bearer <token>`
   - `Accept: application/vnd.github+json`
   - `X-GitHub-Api-Version: 2022-11-28`
   - zalecany `Content-Type: application/json`
   Treść żądania: `{"ref":"main"}`. Oczekiwana odpowiedź: **204**.
4. Sprawdź „Test run” w cron-job.org → 204. W GitHub → Actions → Dane Giełda powinien pojawić się nowy przebieg ze zdarzeniem `workflow_dispatch`. Po zakończeniu sprawdź `index.html` z nowym `aktualizacja_utc` i 84 plikami GOTOWE.

Awarie:
- 401 → token wygasł lub jest błędny; utwórz nowy i podmień nagłówek.
- 403/404 → brak uprawnienia Actions lub zły adres/repozytorium.
- 422 → workflow wyłączony (Actions → Enable workflow) albo zła gałąź.
- GitHub wyłącza workflow po 60 dniach bez commitów; co około 50 dni wykonaj dowolny commit.

Token leży w serwisie zewnętrznym. Ma tylko Actions na jednym repozytorium: może uruchamiać/anulować przebiegi, nie zmienia kodu. Przy podejrzeniu wycieku usuń token w GitHubie.
