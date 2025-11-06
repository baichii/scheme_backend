import zoneinfo
from datetime import datetime, timezone as datetime_timezone

from backend.core.conf import settings


class Timezone:

    def __init__(self, tz: str = settings.DATATIME_TIMEZONE) -> None:
        """
        初始化时区

        Args:
            tz: 时区名称，例如 "Asia/Shanghai"
        """
        self.tz_info = zoneinfo.ZoneInfo(tz)

    def now(self) -> datetime:
        """获取当前时区时间"""
        return datetime.now(self.tz_info)

    def f_datetime(self, dt: datetime) -> datetime:
        """
        将datetime时间转换为指定时区时间格式
        Args:
            dt: datetime对象

        Returns:

        """
        return dt.astimezone(self.tz_info)

    def f_str(self, date_str: str, format_str: str = settings.DATATIME_FORMAT) -> datetime:
        """
        将字符串时间转换为指定时区时间格式
        Args:
            date_str: 时间字符串
            format_str: 时间字符串格式

        Returns:

        """
        dt = datetime.strptime(date_str, format_str)
        dt = dt.replace(tzinfo=self.tz_info)
        return dt

    @staticmethod
    def t_str(dt: datetime, format_str: str = settings.DATATIME_FORMAT) -> str:
        """
        将datetime时间转换为字符串时间格式
        Args:
            dt: datetime对象
            format_str: 时间字符串格式

        Returns:

        """
        return dt.strftime(format_str)

    @staticmethod
    def f_utc(dt: datetime) -> datetime:
        """
        将datetime时间转换为UTC时间格式
        Args:
            dt: datetime对象

        Returns:

        """
        return dt.astimezone(datetime_timezone.utc)


timezone: Timezone = Timezone()
