# Dane Giełda v0.0.4

Pliki świec MID (średnia BID i ASK) z Dukascopy dla projektu Giełda, aktualizowane co godzinę i publikowane przez GitHub Pages. Dane nie są commitowane. Repozytorium nie wymaga danych osobowych ani kluczy.

Źródło: Dukascopy freeserv chart/json3. Dane są udostępniane bez gwarancji; to nie jest porada inwestycyjna. Dukascopy blokuje boty i może w każdej chwili zablokować pobieranie z GitHuba. Dane publikowane przez to repozytorium są publiczne; decyzja o publikacji, zgodności z warunkami źródła i ryzyko należą do właściciela. Skrypt przedstawia się uczciwie nazwą projektu i adresem repozytorium, pobiera raz na przebieg bez ponownych prób i nie obchodzi blokad. HTTP 403/429 kończy zapytania; dane przestają się aktualizować.

Dukascopy bywa wolny (zaobserwowano około 16 s na odpowiedź); skrypt czeka najwyżej 60 s na zapytanie i nie ponawia. Para, która nie zdąży, ma plik `BLAD: przekroczony czas` do następnego przebiegu harmonogramu albo ręcznego uruchomienia.

Instrumenty, interwały i liczbę świec zmieniaj w `konfiguracja.txt`. Adres strony musi być równy `adres_danych` w Projekcie. Częstotliwość zmieniaj w `.github/workflows/dane.yml`: domyślnie `7 * * * *` (co godzinę), dla interwałów poniżej 1H `7,22,37,52 * * * *` (co 15 minut). Ręczne uruchomienie: Actions → Dane Giełda → Run workflow.

GitHub wyłącza harmonogram publicznego repozytorium po 60 dniach bez aktywności. Co około 50 dni wykonaj dowolny commit, np. edytuj ten README. Po wyłączeniu otwórz Actions → Enable workflow. Nie ma sztucznych commitów ani automatycznego podtrzymania.
