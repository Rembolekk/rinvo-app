# Rinvo-app

> **To jest symulacja.** Repo udaje produkt Rinvo: konfigurację agenta głosowego, który dzwoni do klientów firmy
> (walidacja leadów u dealera, potwierdzanie wizyt w klinice). Wszystkie dane są fikcyjne (firmy, osoby, adresy, godziny).
> Repo jest publiczne, więc w produkcji byłoby prywatne.

Powstało, żeby agent wykonawczy z repo Rinvo (`agent.py`) miał gdzie wykonywać zgłoszenia z Lineara: poprawki konfiguracji
i bazy wiedzy, testy i recenzja CodeRabbit, a człowiek tylko w wyjątkach.

## Struktura

| Ścieżka | Co to jest |
|---|---|
| `config/<klient>.yaml` | konfiguracja agenta: salony (adres, godziny podawane klientom), godziny dzwonienia, limit prób, marki i kampanie, teksty wstępu |
| `wiedza/<klient>.md` | baza wiedzy agenta głosowego (musi być spójna z `config/`) |
| `zakazy/<klient>.json` | lista zakazanych zmian klienta, sprawdzana testem (np. Opel nie może być aktywny) |
| `tests/` | walidacja schematu i spójności oraz test „zakazy” |
| `.github/workflows/testy.yml` | testy na każdym pull requeście |
| `.coderabbit.yaml` | recenzje CodeRabbit po polsku, profil zwięzły |

## Testy

```bash
pip install pyyaml
python -m unittest discover -s tests -v
```

Sprawdzają: format godzin (`HH:MM`, „od” przed „do”), godziny dzwonienia w granicach z umowy (`limity.godziny_dzwonienia_do`),
limit prób, marki i kampanie (marka nieaktywna nie ma kampanii), zgodność adresów i godzin salonów z bazą wiedzy, to,
że wstęp mówi „wirtualna asystentka” i „rozmowa jest nagrywana”, oraz zakazy z `zakazy/<klient>.json`.

## Zasady dla agenta wykonawczego

- Agent może zmieniać **tylko** `config/` i `wiedza/`. Nigdy `.github/`, `tests/` ani `zakazy/`.
- Zmiana scala się automatycznie (squash) tylko wtedy, gdy testy są zielone, CodeRabbit nie zgłosił problemów, zmiana
  dotyka wyłącznie `config/` lub `wiedza/`, a zgłoszenie dotyczy konfiguracji lub bazy wiedzy. W pozostałych przypadkach
  decyduje człowiek.
- Stan w `config/` odzwierciedla rzeczywistość z rozmów przed wykonaniem otwartych zgłoszeń (np. Toruń w sobotę
  ma jeszcze 14:00, godziny dzwonienia 9–20).
