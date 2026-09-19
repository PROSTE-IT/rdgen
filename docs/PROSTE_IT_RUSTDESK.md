# PROSTE IT RustDesk — kontekst projektu

Ten dokument jest kanonicznym punktem startowym dla kolejnych sesji pracy nad
generatorem, klientem wsparcia i wspólną książką adresową. Nie przechowujemy tu
sekretów ani danych klientów.

## Repozytoria i aktywne gałęzie

Projekt składa się z trzech niezależnych repozytoriów Git:

| Element | Repozytorium | Aktywna gałąź | Rola |
| --- | --- | --- | --- |
| Generator | https://github.com/PROSTE-IT/rdgen | `feature/support-address-book-build` | Formularz i GitHub Actions budujące klientów |
| Klient wsparcia | https://github.com/PROSTE-IT/rustdesk | `feature/shared-address-book-client` | Fork RustDesk 1.4.9 używany tylko przez aplikację techników |
| Backend książki | https://github.com/PROSTE-IT/rdbk | `feature/shared-address-book` | Django API, PostgreSQL, Caddy, import i kopie zapasowe |

W obecnym lokalnym workspace repozytoria `rustdesk/` i `rdbk/` są osobnymi,
zagnieżdżonymi checkoutami. Nie są częścią historii Git repozytorium `rdgen`.

## Adresy i przepływ

- generator: `https://rdgen.prosteit.pl`
- backend książki adresowej: `https://rdbk.prosteit.pl`
- kompilacja z włączoną książką: Windows x64, RustDesk 1.4.9

Generator przekazuje `RDBK_API_URL` podczas kompilacji. Zwykłe kompilacje nadal
korzystają z oficjalnego RustDesk, a kompilacja aplikacji wsparcia pobiera gałąź
`PROSTE-IT/rustdesk@feature/shared-address-book-client`.

    rdgen -> GitHub Actions -> fork RustDesk -> aplikacja technika
                                          |
                                          v
                            https://rdbk.prosteit.pl
                                          |
                                          v
                             PostgreSQL + kopie zapasowe

## Stan zaimplementowany

### Generator

- przełącznik wspólnej książki adresowej i jej adres URL;
- walidacja tylko dla Windows x64 i wersji 1.4.9;
- warunkowe budowanie aplikacji wsparcia z forka PROSTE IT;
- optymalizacje cache kompilacji Windows;
- domyślny URL `https://rdbk.prosteit.pl`.

### Klient wsparcia

- osobna karta wspólnej książki adresowej;
- grupowanie urządzeń według klientów, wyszukiwanie i status online/offline;
- tworzenie, aktualizacja i usuwanie klientów oraz urządzeń;
- pytanie po sesji o dodanie nieznanego ID albo aktualizację istniejącego wpisu;
- synchronizacja książki pomiędzy aplikacjami techników.

Aktualnie token logowania istnieje tylko w pamięci procesu. Trwałe logowanie jest
częścią zatwierdzonego kolejnego etapu.

### Backend

- Django 5.2 LTS, Django REST Framework i PostgreSQL 17;
- wersjonowanie rekordów, wykrywanie konfliktów, soft delete i przywracanie;
- dziennik audytowy;
- import istniejącego skoroszytu Excel;
- Docker Compose, Caddy/HTTPS i mechanizm kopii zapasowych.

## Zatwierdzony kolejny etap — wykonać jako pełny zakres

Użytkownik nie chce ograniczonego MVP. Następne wdrożenie ma obejmować:

1. **Trwałe logowanie technika** — pierwsze logowanie loginem i hasłem, następnie
   odwoływalny token urządzenia przechowywany na Windows przy użyciu DPAPI /
   Credential Manager w zakresie `CurrentUser`. Ten sam komputer i to samo konto
   Windows nie wymagają ponownego logowania po restarcie aplikacji.
2. **Zarządzanie urządzeniami logowania** — administrator widzi stanowiska
   technika i może unieważnić dostęp konkretnego urządzenia.
3. **Pełne logi sesji** — technik, stanowisko technika, klient i urządzenie,
   RustDesk ID, początek, koniec, czas trwania, wersja aplikacji, wynik i notatka.
   Historia ma obsługiwać filtrowanie, CSV, audyt, retencję i poprawne domykanie
   sesji po awarii lub utracie połączenia.
