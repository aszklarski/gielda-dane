# Dane Giełda v0.0.6

Pliki świec MID (średnia BID i ASK) z Dukascopy dla projektu Giełda, aktualizowane co 5 minut i publikowane przez GitHub Pages. Dane nie są commitowane. Repozytorium nie wymaga danych osobowych ani kluczy.

Źródło: Dukascopy freeserv chart/json3. Dane są udostępniane bez gwarancji; to nie jest porada inwestycyjna. Dukascopy blokuje boty i może w każdej chwili zablokować pobieranie z GitHuba. Dane publikowane przez to repozytorium są publiczne; decyzja o publikacji, zgodności z warunkami źródła i ryzyko należą do właściciela. Skrypt przedstawia się uczciwie nazwą projektu i adresem repozytorium, pobiera raz na przebieg bez ponownych prób i nie obchodzi blokad. HTTP 403/429 kończy zapytania; dane przestają się aktualizować.

Dukascopy bywa wolny (zaobserwowano około 16 s na odpowiedź); skrypt czeka najwyżej 30 s na zapytanie i nie ponawia. Para, która nie zdąży, ma plik `BLAD: przekroczony czas` do następnego przebiegu harmonogramu albo ręcznego uruchomienia.

Instrumenty, interwały i liczbę świec zmieniaj w `konfiguracja.txt`. Adres strony musi być równy `adres_danych` w Projekcie. Częstotliwość zmieniaj w `.github/workflows/dane.yml`: domyślnie `*/5 * * * *` (co 5 minut; GitHub uruchamia harmonogram z opóźnieniami i czasem pomija przebiegi, a minimum to 5 minut). Ręczne uruchomienie: Actions → Dane Giełda → Run workflow.

GitHub wyłącza harmonogram publicznego repozytorium po 60 dniach bez aktywności. Co około 50 dni wykonaj dowolny commit, np. edytuj ten README. Po wyłączeniu otwórz Actions → Enable workflow. Nie ma sztucznych commitów ani automatycznego podtrzymania.

**Ostrzeżenie:** około 112 zapytań co 5 minut (do około 32 tys. na dobę) to duże obciążenie serwisu, który blokuje boty; ryzyko blokady ponosi użytkownik.

Bezpiecznik 1: job `sprawdz` pyta API Actions o starsze, niezakończone przebiegi `dane.yml`. Gdy poprzedni przebieg jeszcze trwa, nowy kończy się bez pobierania, bez kolejki. Ponowienia są wyłączone zarówno w `sprawdz`, jak i niezależnie w pierwszym kroku jobu `dane`; uruchom nowy przebieg przez Run workflow.

Bezpiecznik 2: po HTTP 403/429 skrypt zapisuje czas UTC i kod w `blokada/czas.txt`, zachowywanym w cache Actions. Przez 60 minut od znacznika nie wykonuje zapytań, nie tworzy plików danych i nie publikuje (`publikuj=nie`, kod 0). Po tym czasie zwykły przebieg może wznowić pobieranie. Co najmniej jedna udana para pozwala opublikować częściowy wynik; bez udanych par kod 1 i brak publikacji.
Uszkodzony znacznik blokady jest pomijany z ostrzeżeniem, a pobieranie odbywa się normalnie.

Budżet przebiegu to 540 s, timeout zapytania 30 s, przerwa 1 s; brak ponowień. Po wyczerpaniu budżetu pozostałe pary dostają `BLAD: przerwano: limit czasu przebiegu` bez zapytań. Limit jobu: 15 minut. Przy stale wolnym źródle (> 4 s na odpowiedź) końcowe pary mogą stale mieć BLAD: skróć listę albo zmniejsz liczbę interwałów. Rotacja i przenoszenie ostatnich poprawnych plików pozostają poza zakresem.

Konfiguracja: 28 instrumentów × 1D i 4H = 56 plików, po 150 świec; maksymalnie 60 par. Przykład: `dane/EURUSD_4HOUR.txt`.
