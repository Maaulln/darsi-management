"""Service klien SurrealDB untuk integrasi clean data layer."""

from __future__ import annotations

import json
from typing import Any

import requests

from app.core.config import settings


class SurrealDBClient:
    """Klien HTTP untuk query SurrealDB endpoint /sql.

    Mengakses data clean dari namespace darsi, database operasional.
    Semua method exception-safe dengan fallback ke empty data.
    """

    def __init__(
        self,
        url: str = settings.surrealdb_url,
        user: str = settings.surrealdb_user,
        password: str = settings.surrealdb_password,
        namespace: str = settings.surrealdb_ns,
        database: str = settings.surrealdb_db,
    ) -> None:
        """Inisialisasi klien SurrealDB.

        Args:
            url: Base URL SurrealDB, contoh http://surrealdb:8000.
            user: Username untuk autentikasi basic.
            password: Password untuk autentikasi basic.
            namespace: Namespace SurrealDB untuk query.
            database: Database SurrealDB untuk query.
        """

        self.url = url.rstrip("/").replace("/rpc", "") + "/sql"
        self.auth = (user, password)
        self.headers = {
            "Accept": "application/json",
            "surreal-ns": namespace,
            "surreal-db": database,
        }

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Menjalankan query SQL ke SurrealDB dan kembalikan hasil.

        Args:
            sql: Query SQL SurrealDB yang akan dijalankan.

        Returns:
            List dictionary hasil query. Kosong jika gagal atau tidak ada hasil.
        """

        try:
            response = requests.post(
                self.url,
                data=sql,
                headers=self.headers,
                auth=self.auth,
                timeout=10,
            )
            response.raise_for_status()

            payload = response.json()
            if isinstance(payload, list) and len(payload) > 0:
                first_item = payload[0]
                if isinstance(first_item, dict) and first_item.get("status") == "OK":
                    result = first_item.get("result", [])
                    return result if isinstance(result, list) else []

        except (requests.RequestException, ValueError, KeyError) as error:
            pass

        return []

    def get_resource_summary(self) -> dict[str, Any]:
        """Mengambil ringkasan utilitas resource dari clean layer.

        Returns:
            Dictionary berisi agregat per unit untuk listrik, air, dan okupansi.
        """

        summary: dict[str, Any] = {
            "timestamp": None,
            "units": {},
        }

        listrik_query = """
            SELECT
                unit_code,
                meter_id,
                building_code,
                kwh_total,
                reading_at
            FROM clean_meter_listrik
        """
        listrik_records = self.query(listrik_query)

        air_query = """
            SELECT
                unit_code,
                meter_id,
                volume_m3_total,
                reading_at
            FROM clean_konsumsi_air
        """
        air_records = self.query(air_query)

        okupansi_query = """
            SELECT
                unit_code,
                room_class,
                bed_capacity,
                bed_occupied,
                room_status
            FROM clean_okupansi_kamar
        """
        okupansi_records = self.query(okupansi_query)

        unit_map: dict[str, dict[str, Any]] = {}

        for record in listrik_records:
            unit = record.get("unit_code", "unknown")
            if unit not in unit_map:
                unit_map[unit] = {
                    "unit_code": unit,
                    "listrik_kwh": 0,
                    "air_m3": 0,
                    "bed_occupied": 0,
                    "bed_capacity": 0,
                }
            unit_map[unit]["listrik_kwh"] += record.get("kwh_total", 0)

        for record in air_records:
            unit = record.get("unit_code", "unknown")
            if unit not in unit_map:
                unit_map[unit] = {
                    "unit_code": unit,
                    "listrik_kwh": 0,
                    "air_m3": 0,
                    "bed_occupied": 0,
                    "bed_capacity": 0,
                }
            unit_map[unit]["air_m3"] += record.get("volume_m3_total", 0)

        for record in okupansi_records:
            unit = record.get("unit_code", "unknown")
            if unit not in unit_map:
                unit_map[unit] = {
                    "unit_code": unit,
                    "listrik_kwh": 0,
                    "air_m3": 0,
                    "bed_occupied": 0,
                    "bed_capacity": 0,
                }
            unit_map[unit]["bed_occupied"] += record.get("bed_occupied", 0)
            unit_map[unit]["bed_capacity"] += record.get("bed_capacity", 0)

        summary["units"] = list(unit_map.values())
        return summary

    def get_cost_summary(self) -> dict[str, Any]:
        """Mengambil ringkasan biaya operasional dari clean layer.

        Returns:
            Dictionary berisi agregat biaya per unit dan kategori.
        """

        summary: dict[str, Any] = {
            "timestamp": None,
            "units": {},
        }

        cost_query = """
            SELECT
                unit_code,
                cost_category,
                amount_idr,
                budget_idr,
                period_month
            FROM clean_biaya_operasional
        """
        cost_records = self.query(cost_query)

        unit_map: dict[str, dict[str, Any]] = {}

        for record in cost_records:
            unit = record.get("unit_code", "unknown")
            if unit not in unit_map:
                unit_map[unit] = {
                    "unit_code": unit,
                    "total_cost_idr": 0,
                    "total_budget_idr": 0,
                    "categories": {},
                }

            cost_category = record.get("cost_category", "other")
            amount = record.get("amount_idr", 0)
            budget = record.get("budget_idr", 0)

            unit_map[unit]["total_cost_idr"] += amount
            unit_map[unit]["total_budget_idr"] += budget

            if cost_category not in unit_map[unit]["categories"]:
                unit_map[unit]["categories"][cost_category] = {
                    "amount_idr": 0,
                    "budget_idr": 0,
                }
            unit_map[unit]["categories"][cost_category]["amount_idr"] += amount
            unit_map[unit]["categories"][cost_category]["budget_idr"] += budget

        summary["units"] = list(unit_map.values())
        return summary
