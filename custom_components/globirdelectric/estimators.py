"""Sensor estimator definitions."""
from __future__ import annotations

import datetime
from datetime import timedelta
from typing import Callable


class BaseEstimator(object):
    def estimate(
        self,
        now: datetime.datetime,
        get_actual_fn: Callable[[datetime.datetime], float],
    ) -> float:
        pass


class Last30DaysEstimator(BaseEstimator):
    def estimate(
        self,
        now: datetime.datetime,
        get_actual_fn: Callable[[datetime.datetime], float],
    ) -> float:
        sum = 0.0
        count = 0
        for day_delta in range(1, 31):
            delta = timedelta(days=day_delta)
            actual = get_actual_fn(now - delta)
            if actual is not None:
                sum += actual
                count += 1
        if count == 0:
            return 0
        return sum / count
