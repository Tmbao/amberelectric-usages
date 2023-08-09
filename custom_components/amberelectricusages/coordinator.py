"""Amber Electric - Usages Coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from amberelectric import ApiException
from amberelectric.api import amber_api
from amberelectric.model.usage import Usage
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.components.recorder.util import get_instance
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER


class AmberUsagesCoordinator(DataUpdateCoordinator):
    """Handle and update past grid usage data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: amber_api.AmberApi,
        site_id: str,
        entry_title: str,
    ) -> None:
        """Initialise the data service."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )
        self._hass = hass
        self._api = api
        self._site_id = site_id
        self._statistic_id_prefix = (
            f"{DOMAIN}:{entry_title.lower().replace('-', '')}_usages"
        )

    def _get_usages(self) -> list[Usage]:
        today = dt_util.now().date()
        day_2_weeks_ago = today - timedelta(weeks=2)
        return self._api.get_usage(
            self._site_id, start_date=day_2_weeks_ago, end_date=today
        )

    async def _async_update_data(self) -> None:
        usages: list[Usage] = []
        try:
            usages = await self._hass.async_add_executor_job(self._get_usages)
        except ApiException as api_exception:
            raise UpdateFailed("Missing usage data, skipping update") from api_exception

        LOGGER.debug("Fetched new Amber data: %s", usages)
        await self._insert_usage_statistic(usages)

    async def _insert_usage_statistic(self, raw_usages: list[Usage]) -> None:
        usages_by_hour_by_channel: dict[str, dict[datetime, list[Usage]]] = {}
        for usage in raw_usages:
            usages_by_hour_by_channel.setdefault(usage.channelIdentifier, {})

            start_time_hour = usage.start_time - timedelta(
                minutes=usage.start_time.minute, seconds=usage.start_time.second
            )
            usages_by_hour_by_channel[usage.channelIdentifier].setdefault(
                start_time_hour, []
            )
            usages_by_hour_by_channel[usage.channelIdentifier][start_time_hour].append(
                usage
            )

        for channel, usages_by_hour in usages_by_hour_by_channel.items():
            statistic_id = f"{self._statistic_id_prefix}_{channel.lower()}"
            LOGGER.debug(f"Updating {statistic_id}")
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"{self._statistic_id_prefix} - {channel}",
                source=DOMAIN,
                statistic_id=statistic_id,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            )

            last_stat_sum: float = 0
            last_stat_start: datetime = None
            last_stats = await get_instance(self._hass).async_add_executor_job(
                get_last_statistics, self._hass, 1, statistic_id, True, {"sum"}
            )
            if last_stats is not None and statistic_id in last_stats:
                last_stat = last_stats[statistic_id][0]
                LOGGER.info(last_stat)
                last_stat_sum = last_stat["sum"]
                last_stat_start = datetime.fromtimestamp(
                    last_stat["start"], timezone.utc
                )

            statistics: list[StatisticData] = []
            for start_hour, usages in usages_by_hour.items():
                # Skip if we've read this data
                if last_stat_start is not None and start_hour <= last_stat_start:
                    continue

                total_kwh: float = 0
                for usage in usages:
                    total_kwh += usage.kwh

                last_stat_sum += total_kwh

                statistics.append(
                    StatisticData(state=total_kwh, sum=last_stat_sum, start=start_hour)
                )
            async_add_external_statistics(self._hass, metadata, statistics)