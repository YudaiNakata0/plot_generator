# scripts/ の論文用の図の見た目を引き継ぐ共通スタイル

# 目標値の線 (axhline)
TARGET_LINE = dict(color="C1", alpha=0.5)
# 目標値の許容範囲の帯 (axhspan)
TARGET_BAND = dict(color="C1", alpha=0.2)

# 時間で色付けする軌跡のカラーマップ
TIME_CMAP = "viridis"

# 箱ひげ図（ひげ = 最小〜最大）
BOXPLOT = dict(
    whis=[0, 100],
    showfliers=True,
    patch_artist=True,
    boxprops=dict(linewidth=1.2, edgecolor="black"),
    medianprops=dict(linewidth=1.0, color="black"),
    whiskerprops=dict(linewidth=1.2, color="black"),
    capprops=dict(linewidth=1.2, color="black"),
)
GRID_Y = dict(axis="y", linestyle="--", alpha=0.5)

SAVE_DPI = 300


# ===== 日本語フォント =====
# matplotlib 3.5 はフォントのフォールバックが無いので、日本語を含む文字列にだけ日本語フォントを使う
# （英語だけの図は従来どおり DejaVu Sans のまま）
_JP_FONT_CANDIDATES = ["IPAexGothic", "Noto Sans CJK JP", "IPAGothic", "TakaoGothic"]
_jp_font = None


def _find_jp_font():
    global _jp_font
    if _jp_font is None:
        from matplotlib import font_manager
        names = {f.name for f in font_manager.fontManager.ttflist}
        _jp_font = next((name for name in _JP_FONT_CANDIDATES if name in names), "")
    return _jp_font


def font_kwargs(*texts):
    """texts に ASCII 以外の文字があれば {"fontfamily": 日本語フォント} を返す（set_title などに渡す）。"""
    if any(text and not str(text).isascii() for text in texts) and _find_jp_font():
        return {"fontfamily": _jp_font}
    return {}


def legend_kwargs(ax):
    """凡例のラベルに日本語があれば legend(prop=...) 用の引数を返す。"""
    _, labels = ax.get_legend_handles_labels()
    kwargs = font_kwargs(*labels)
    return {"prop": {"family": kwargs["fontfamily"]}} if kwargs else {}
