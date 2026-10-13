# Novi FlowOS Assistant

Lekka aplikacja Docker na ZimaOS/CasaOS. Panel projektu z **wyborem telefonu i bazy Androida**, **listą APK**, **diagnozowaniem błędów** i wykrywaniem folderów. Nie zmienia istniejącego buildu, nie uruchamia kompilacji i nie instaluje niczego na telefonie. Nie potrzebuje dostępu do Docker socket ani kluczy SSH.

## Co działa

- Wybór telefonu z listy i rozpoznawanie nazwy modelu przez lokalne AI. Telefon rozpoznany przez AI jest propozycją: aplikacja potwierdza istnienie repozytorium, zanim użyje wyniku. Brak repozytorium nie zostaje ukryty.
- Wersje Androida: 7.1, 8.0, 8.1, 9, 10, 11, 12.0, 12L i 13–16. Gałęzie są sprawdzane online; menu nie oznacza dostępności każdej wersji dla każdego telefonu. Android 12.0 i 12L to osobne wybory.
- Lista aplikacji z `/DATA/FlowOS/apps` oraz osobno dodanych APK. Dodawanie sprawdza manifest i sumę SHA-256, odrzuca duplikaty i przesyła plik strumieniowo (limit 128 MB). To kontrola struktury, nie weryfikacja podpisu ani bezpieczeństwa aplikacji.
- Sprawdzenie istnienia gałęzi urządzenia, zależności, kernela i repozytorium vendor; zapis konkretnego commit SHA w wyniku. Brak gałęzi jest jawny, a błąd sieci nie jest traktowany jako brak wsparcia.
- Osobne sprawdzenie konkretnej bazy AOSP w serwerze źródeł Google. To historyczne tagi startowe, nie automatyczny dobór najnowszego zestawu poprawek. Źródła platformy i źródła sprzętowe są wyświetlane osobno.
- Rekurencyjny odczyt `lineage.dependencies` z wersji przypiętej do sprawdzonego commita. To badanie źródeł sprzętowych, nie automatyczny wybór pełnego ROM-u LineageOS.
- Wykrycie źródeł, APK, logów, wyników, firmware i Novi CDN bez skanowania gigabajtów zawartości.
- Log z listy lub wklejony fragment, skrócony do okolic błędu, z maskowaniem typowych sekretów. Maskowanie jest pomocnicze; przejrzyj tekst, zanim go analizujesz.
- Prawdziwe AI przez lokalny endpoint Ollama `/api/chat`, strukturalny JSON i jawne oznaczenie odpowiedzi modelu. Model nie może zmienić zweryfikowanych faktów ani wykonywać komend. Wskazówki regułowe są osobno oznaczone i nie udają AI.

AI nie potwierdza działania telefonu. Repozytorium, dostępna gałąź, komplet blobów, zgodny firmware i działający build to różne rzeczy. Brakującej bazy nie naprawia opinia modelu.

## Układ folderów

| Host ZimaOS | Funkcja | Dostęp aplikacji |
|---|---|---|
| `/DATA/FlowOS/source` | źródła na systemowym SSD | tylko odczyt |
| `/DATA/FlowOS/logs` | logi | tylko odczyt |
| `/DATA/FlowOS/apps` | APK | tylko odczyt |
| `/media/Storage Shared/FlowOS/out` | wyniki na dodatkowym SSD | tylko odczyt |
| `/media/Storage Shared/FlowOS/firmware` | firmware | tylko odczyt |
| `/media/Storage Shared/Novi CDN` | publiczne pliki | tylko odczyt |
| `/DATA/AppData/novi-flowos-assistant` | klucz dostępu panelu | zapis |
| `/DATA/AppData/novi-flowos-assistant/added-apps` | nowe APK do przyszłego projektu | zapis |
| `/DATA/AppData/novi-flowos-ai` | opcjonalne modele | zapis serwera Ollama |

Jeżeli dyski lub foldery na Twoim ZimaOS mają inne nazwy, zmień bind mounts w Compose. Nie montuj całego `/DATA` jako zamiennika. Foldery referencyjne powinny istnieć przed instalacją; jeśli ich brakuje, wskaż odpowiednie istniejące foldery zamiast tworzenia pustego projektu na potrzeby asystenta.

