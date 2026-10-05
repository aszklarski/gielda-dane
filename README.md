# Dane Giełda v0.0.21

Pliki świec MID (średnia BID i ASK) z Dukascopy dla projektu Giełda, aktualizowane przez budzik co 5 minut z harmonogramem GitHuba `*/5` jako zapasem (w praktyce co kilka godzin) i publikowane przez GitHub Pages. Dane nie są commitowane. Samo pobieranie nie wymaga kluczy; budzik używa tokenu Actions opisanego poniżej. W repozytorium są cztery jawne pliki: `pobierz_dane.py`, `konfiguracja.txt`, `README.md`, `.github/workflows/dane.yml` oraz zaszyfrowany `silnik.gpg`.

Źródło: Dukascopy freeserv chart/json3. Dane są udostępniane bez gwarancji; to nie jest porada inwestycyjna. Dukascopy blokuje boty i może w każdej chwili zablokować pobieranie z GitHuba. Dane publikowane przez to repozytorium są publiczne; decyzja o publikacji, zgodności z warunkami źródła i ryzyko należą do właściciela. Skrypt przedstawia się uczciwie nazwą projektu i adresem repozytorium, pobiera raz na przebieg bez ponownych prób i nie obchodzi blokad. HTTP 403/429 kończy zapytania; dane przestają się aktualizować.

Dukascopy bywa wolny (zaobserwowano około 16 s na odpowiedź); skrypt czeka najwyżej 30 s na zapytanie i nie ponawia. Para, która nie zdąży, ma plik `BLAD: przekroczony czas` do następnego przebiegu harmonogramu albo ręcznego uruchomienia.

Instrumenty, interwały i liczbę świec zmieniaj w `konfiguracja.txt`. Adres strony musi być równy `adres_danych` w Projekcie. Częstotliwość zmieniaj w `.github/workflows/dane.yml`: domyślnie `*/5 * * * *` (co 5 minut; GitHub uruchamia harmonogram z opóźnieniami i czasem pomija przebiegi, a minimum to 5 minut). Ręczne uruchomienie: Actions → Dane Giełda → Run workflow.

GitHub wyłącza harmonogram publicznego repozytorium po 60 dniach bez aktywności. Co około 50 dni wykonaj dowolny commit, np. edytuj ten README. Po wyłączeniu otwórz Actions → Enable workflow. Nie ma sztucznych commitów ani automatycznego podtrzymania.

**Ostrzeżenie:** 112 zapytań na pełny przebieg; budzik co 5 min to około 32 tys. na dobę, a harmonogram `*/5` teoretycznie do około 32 tys. na dobę to duże obciążenie serwisu, który blokuje boty; ryzyko blokady ponosi użytkownik.

Bezpiecznik 1: job `sprawdz` pyta API Actions o starsze, niezakończone przebiegi `dane.yml`. Gdy poprzedni przebieg jeszcze trwa, nowy kończy się bez pobierania, bez kolejki. Ponowienia są wyłączone zarówno w `sprawdz`, jak i niezależnie w pierwszym kroku jobu `dane`; uruchom nowy przebieg przez Run workflow.

Bezpiecznik 2: po HTTP 403/429 skrypt zapisuje czas UTC i kod w `blokada/czas.txt`, zachowywanym w cache Actions. Przez 60 minut od znacznika nie wykonuje zapytań, nie tworzy plików danych i nie publikuje (`publikuj=nie`, kod 0). Po tym czasie zwykły przebieg może wznowić pobieranie. Co najmniej jedna udana para pozwala opublikować częściowy wynik; bez udanych par kod 1 i brak publikacji.
Uszkodzony znacznik blokady jest pomijany z ostrzeżeniem, a pobieranie odbywa się normalnie.

Budżet przebiegu to 600 s, timeout zapytania 30 s, przerwa 1 s; brak ponowień. Po wyczerpaniu budżetu pozostałe pary dostają `BLAD: przerwano: limit czasu przebiegu` bez zapytań. Limit jobu: 15 minut. Przy stale wolnym źródle (> ok. 4,4 s na odpowiedź: 600 s budżetu na 112 zapytań minus 1 s przerwy) końcowe pary mogą stale mieć BLAD: skróć listę albo zmniejsz liczbę interwałów. Rotacja i przenoszenie ostatnich poprawnych plików pozostają poza zakresem.

Konfiguracja: 28 instrumentów × 1D, 4H, 15m = 84 pliki, po 150 świec; maksymalnie 90 par. Przykłady: `dane/EURUSD_4HOUR.txt`, `dane/EURUSD_15MIN.txt`.

Budzik tworzy nowy przebieg REST API (`workflow_dispatch`, `run_attempt = 1`), więc przechodzi obie blokady ponowień. Przy nakładaniu nowy przebieg kończy się bez pobierania, a starszy trwający dostarcza dane, bez kolejki. Job `sprawdz` ma limit 2 minut, job `dane` 15 minut. Przebieg wiszący w kolejce GitHuba na maszynę nadal blokuje następców aż do startu (GitHub anuluje go po 24 h): anuluj go ręcznie w Actions. Bezpiecznik 60 minut po 403/429 obowiązuje także budzik.

## Świece NY17 i historia 1H
4H i 1D powstają z MID świec `1HOUR` (dokładna średnia BID i ASK dla każdej godziny). Doba zaczyna się o 17:00 Nowego Jorku: 4H o 17, 21, 1, 5, 9 i 13 NY; 1D o 17 NY poprzedniego dnia sesji. Niedzielny wieczór należy do poniedziałku. Czas USA jest liczony regułą obowiązującą od 2007: druga niedziela marca, pierwsza niedziela listopada. Puste koszyki nie tworzą świec, najstarszy koszyk jest odrzucany, ostatni może być niepełny. Pozostałe interwały, w tym 15m, zachowują natywne świece i siatkę UTC.

