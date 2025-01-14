# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=too-many-ancestors

from logging import getLogger
from typing import TYPE_CHECKING, Dict, Generator, Iterable, Optional, Union

from opentelemetry._metrics import CallbackT
from opentelemetry._metrics import Counter as APICounter
from opentelemetry._metrics import Histogram as APIHistogram
from opentelemetry._metrics import ObservableCounter as APIObservableCounter
from opentelemetry._metrics import ObservableGauge as APIObservableGauge
from opentelemetry._metrics import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry._metrics import UpDownCounter as APIUpDownCounter
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

if TYPE_CHECKING:
    from opentelemetry.sdk._metrics._internal.measurement_consumer import (
        MeasurementConsumer,
    )


_logger = getLogger(__name__)


_ERROR_MESSAGE = (
    "Expected ASCII string of maximum length 63 characters but got {}"
)


class _Synchronous:
    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: "MeasurementConsumer",
        unit: str = "",
        description: str = "",
    ):
        # pylint: disable=no-member
        is_name_valid, is_unit_valid = self._check_name_and_unit(name, unit)

        if not is_name_valid:
            raise Exception(_ERROR_MESSAGE.format(name))

        if not is_unit_valid:
            raise Exception(_ERROR_MESSAGE.format(unit))
        self.name = name.lower()
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        super().__init__(name, unit=unit, description=description)


class _Asynchronous:
    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: "MeasurementConsumer",
        callbacks: Optional[Iterable[CallbackT]] = None,
        unit: str = "",
        description: str = "",
    ):
        # pylint: disable=no-member
        is_name_valid, is_unit_valid = self._check_name_and_unit(name, unit)

        if not is_name_valid:
            raise Exception(_ERROR_MESSAGE.format(name))

        if not is_unit_valid:
            raise Exception(_ERROR_MESSAGE.format(unit))
        self.name = name.lower()
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        super().__init__(name, callbacks, unit=unit, description=description)

        self._callbacks = []

        if callbacks is not None:

            for callback in callbacks:

                if isinstance(callback, Generator):

                    def inner(callback=callback) -> Iterable[Measurement]:
                        return next(callback)

                    self._callbacks.append(inner)
                else:
                    self._callbacks.append(callback)

    def callback(self) -> Iterable[Measurement]:
        for callback in self._callbacks:
            try:
                for api_measurement in callback():
                    yield Measurement(
                        api_measurement.value,
                        instrument=self,
                        attributes=api_measurement.attributes,
                    )
            except StopIteration:
                pass
            except Exception:  # pylint: disable=broad-except
                _logger.exception(
                    "Callback failed for instrument %s.", self.name
                )


class Counter(_Synchronous, APICounter):
    def add(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        if amount < 0:
            _logger.warning(
                "Add amount must be non-negative on Counter %s.", self.name
            )
            return
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class UpDownCounter(_Synchronous, APIUpDownCounter):
    def add(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class ObservableCounter(_Asynchronous, APIObservableCounter):
    pass


class ObservableUpDownCounter(_Asynchronous, APIObservableUpDownCounter):
    pass


class Histogram(_Synchronous, APIHistogram):
    def record(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        if amount < 0:
            _logger.warning(
                "Record amount must be non-negative on Histogram %s.",
                self.name,
            )
            return
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class ObservableGauge(_Asynchronous, APIObservableGauge):
    pass
