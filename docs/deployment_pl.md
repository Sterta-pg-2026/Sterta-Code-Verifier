# Instrukcja wdrożenia systemu STOS

## 1. Przygotowanie obecnego systemu GUI

### Tworzenie nowych kolejek zgłoszeń
Opracowywany system zakłada użycie osobnych kolejek w celu zachowania kompatybilnosci wstecznej. W celu dodania nowych kolejek, w pliku `config.inc` należy dodać nowe wpisy osobno dla każdego języka do zmiennej `$availableQueues` (linia 31):

```php
array("stos2025", false, $cppNamePatterns),
array("stos2025-python", true, $pyNamePatterns)
```
- Pierwszy argument: nazwa kolejki.
- Drugi argument: czy wymagany jest wybór pliku głównego przy uruchomieniu.
- Trzeci argument: tablica wzorców plików do wysłania na serwer.

Przykład wzorców plików dla C/C++:
```php
array("*.c", "*.cpp", "*.cxx", "*.h", "*.hpp", "*.hxx");
```
### Dodanie tłumaczenia nazw kolejek
Domyślnie nowe kolejki są wyświetlane przez GUI jako "qname_" + nazwa kolejki.
Aby ustawić czytelne nazwy kolejek, należy w pliku `dict.inc` dodać do słownika `$dictData` (linia 20) odpowiednie tłumaczenia:
```php
"qname_stos2025" => array("pl" => "Stos 2025", "en" => "Stos 2025")
```


### Rozszerzenie listy dozwolonych adresów
Kolejnym krokiem, niezbędnym do poprawnego działania systemu, jest dodanie adresu do listy dozwolonych (whitelisty).
W tym celu, w pliku `configlocal.inc` należy dopisać do zmiennej `$globalACL` (linia 23) wpis z adresem hosta.


### Naprawa błędu związanego z wyborem głównego pliku (funkcjonalność wymagana np. dla pythona)
Ocenianie zadań w językach takich jak Python wymaga wskazania głównego pliku. Obecna wersja GUI zawiera taką funkcjonalność, jednak jej implementacja zawiera błąd.

W celu ich naprawy, w pliku `problem/put_pre.inc` w linii 319 należy usuńąć wywołanie funkcji `intval()`, ponieważ oczekiwany typ zmiennej `$mainfile` to string:

**Przed:**
```php
if(isset($pliki[""]) && isset($pliki[""]["mainfile"])) $mainfile = intval($pliki[""]["mainfile"]);
```
**Po:**
```php
if(isset($pliki[""]) && isset($pliki[""]["mainfile"])) $mainfile = $pliki[""]["mainfile"];
```

Dodatkowo, należy ustawić wartość `$pliki[""]["mainfile"]` np. w linii 525:

```php
$pliki[""]["mainfile"] = $mainfile;
```

