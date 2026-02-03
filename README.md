 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
new file mode 100644
index 0000000000000000000000000000000000000000..bac28d01d018ce8a980f676a55ee026ccf7f768a
--- /dev/null
+++ b/README.md
@@ -0,0 +1,39 @@
+# Lead Lookalike API
+
+Minimalna aplikacja API do wyszukiwania leadów z wykorzystaniem metody look‑a‑like.
+Serwis przechowuje leady w pamięci procesu i zwraca podobne rekordy na podstawie
+prostej funkcji podobieństwa (branża, lokalizacja, rozmiar firmy, tagi).
+
+## Funkcje
+- Dodawanie leadów
+- Lista leadów
+- Wyszukiwanie look‑a‑like względem podanego leada
+
+## Szybki start
+
+```bash
+python -m venv .venv
+source .venv/bin/activate
+pip install -r requirements.txt
+uvicorn app.main:app --reload
+```
+
+## Przykładowe użycie
+
+```bash
+curl -X POST http://localhost:8000/leads \
+  -H 'Content-Type: application/json' \
+  -d '{"name":"Acme","industry":"ecommerce","location":"PL","company_size":120,"tags":["b2b","saas"]}'
+
+curl -X POST http://localhost:8000/leads \
+  -H 'Content-Type: application/json' \
+  -d '{"name":"Beta","industry":"ecommerce","location":"PL","company_size":90,"tags":["saas","retail"]}'
+
+curl -X POST http://localhost:8000/lookalike \
+  -H 'Content-Type: application/json' \
+  -d '{"seed":{"industry":"ecommerce","location":"PL","company_size":100,"tags":["saas"]},"limit":5}'
+```
+
+## Uwagi
+Aplikacja jest przykładowa i gotowa do podmiany warstwy przechowywania (np. baza
+PostgreSQL + wektorowe podobieństwo) oraz rozbudowy funkcji scoringu.
 
EOF
)