4. **Automatyczne dane urządzenia** — po połączeniu zapisać hostname, użytkownika,
   platformę/system, wersję RustDesk i dostępne podstawowe dane. Formularz
   aktualizacji ma pokazywać wykryte różnice i proponować ich zatwierdzenie.
5. **Karta urządzenia** — dane książki, online/offline, `ostatnio widziany` w
   formacie `dd.mm.rrrr gg:mm`, podstawowe informacje techniczne, ostatni technik,
   ostatnia sesja, historia sesji/notatek oraz opcjonalne ostrzeżenie krytyczne.
6. **Obecność techników** — podczas aktywnej sesji inni widzą, kto jest połączony
   i od kiedy. Użyć heartbeatów i timeoutu, aby awaria aplikacji nie pozostawiała
   fałszywie aktywnej sesji. Przed drugim połączeniem pokazać ostrzeżenie.
7. **Blokowanie po rozłączeniu** — automatycznie blokować zdalny ekran/sesję po
   zakończeniu połączenia zarówno na komputerach, jak i na serwerach.
8. **Bezpieczeństwo i niezawodność** — kolejka i ponawianie zdarzeń przy chwilowym
   braku dostępu do backendu, brak przechowywania hasła, możliwość wylogowania i
   unieważnienia tokenu. Nie logować ekranu, klawiszy ani treści plików.

## Odłożony etap — rozmowa klienta z technikami przez Teams

Nie wdrażać w bieżącym etapie, ale zachować jako roadmapę.

- Klient wybiera w aplikacji „Porozmawiaj z technikiem”.
- Backend tworzy wątek na kanale Teams z klientem, urządzeniem, ID i wiadomością.
- Technik odpowiada bezpośrednio w Teams; klient widzi nazwę autora odpowiedzi,
  np. Wojtek, Marcin lub Mikołaj.
- Kolejne wiadomości pozostają w tym samym wątku, a zgłoszenie można przejąć i
  zamknąć.
- Integracja wymaga aplikacji/bota Teams, rejestracji w Microsoft Entra,
  odpowiednich zgód oraz Microsoft Graph change notifications. Jednokierunkowy
  webhook/Workflow nie wystarczy do pełnego czatu.
- Klient nie łączy się bezpośrednio z Teams. Ruch przechodzi przez backend RDBK,
  a instalacja klienta używa własnej kryptograficznej tożsamości — publiczne ID
  RustDesk nie może być jedynym uwierzytelnieniem.
- Szacunek pełnej, bezpiecznej wersji: około 4–6 dni pracy.

## Ważne decyzje

- Nie łączyć zmian do `master`, dopóki cały przepływ nie zostanie przetestowany.
- Aplikacja wsparcia jest osobnym wariantem; zwykli klienci nie dostają książki.
- Produkcyjna domena to `rdbk.prosteit.pl`; nie wracać do wariantu `rdbk-dev`.
- Nie commitować sekretów, tokenów GitHub, produkcyjnego `.env`, bazy, backupów
  ani skoroszytu klientów.
- Wpis istniejącego ID również ma wywoływać pytanie o aktualizację po sesji.
- Usunięcia książki są miękkie i możliwe do przywrócenia; zmiany są audytowane.

## Start kolejnej sesji

1. Przeczytać ten dokument w całości.
2. Sprawdzić `git status`, remote i aktywną gałąź osobno w każdym repozytorium.
3. Pobrać zmiany bez nadpisywania lokalnej pracy użytkownika.
4. Modyfikować i commitować tylko w repozytorium będącym właścicielem pliku.
5. Po zmianach uruchomić testy lokalne oraz sprawdzić GitHub Actions.
6. Aktualizować ten dokument, gdy zmienią się gałęzie, architektura lub roadmapa.

Podstawowe testy:

    # rdgen
    .\.venv\Scripts\python.exe manage.py test rdgenerator

    # rdbk
    cd rdbk
    .\.venv\Scripts\python.exe manage.py test

    # rustdesk — statyczna analiza zmienionych plików Flutter
    cd ..\rustdesk\flutter
    flutter analyze <lista-zmienionych-plików>

Po wypchnięciu zmian sprawdzić wynik odpowiedniego workflow GitHub Actions.