Format to `GIELDA-DANE 3`. Pliki 4H/1D mają `sesja: NY17`, `dukascopy: 1HOUR` i `n` liczące godziny od `start_utc`; pozostałe mają `sesja: UTC`. Za źródłem znajdują się `historia: <liczba świec pełnej serii>` i `stan: brak|tak`. Przy stanie linie parametrów, świec `przed` i stanu silnika poprzedzają `kolumny`. Skrót obejmuje cały nagłówek i stan, sumy oraz liczba wierszy tylko okno. Pliki błędów mają wersję 3, bez pól sesji, historii i stanu. Czytnik v0.0.21 odrzuca wersję 2.

Workflow odtwarza cache `historia-` i uruchamia publikator z `--historia historia --pelne pelne`. Cache 1H ma 9600 wierszy w `<INSTR>_1HOUR_MID.txt`, nagłówek bez zmian: `GIELDA-HISTORIA 1 <instrument>`. Cache 15m ma 2000 wierszy w `<INSTR>_15MIN_MID.txt`, nagłówek `GIELDA-HISTORIA 1 <instrument> 15MIN`. Wiersze `ms,o,h,l,c` są rosnące, ceny Decimal. 4H i 1D są agregowane ze wszystkich godzin cache; najstarszy koszyk odrzucany. Konfiguracja 4H/1D wymaga `24*swiece+400 <= HISTORIA_1H`.

Ogon pustego cache: `limit=min(5000,pojemność)`; istniejącego: sufit czasu od najnowszej świecy podzielonego przez krok plus 3. Limit większy od 5000 oznacza pełne pobranie. Brzegi BID/ASK wyrównujemy jak dotąd, z logiem `wyrownano BID/ASK`. Brak nakładki świeżego ogona z cache powoduje błąd i usunięcie cache; następny przebieg pobiera pełny ogon. Po scaleniu mniej niż pojemność minus 48 wierszy uruchamia najwyżej jedno dociąganie BID/ASK: znacznik najstarszej świecy minus 1 ms, limit do 5000 brakujących wierszy. Dopisywane są wyłącznie starsze świece; błąd daje ostrzeżenie bez ponowienia. Blokada 403/429 zatrzymuje dalsze zapytania. Zawsze przycinamy do pojemności.

Przy pełnym cache jest 112 zapytań na przebieg (28 symboli × 2 bazy × BID/ASK). Zimny albo krótki cache dodaje najwyżej 2 zapytania na bazę i symbol (maksymalnie 224 łącznie). 1H po zimnym starcie potrzebuje ogona 5000 i jednej strony do 4600; 15m może zapełnić się z jednego ogona 2000. Liczby zależą od długości odpowiedzi dostawcy i dostępnego budżetu czasu.

Pliki Pages zawierają ostatnie 150 świec. Katalog `pelne/` zawiera wszystkie świece i nie trafia na Pages ani do cache. Silnik z `--pelne pelne` dopisuje zweryfikowany stan do plików okna, a dopiero potem liczy `wyniki.txt`. Log `stany:` podaje liczby stanów, czas, długości historii i przełamania przed oknem. Brak odpowiednika, krótka historia albo różne parametry aktywnych strategii pozostawiają `stan: brak`.

## Wyniki analizy
Strona główna zawiera link do `wyniki.txt` (`GIELDA-WYNIKI 2`). Po pobraniu świec workflow odszyfrowuje `silnik.gpg` kluczem z sekretu Actions `KLUCZ_SILNIKA` i liczy wyniki wszystkich par. Kod oraz strategie są prywatne; do repozytorium i jego historii trafia wyłącznie szyfr, nigdy jawna paczka ani klucz. Szyfr aktualizuje narzędzie z prywatnego projektu; nie edytuj go ręcznie.

Odszyfrowany katalog leży w `$RUNNER_TEMP/silnik`, poza stroną i checkoutem, jest usuwany po analizie i nie trafia do cache ani artefaktów. Log zawiera tylko liczbę wierszy i błędów, czas oraz skróty kodu i plików. Brak klucza/paczki albo błąd odszyfrowania daje plik błędu `silnik niedostepny (paczka lub klucz)`; błąd silnika również daje plik błędu zamiast starych wyników. Przed publikacją dozwolone są tylko `index.html`, `wyniki.txt` i `dane/*.txt`. Nie dodawaj wyzwalacza `pull_request` udostępniającego sekret.

Skróty `kod` i `pliki` z nagłówka porównaj z `diagnostyka` w ChatGPT. Świece mają format `GIELDA-DANE 3`; analiza nie dodaje zapytań do źródła. Linia `wyniki:` pozwala zmierzyć sam czas analizy, `podsumowanie:` — pobieranie (112 zapytań przy pełnej konfiguracji).

## Budzik (cron-job.org)
1. Utwórz token fine-grained w GitHub: Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token. Wpisz nazwę i ważność około roku. Repository access: Only select repositories → `aszklarski/gielda-dane`. Permissions: Actions = Read and write, pozostałe brak; GitHub obowiązkowo dodaje Metadata: Read-only. Skopiuj token teraz — jest pokazywany tylko raz.
2. Samodzielnie załóż konto w cron-job.org. Wybierz Create cronjob. URL: `https://api.github.com/repos/aszklarski/gielda-dane/actions/workflows/dane.yml/dispatches`. Ustaw własny harmonogram: minuty **1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56** każdej godziny, każdego dnia.
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
