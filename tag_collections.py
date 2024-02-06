import time as _time
import datetime as _datetime
import typing as _typing


class TagTime:
    def __init__(self, param=None) -> None:
        match param:
            case None:
                self.start = _time.time()
                self.end = _time.time()
            case str():
                pass

    @property
    def struct_time(self) -> _time.struct_time:
        return _time.localtime(self.start)

    @property
    def datetime(self) -> _datetime.datetime:
        return _datetime.datetime.fromtimestamp(self.start)

    @staticmethod
    def formating_timestamp(
        timestamp=_time.time(),
        format_: _typing.Literal["normal", "iso", "timestamp"] = "normal",
    ) -> str:
        struct_time = _time.localtime(timestamp)
        datetime = _datetime.datetime.fromtimestamp(timestamp)
        match format_:
            case "normal":
                time_struct = struct_time
                date_str = (
                    f"{time_struct.tm_year}-{time_struct.tm_mon}-{time_struct.tm_mday}"
                )
                time_str = (
                    f"{time_struct.tm_hour}-{time_struct.tm_min}-{time_struct.tm_sec}"
                )
                return f"{date_str}--{time_str}"
            case "iso":
                return f"i_{datetime.isoformat()}"
            case "timestamp":
                return f"s_{timestamp}"
            case _:
                raise ValueError(format_)