## Uruchomienie z repozytorium

```sh
docker compose up -d --build assistant
```

Panel: `http://ADRES_ZIMAOS:48103`. Klucz dostępu:

```sh
docker exec novi-flowos-assistant cat /state/access-key
```

Nie publikuj tego panelu jako anonimowej aplikacji internetowej. Do testów aplikacja nie wymaga żadnego modelu; źródła i foldery działają bez AI.

## Włączenie prawdziwego AI

```sh
docker compose --profile ai up -d --build
docker compose logs -f model-init
```

Profil uruchamia lokalne Ollama i pobiera model `qwen3:0.6b`. Nie został automatycznie zainstalowany na Twoim obecnym serwerze. Model ma około 523 MB do pobrania (to rozmiar pliku, nie zużycie RAM). Konfiguracja ogranicza serwer AI do 2 GiB RAM i dwóch CPU; to startowy limit, nie gwarancja, że każde zapytanie się zmieści. Malutki model bywa niedokładny. Możesz podmienić `OLLAMA_MODEL` i polecenie pobierania na lepszy model, gdy masz zasoby. Każda odpowiedź zwalnia model z pamięci przez `keep_alive: 0`. AI analizuje po jednym zapytaniu.

Możesz też ustawić `OLLAMA_URL` na istniejący lokalny serwer w LAN. Ta wersja odrzuca publiczne endpointy modelu. Nie ma ukrytej chmury ani opłat API.

## GitHub i instalacja w ZimaOS

**Chcesz aplikację widoczną po dodaniu sklepu do ZimaOS? Przeczytaj [APPSTORE.md](APPSTORE.md).** Repozytorium ma teraz pełną konfigurację własnego sklepu oraz workflow publikacji GitHub Pages. Poniższa instrukcja dotyczy dodatkowej możliwości ręcznego importu Compose.

1. Utwórz publiczne repozytorium i wrzuć **zawartość tego katalogu** (nie całe lokalne źródła projektu).
2. Przed wrzuceniem wygeneruj plik importu dla swojego repozytorium:

```sh
python scripts/prepare-github.py TWOJ_LOGIN/TWOJE_REPO
```

3. Commituj wygenerowane `Apps/NoviFlowOSAssistant/docker-compose.yml` i push na `main`.
4. GitHub Actions przetestuje aplikację i zbuduje obrazy `ghcr.io/twoj_login/twoje_repo:latest` dla amd64/arm64. Ustaw pakiet GHCR jako **publiczny**, jeśli jego domyślna widoczność jest prywatna.
5. W ZimaOS użyj instalacji własnej aplikacji / importu Docker Compose. Podaj adres raw wygenerowanego pliku lub wklej go. Instalacja z pliku potrzebuje opublikowanego obrazu — sam upload kodu nie wystarcza.

Metadane `x-casaos` są przygotowane według dokumentacji ZimaOS. Wygenerowany plik aplikacji obejmuje AI bez profili, żeby instalacja sklepowa mogła uruchomić je od razu. Plik importu to pojedyncza aplikacja; pełny sklep generuje workflow opisany w APPSTORE.md. Ręczny deweloperski Compose w katalogu głównym nadal uruchamia model tylko z profilem `ai`.

## Testy

```sh
python -m unittest discover -s tests -v
```

Testy sprawdzają zależności, odmowę niepoprawnych ścieżek, maskowanie sekretów, format wywołania modelu, brak modelu i rozpoznawanie folderów. Odpowiedzi Ollama w testach są mockowane; rzeczywistą jakość diagnoz należy sprawdzić z uruchomionym modelem. Aplikacja nie została zainstalowana na istniejącym ZimaOS ani podłączona do telefonu.

Źródła dokumentacji: [ZimaOS Compose](https://www.zimaspace.com/docs/developer/app-store-compose-x-casaos), [Ollama chat](https://docs.ollama.com/api/chat), [Qwen3 0.6b](https://ollama.com/library/qwen3:0.6b).
