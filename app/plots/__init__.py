from .base import REGISTRY, Param, PlotType, register

# 各グラフ種類を import して REGISTRY に登録する
from . import timeseries, trajectory2d  # noqa: F401

__all__ = ["REGISTRY", "Param", "PlotType", "register"]
