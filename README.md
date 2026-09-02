# Radar de Voos

Painel estatico de voos programados em aeroportos brasileiros, alimentado pela API publica SIROS/ANAC, armazenado no Supabase e publicado pelo GitHub Pages.

## Arquitetura

1. `scripts/fetch_flights.py` consulta os voos do dia no SIROS/ANAC.
2. Os movimentos sao enviados para a tabela `voos` do Supabase.
3. Cada aeroporto tambem e salvo como `data/{ICAO}.json`.
4. `index.html` consulta o Supabase e usa o JSON como fallback.
5. `.github/workflows/update_flights.yml` executa a coleta automaticamente.

## Configuracao no GitHub

Em **Settings > Secrets and variables > Actions**, crie:

- Secret `SUPABASE_URL`: URL do projeto Supabase.
- Secret `SUPABASE_SERVICE_KEY`: chave de servico do Supabase, usada somente no workflow.
- Variable `AIRPORTS`: ICAOs separados por virgula, por exemplo `SBGR,SBSP,SBBR,SBGL`.

Depois ative o GitHub Pages usando a branch `main` e a pasta raiz. O workflow tambem pode ser iniciado manualmente em **Actions > Atualizar voos > Run workflow**.

## Uso local

```bash
python -m pip install requests
python scripts/fetch_flights.py
python -m http.server 8080
```

Abra `http://localhost:8080`. Sem uma chave, o dashboard continua abrindo, mas exibira um estado vazio para os aeroportos sem JSON coletado.

## Banco de dados

`sql/setup.sql` contem um schema PostgreSQL opcional para aeroportos e movimentos, caso o projeto evolua de arquivos estaticos para persistencia.
