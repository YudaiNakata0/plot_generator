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
