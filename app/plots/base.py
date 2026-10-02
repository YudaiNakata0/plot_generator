"""グラフ種類 (PlotType) の基底クラスとレジストリ。

新しいグラフを追加するときは PlotType を継承したクラスを作り、@register を付ける。
GUI は params の定義から入力欄を自動生成し、draw() を呼ぶだけにする。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class Param:
    """グラフのパラメータ定義。

    default が None のものは「未指定」を許す（0 とは区別する）。
    per_channel=True のものは値が {チャンネル名: 値} の dict になる。
    """

    key: str
    type: type
    default: Any = None
    label: str = ""
    unit: str = ""
    choices: tuple = ()
    per_channel: bool = False
    help: str = ""

    def convert(self, value):
        if value is None or value == "":
            return None
        if self.per_channel:
            return {
                channel: self.type(v)
                for channel, v in dict(value).items()
                if v is not None and v != ""
            }
        if self.type is bool and isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        value = self.type(value)
        if self.choices and value not in self.choices:
            raise ValueError(f"{self.key}: '{value}' is not in {self.choices}")
        return value


class PlotType:
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    params: ClassVar[list[Param]] = []

    @classmethod
    def default_params(cls) -> dict:
        return {p.key: (dict() if p.per_channel else p.default) for p in cls.params}

    @classmethod
    def resolve_params(cls, params=None) -> dict:
        """デフォルト値で補い、型変換した params を返す。未知のキーはエラー。"""
        params = dict(params or {})
        known = {p.key: p for p in cls.params}
        unknown = set(params) - set(known)
        if unknown:
            raise KeyError(f"{cls.name}: unknown params {sorted(unknown)}")
        resolved = cls.default_params()
        for key, value in params.items():
            converted = known[key].convert(value)
            if converted is not None:
                resolved[key] = converted
            elif not known[key].per_channel:
                resolved[key] = None
        return resolved

    def figsize(self, datasets, channels, params) -> tuple[float, float]:
        return (8, 6)

    def draw(self, fig, datasets, channels, params) -> None:
        """fig (matplotlib.figure.Figure) に描画する。

        datasets: 描画する Dataset のリスト
        channels: 描画するチャンネル名のリスト
        params  : resolve_params() 済みの dict
        ファイルの読み込みや plt.show() はしない。
        """
        raise NotImplementedError


REGISTRY: dict[str, type[PlotType]] = {}


def register(cls):
    if not cls.name:
        raise ValueError(f"{cls.__name__} has no name")
    if cls.name in REGISTRY:
        raise ValueError(f"plot type '{cls.name}' is already registered")
    REGISTRY[cls.name] = cls
    return cls


def check_channels(datasets, channels):
    for ds in datasets:
        missing = [ch for ch in channels if ch not in ds]
        if missing:
            raise KeyError(f"{ds.name}: no channel {missing} (available: {ds.channel_names})")
