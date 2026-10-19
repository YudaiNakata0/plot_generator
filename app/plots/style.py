# scripts/ の論文用の図の見た目を引き継ぐ共通スタイル

import matplotlib


# 図全体の文字設定。Times New Roman にない日本語だけは、下の
# font_kwargs() で利用可能な日本語フォントに切り替える。
FONT_FAMILY = "Times New Roman"
FONT_SIZE = 36
AXES_LABEL_SIZE = 24
AXES_TITLE_SIZE = 28
FIGURE_TITLE_SIZE = 28
TICK_LABEL_SIZE = 24
LEGEND_FONT_SIZE = 10

matplotlib.rcParams.update(
    {
        "font.family": FONT_FAMILY,
        "font.size": FONT_SIZE,
        "axes.labelsize": AXES_LABEL_SIZE,
        "axes.titlesize": AXES_TITLE_SIZE,
        "figure.titlesize": FIGURE_TITLE_SIZE,
        "xtick.labelsize": TICK_LABEL_SIZE,
        "ytick.labelsize": TICK_LABEL_SIZE,
        "legend.fontsize": LEGEND_FONT_SIZE,
    }
)

# 目標値の線 (axhline)
TARGET_LINE = dict(color="C1", alpha=0.5)
# 目標値の許容範囲の帯 (axhspan)
TARGET_BAND = dict(color="C1", alpha=0.2)

# 時間で色付けする軌跡のカラーマップ
TIME_CMAP = "viridis"
# 目標領域（円）
TARGET_AREA = dict(color="C1", alpha=0.2)
# 軌跡の開始・終了のマーカー
START_MARKER = dict(marker="o", color="black")
END_MARKER = dict(marker="x", color="black")

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
# （英語だけの図は Times New Roman）
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
    """文字列に応じたフォント指定を返す（set_title などに渡す）。"""
    if any(text and not str(text).isascii() for text in texts):
        jp_font = _find_jp_font()
        if jp_font:
            return {"fontfamily": jp_font}
    return {"fontfamily": FONT_FAMILY}


def legend_kwargs(ax):
    """凡例のラベルに日本語があれば legend(prop=...) 用の引数を返す。"""
    _, labels = ax.get_legend_handles_labels()
    kwargs = font_kwargs(*labels)
    return {"prop": {"family": kwargs["fontfamily"]}} if kwargs else {}
