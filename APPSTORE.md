# Novi Apps w sklepie ZimaOS

Ten katalog jest teraz również źródłem **własnego sklepu aplikacji**. Po publikacji dodajesz jego adres w App Store ZimaOS, a Novi FlowOS Assistant pojawia się na liście i można kliknąć Instaluj.

## Pierwsza publikacja

1. Utwórz **publiczne repozytorium** GitHub i wrzuć zawartość tego katalogu do głównego katalogu repozytorium. Koniecznie dołącz `.github/workflows/image.yml`, `Apps`, `store-config.json` i `supported-languages.json`.
2. Workflow wystartuje po pushu na `main`; możesz też uruchomić go z zakładki Actions. Nie musisz włączać GitHub Pages ani dodawać tokenu administracyjnego.
3. Workflow **Publish Novi application and ZimaOS store** wygeneruje poprawne nazwy obrazów i linki, zbuduje obraz aplikacji, a następnie opublikuje sklep na gałęzi `gh-pages`. Pliki są udostępniane przez jsDelivr. Nie musisz ręcznie zmieniać przykładowych linków w źródłach.
4. Jeżeli workflow zatrzyma się na **Require publicly installable image**, ustaw pakiet kontenera jako publiczny: profil GitHub → Packages → pakiet aplikacji → Package settings → Change visibility → Public. Następnie uruchom workflow ponownie. To zwykle jednorazowa czynność przy pierwszym pakiecie GHCR.
5. Po zielonym wyniku workflow skopiuj adres sklepu z jego podsumowania i dodaj go w ZimaOS.

## Adres do dodania w ZimaOS

Dla repozytorium `LOGIN/REPO`:

```text
https://cdn.jsdelivr.net/gh/LOGIN/REPO@gh-pages/
```

W ZimaOS otwórz **App Store → ustawienia / dodaj sklep** i dodaj ten adres. Następnie znajdź **Novi FlowOS Assistant → Instaluj**. Słowa w interfejsie mogą różnić się między wersjami ZimaOS.

Jeżeli Twoja wersja przyjmuje starsze repozytoria ZIP, użyj:

```text
https://cdn.jsdelivr.net/gh/LOGIN/REPO@gh-pages/store/main.zip
```

Adres głównej strony repozytorium `github.com/LOGIN/REPO` nie jest adresem wygenerowanego sklepu. Właściwy katalog powstaje po wykonaniu workflow. GitHub Pages jest opcjonalną alternatywą; domyślne linki sklepu wskazują jsDelivr. CDN może przez pewien czas pamiętać starsze wersje plików.

## Co instaluje wersja sklepowa

- panel Novi FlowOS Assistant (port 48103),
- lokalny serwer Ollama (limit 2 GiB RAM, dwa CPU),
- jednorazowe pobranie modelu Qwen3 0.6B.

Przy pierwszym uruchomieniu AI będzie dostępne dopiero po pobraniu modelu. Panel nie zmienia starego buildu i nie wgrywa niczego na telefon. Dodane APK zapisuje we własnym katalogu przygotowawczym. Istniejące foldery projektu są montowane tylko do odczytu. Możesz ustawić `PANEL_ACCESS_KEY` na własne hasło podczas konfiguracji instalacji; pusty parametr oznacza losowy klucz w `/DATA/AppData/novi-flowos-assistant/access-key`.

## Pliki sklepu i weryfikacja

- `store-config.json`: tożsamość i opis sklepu.
- `supported-languages.json`: polski i angielski.
- `Apps/NoviFlowOSAssistant`: Compose aplikacji i ikona.
- Workflow używa oficjalnego `IceWhaleTech/build-appstore-action@v1.1.2` do generowania `store.json`, `index.json`, metadanych i plików aplikacji.
- Workflow wymaga publicznego obrazu, sprawdza wygenerowane pliki, tworzy również legacy ZIP i publikuje wynik na gałęzi `gh-pages` dostępnej przez jsDelivr.

Szablon został lokalnie przetworzony oficjalnym generatorem z publicznym zastępczym obrazem Pythona zamiast nieopublikowanego obrazu Novi. To sprawdzenie struktury sklepu; publikacja rzeczywistego obrazu i instalacja w UI ZimaOS wymagają testu po wrzuceniu repozytorium. Ten sklep nie jest zgłoszeniem do oficjalnego centralnego katalogu ZimaOS — jest Twoim dodatkowym sklepem.

Dokumentacja: [tworzenie sklepu ZimaOS](https://www.zimaspace.com/docs/developer/app-store-create-from-scratch), [oficjalny generator](https://github.com/IceWhaleTech/build-appstore-action).
