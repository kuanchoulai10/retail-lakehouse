from __future__ import annotations

from peak_heap_bytes import PEAK_DRIVER_HEAP_BYTES, PEAK_EXECUTOR_HEAP_BYTES, peak_heap_bytes

MIB = 1024 * 1024
UI = "http://tm-run-1-driver-svc.lakehouse-maintenance-operations.svc:4040"


class _Conf:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class _Context:
    def __init__(self, ui, conf):
        self.uiWebUrl = ui
        self.applicationId = "spark-0001"
        self._conf = _Conf(conf)

    def getConf(self):
        return self._conf


class _Spark:
    def __init__(self, ui=UI, conf=None):
        self.sparkContext = _Context(ui, conf or {})


def _executor(id_, heap=None):
    entry = {"id": id_}
    if heap is not None:
        entry["peakMemoryMetrics"] = {"JVMHeapMemory": heap}
    return entry


def test_peaks_are_the_driver_and_the_largest_executor_in_bytes():
    def fetch(_url):
        return [_executor("driver", 384 * MIB), _executor("1", 700 * MIB), _executor("2", 900 * MIB)]

    assert peak_heap_bytes(_Spark(), fetch=fetch) == {
        PEAK_DRIVER_HEAP_BYTES: 384 * MIB,
        PEAK_EXECUTOR_HEAP_BYTES: 900 * MIB,
    }
    assert PEAK_DRIVER_HEAP_BYTES == "peak_coordinator_memory_bytes"
    assert PEAK_EXECUTOR_HEAP_BYTES == "peak_worker_memory_bytes"


def test_the_ui_is_read_on_localhost_at_its_port():
    fetched = []

    def fetch(url):
        fetched.append(url)
        return []

    peak_heap_bytes(_Spark(ui="http://driver-svc.ns.svc:4041"), fetch=fetch)
    assert fetched == ["http://localhost:4041/api/v1/applications/spark-0001/allexecutors"]


def test_the_ui_port_defaults_to_the_spark_ui_port():
    fetched = []

    def fetch(url):
        fetched.append(url)
        return []

    peak_heap_bytes(_Spark(ui="http://driver-svc.ns.svc", conf={"spark.ui.port": "4050"}), fetch=fetch)
    assert fetched == ["http://localhost:4050/api/v1/applications/spark-0001/allexecutors"]


def test_a_role_without_a_peak_is_left_out():
    assert peak_heap_bytes(_Spark(), fetch=lambda _url: [_executor("driver", 10), _executor("1")]) == {
        PEAK_DRIVER_HEAP_BYTES: 10,
    }


def test_nothing_is_measured_without_metrics():
    assert peak_heap_bytes(_Spark(), fetch=lambda _url: [_executor("driver"), _executor("1")]) == {}


def test_nothing_is_measured_when_the_ui_is_off():
    def fetch(_url):
        raise AssertionError("no UI to read")

    assert peak_heap_bytes(_Spark(ui=None), fetch=fetch) == {}


def test_nothing_is_measured_when_the_ui_cannot_be_read():
    def fetch(_url):
        raise OSError("connection refused")

    assert peak_heap_bytes(_Spark(), fetch=fetch) == {}


def test_nothing_is_measured_for_an_unexpected_reply():
    assert peak_heap_bytes(_Spark(), fetch=lambda _url: {"error": "nope"}) == {}
