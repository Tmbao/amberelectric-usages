"""Globird Electric utilities."""
from __future__ import annotations

import csv
import datetime
import logging
import multiprocessing
from datetime import timedelta
from enum import Enum
from typing import Iterator

import requests

from .estimators import BaseEstimator

_LOGGER = logging.getLogger(__name__)

USER_URL = "https://myaccount.globirdenergy.com.au/api/account/currentuser"
DATA_CSV_URL = "https://myaccount.globirdenergy.com.au/api/site/generatecsvfile?accountServiceId={}"


def _find_electricity_service_id(accounts: list, site_id: str) -> int | None:
    for account in accounts:
        for service in account["services"]:
            if (
                service["serviceType"] == "Power"
                and service["siteIdentifier"] == site_id
            ):
                return service["accountServiceId"]
    return None


class GlobirdError(Exception):
    pass


class GlobirdServiceClient(object):
    def __init__(
        self, service_id: str, site_id: str, session: requests.Session
    ) -> None:
        self.service_id = service_id
        self.site_id = site_id
        self.session = session

    @classmethod
    def authenticate(cls, access_token: str, site_id: str) -> "GlobirdServiceClient":
        session = requests.Session()

        response = session.get(USER_URL, cookies={"globird-portal-user": access_token})
        if response.status_code != 200:
            raise GlobirdError(
                "Failed to get user info: {}\nCookies:{}\nResponse body:{}".format(
                    response.status_code, session.cookies, response.text
                )
            )
        body = response.json()
        if not body["success"]:
            raise GlobirdError("Failed to get user info: {}".format(body))
        service_id = _find_electricity_service_id(body["data"]["accounts"], site_id)
        if service_id is None:
            raise GlobirdError(
                "Unable to find electricity service: {}\n{}".format(site_id, body)
            )

        return GlobirdServiceClient(service_id, site_id, session)


class GlobirdChargeType(Enum):
    SOLAR_FEED_IN = 1
    USAGE = 2

    @classmethod
    def from_symbol(cls, symbol: str) -> "GlobirdChargeType":
        if symbol == "B1":
            return GlobirdChargeType.SOLAR_FEED_IN
        elif symbol == "E1":
            return GlobirdChargeType.USAGE
        else:
            return None


class GlobirdDataPoint(object):
    def __init__(self, date: datetime.date, time: datetime.time, value: float) -> None:
        self.date = date
        self.time = time
        self.value = value


class GlobirdStore(object):
    _SENSOR_INTERVAL_MINS = 5

    def __init__(self, estimator: BaseEstimator) -> None:
        self._usage_data_points = {}
        self._feedin_data_points = {}
        self._latest_date = None
        self._estimator = estimator

    def is_stale(self, now: datetime.datetime) -> bool:
        if self._latest_date is None:
            return True
        diff = now.date() - self._latest_date
        return diff.days > 1

    def get_total_daily_consumption(self, until: datetime.datetime) -> float:
        total_consumption = 0
        time = datetime.datetime(
            year=until.year, month=until.month, day=until.day, tzinfo=until.tzinfo
        )
        step = timedelta(minutes=GlobirdStore._SENSOR_INTERVAL_MINS)
        while time <= until:
            consumption = self._get_consumption_actual(time)
            if consumption is None:
                consumption = self._get_consumption_estimated(time)
            total_consumption += consumption
            time += step

        return consumption

    def _get_consumption_actual(self, now: datetime.datetime) -> float | None:
        now = GlobirdStore._normalize_time(now)
        if now in self._usage_data_points:
            return self._usage_data_points[now].value
        return None

    def _get_consumption_estimated(self, now: datetime.datetime) -> float:
        return self._estimator.estimate(now, self._get_consumption_actual)

    @staticmethod
    def _normalize_time(now: datetime.datetime) -> datetime.datetime:
        discard = timedelta(
            minutes=now.minute % GlobirdStore._SENSOR_INTERVAL_MINS,
            seconds=now.second,
            microseconds=now.microsecond,
        )
        normalized_now = now - discard
        return datetime.datetime(
            year=normalized_now.year,
            month=normalized_now.month,
            day=normalized_now.day,
            hour=normalized_now.hour,
            minute=normalized_now.minute,
        )

    def merge_data(self, reader: Iterator[list[str]]) -> None:
        charge_type: GlobirdChargeType = None
        col_time: list[datetime.time] = []
        for row in reader:
            # Special rows
            if row[0] == "Nmi":
                # Ignore
                continue
            if row[0] == "Stream ID":
                charge_type = GlobirdChargeType.from_symbol(row[2])
                continue
            if row[0] == "LOCAL TIME":
                # TODO: Support non-AEST time
                continue
            if row[0] == "Date/Time":
                col_time = []
                for i in range(1, len(row)):
                    col_time.append(datetime.datetime.strptime(row[i], "%H:%M").time())
                continue
            if row[0] == "Total for Period":
                continue

            # Usage data
            date = datetime.datetime.strptime(row[0], "%Y%m%d").date()
            if self._latest_date is None or self._latest_date < date:
                self._latest_date = date
            for i in range(1, len(row)):
                time = col_time[i - 1]
                dt_key = datetime.datetime(
                    year=date.year,
                    month=date.month,
                    day=date.day,
                    hour=time.hour,
                    minute=time.minute,
                )
                if charge_type == GlobirdChargeType.SOLAR_FEED_IN:
                    self._feedin_data_points[dt_key] = GlobirdDataPoint(
                        date, time, float(row[i])
                    )
                elif charge_type == GlobirdChargeType.USAGE:
                    self._usage_data_points[dt_key] = GlobirdDataPoint(
                        date, time, float(row[i])
                    )


class GlobirdDAO(object):
    def __init__(self, auth: GlobirdServiceClient, estimator: BaseEstimator) -> None:
        self._auth = auth
        self._store = GlobirdStore(estimator)
        self._download_lock = multiprocessing.Lock()
        self._last_read_dt = None
        self._last_read = 0

    def _build_fetch_form(self, now: datetime.datetime) -> dict:
        range = timedelta(days=60)
        to_date = now.strftime("%Y/%m/%d")
        from_date = (now - range).strftime("%Y/%m/%d")
        return {
            "fromDate": to_date,
            "toDate": from_date,
            "identifier": self._auth.site_id,
            "isSmart": True,
            "isCrossAccount": False,
        }

    def fetch(self, now: datetime.datetime) -> float:
        if self._store.is_stale(now):
            self._download_data(now)

        read = self._store.get_total_daily_consumption(now)
        delta = read

        if self._last_read_dt is not None and self._last_read_dt.date() == now.date():
            delta -= self._last_read

        self._last_read_dt = now
        self._last_read = read

        _LOGGER.warn("Data read at %s: %f", now, read)
        return delta

    def _download_data(self, now: datetime.datetime) -> None:
        self._download_lock.acquire()
        try:
            if not self._store.is_stale(now):
                return

            url = DATA_CSV_URL.format(self._auth.service_id)
            response = self._auth.session.post(url, json=self._build_fetch_form(now))
            decoded_text = response.content.decode("utf-8-sig")
            reader = csv.reader(decoded_text.splitlines(), delimiter=",")
            # skip header
            self._store.merge_data(reader)
        except Exception as e:
            _LOGGER.error("Failed to download data: %s", e)
        finally:
            self._download_lock.release()
