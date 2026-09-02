"""Collect scheduled flights from the public SIROS/ANAC API."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from supabase import create_client

API_BASE = "https://sas.anac.gov.br/sas/siros_api/voos"
AIRPORTS = [item.strip().upper() for item in os.getenv("AIRPORTS", "SBCA,SBGR,SBSP,SBCT,SBGL,SBBR,SBFL,SBPA").split(",") if item.strip()]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

AIRPORT_NAMES = {
    "SBGR": "Sao Paulo / Guarulhos", "SBSP": "Sao Paulo / Congonhas",
    "SBBR": "Brasilia", "SBGL": "Rio de Janeiro / Galeao",
    "SBRJ": "Rio de Janeiro / Santos Dumont", "SBCT": "Curitiba",
    "SBPA": "Porto Alegre", "SBCF": "Belo Horizonte / Confins",
    "SBSV": "Salvador", "SBFZ": "Fortaleza", "SBEG": "Manaus",
    "SBFL": "Florianopolis",
}


def fetch_flights(icao, direction):
    today = datetime.now(timezone(timedelta(hours=-3)))
    response = requests.get(API_BASE, params={"dataReferencia": today.strftime("%d%m%Y")}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, list):
        raise RuntimeError("Resposta inesperada da API SIROS")
    print(f"Total retornado pela API SIROS ({direction}): {len(payload)}")

    flights = []
    for item in payload:
        departure_icao = (item.get("sg_icao_origem") or "").strip().upper()
        arrival_icao = (item.get("sg_icao_destino") or "").strip().upper()
        if (direction == "arrival" and arrival_icao != icao) or (direction == "departure" and departure_icao != icao):
            continue
        endpoint_time = item.get("dt_chegada_prevista_utc" if direction == "arrival" else "dt_partida_prevista_utc") or ""
        route_icao = departure_icao if direction == "arrival" else arrival_icao
        company = (item.get("sg_empresa_icao") or "").strip().upper()
        flight_number = str(item.get("nr_voo") or "").strip().lstrip("0") or "0"
        flights.append({
            "callsign": f"{company}{flight_number}" if company else flight_number,
            "airline": company or "Companhia desconhecida",
            "airport": route_icao or "?",
            "airport_name": AIRPORT_NAMES.get(route_icao, route_icao or "Rota desconhecida"),
            "scheduled": endpoint_time,
            "time_iso": parse_siros_datetime(endpoint_time),
            "status": "scheduled",
        })
    return flights


def deduplicate(flights):
    seen = set()
    unique = []
    for flight in flights:
        key = (flight["callsign"], flight["airport"], flight["scheduled"], flight["status"])
        if key not in seen:
            seen.add(key)
            unique.append(flight)
    return unique


def parse_siros_datetime(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y %H:%M").replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ""


def write_airport(icao):
    result = {"updated_at": datetime.now(timezone.utc).isoformat(), "airport_icao": icao,
              "airport_name": AIRPORT_NAMES.get(icao, icao), "source": "SIROS/ANAC",
              "arrivals": [], "departures": []}
    for direction in ("arrival", "departure"):
        try:
            result["arrivals" if direction == "arrival" else "departures"] = fetch_flights(icao, direction)
        except requests.RequestException as error:
            print(f"Aviso: falha de rede em {icao} ({direction}): {error}")
        except RuntimeError as error:
            print(f"Aviso: API rejeitou {icao} ({direction}): {error}")
    output = DATA_DIR / f"{icao}.json"
    before = len(result["arrivals"]) + len(result["departures"])
    result["arrivals"] = deduplicate(result["arrivals"])
    result["departures"] = deduplicate(result["departures"])
    removed = before - len(result["arrivals"]) - len(result["departures"])
    print(f"Filtrados para o ICAO configurado: {before}")
    print(f"Duplicados removidos: {removed}")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if SUPABASE_URL and SUPABASE_KEY:
        push_to_supabase(icao, result)
    print(f"{icao}: {len(result['arrivals'])} chegadas, {len(result['departures'])} partidas")


def push_to_supabase(icao, result):
    """Upsert SIROS movements and register the pipeline execution."""
    database = create_client(SUPABASE_URL, SUPABASE_KEY)
    rows = []
    reference_date = datetime.now(timezone(timedelta(hours=-3))).date().isoformat()
    for direction in ("arrival", "departure"):
        for flight in result["arrivals" if direction == "arrival" else "departures"]:
            origin = flight["airport"] if direction == "arrival" else icao
            destination = icao if direction == "arrival" else flight["airport"]
            rows.append({
                "data_referencia": reference_date,
                "icao_empresa": flight["callsign"][:3] or "UNK",
                "nome_empresa": flight["airline"],
                "numero_voo": flight["callsign"][3:] or flight["callsign"],
                "etapa": "1",
                "icao_origem": origin,
                "icao_destino": destination,
                "partida_iso": flight.get("time_iso") if direction == "departure" else None,
                "chegada_iso": flight.get("time_iso") if direction == "arrival" else None,
                "tipo_operacao": "Domestico",
                "tipo_servico": flight["status"],
            })
    if rows:
        database.table("voos").upsert(rows, on_conflict="data_referencia,icao_empresa,numero_voo,icao_origem,icao_destino,etapa").execute()
    database.table("execucoes").insert({
        "concluido_em": datetime.now(timezone.utc).isoformat(),
        "aeroportos_buscados": [icao],
        "voos_processados": len(rows),
        "lotes_enviados": 1 if rows else 0,
        "erros": 0,
        "status": "concluido",
    }).execute()
    print(f"Enviados ao Supabase: {len(rows)}")


if __name__ == "__main__":
    if SUPABASE_URL and not SUPABASE_KEY:
        raise SystemExit("Defina SUPABASE_SERVICE_KEY quando SUPABASE_URL estiver configurada.")
    DATA_DIR.mkdir(exist_ok=True)
    total = 0
    errors = 0
    for airport in AIRPORTS:
        try:
            write_airport(airport)
            total += 1
        except Exception as error:
            errors += 1
            print(f"Erro em {airport}: {error}")
    status = "concluido" if errors == 0 else "erro_parcial" if total else "erro_critico"
    print(f"Status final: {status}")
    if errors:
        raise SystemExit(1)
