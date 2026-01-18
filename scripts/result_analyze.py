#!/usr/bin/env python3
import cv2
import numpy as np
import argparse
import sys


class ColorAreaAnalyzer:
    def __init__(self, image_path):
        self.image_path = image_path
        self.image = cv2.imread(image_path)

        if self.image is None:
            raise FileNotFoundError(f"画像が読み込めません: {image_path}")

        # BGR -> HSV
        self.hsv = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)

        # マスク初期化
        self.yellow_mask = None
        self.white_mask = None
        self.non_white_mask = None

    def extract_yellow(self):
        """黄色領域を抽出し、面積を返す"""
        yellow_lower = np.array([10, 50, 50])
        yellow_upper = np.array([50, 255, 255])

        self.yellow_mask = cv2.inRange(
            self.hsv, yellow_lower, yellow_upper
        )

        yellow_area = cv2.countNonZero(self.yellow_mask)
        return yellow_area

    def extract_white(self):
        """白色領域を抽出"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])

        self.white_mask = cv2.inRange(
            self.hsv, white_lower, white_upper
        )

    def compute_non_white_area(self):
        """白を除いた領域の面積を返す"""
        if self.white_mask is None:
            self.extract_white()

        self.non_white_mask = cv2.bitwise_not(self.white_mask)
        non_white_area = cv2.countNonZero(self.non_white_mask)
        return non_white_area

    # def visualize(self):
    #     """面積計算対象を可視化"""
    #     yellow_extracted = None
    #     non_white_extracted = None

    #     if self.yellow_mask is not None:
    #         yellow_extracted = cv2.bitwise_and(
    #             self.image, self.image, mask=self.yellow_mask
    #         )

    #     if self.non_white_mask is not None:
    #         non_white_extracted = cv2.bitwise_and(
    #             self.image, self.image, mask=self.non_white_mask
    #         )

    #     cv2.imshow("Original Image", self.image)

    #     if self.yellow_mask is not None:
    #         cv2.imshow("Yellow Mask", self.yellow_mask)
    #         cv2.imshow("Yellow Extracted", yellow_extracted)

    #     if self.white_mask is not None:
    #         cv2.imshow("White Mask", self.white_mask)

    #     if self.non_white_mask is not None:
    #         cv2.imshow("Non-White Extracted", non_white_extracted)

    #     cv2.waitKey(0)
    #     cv2.destroyAllWindows()

    def visualize(self):
        windows = [
            "Original Image",
            "Yellow Mask",
            "Yellow Extracted",
            "White Mask",
            "Non-White Extracted"
        ]

        # ウィンドウ作成（リサイズ可能）
        for w in windows:
            cv2.namedWindow(w, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
            cv2.resizeWindow(w, 500, 400)

        yellow_extracted = None
        non_white_extracted = None

        if self.yellow_mask is not None:
            yellow_extracted = cv2.bitwise_and(
                self.image, self.image, mask=self.yellow_mask
            )

        if self.non_white_mask is not None:
            non_white_extracted = cv2.bitwise_and(
                self.image, self.image, mask=self.non_white_mask
            )

        # 表示
        cv2.imshow("Original Image", self.image)

        if self.yellow_mask is not None:
            cv2.imshow("Yellow Mask", self.yellow_mask)
            cv2.imshow("Yellow Extracted", yellow_extracted)

        if self.white_mask is not None:
            cv2.imshow("White Mask", self.white_mask)

        if self.non_white_mask is not None:
            cv2.imshow("Non-White Extracted", non_white_extracted)

        # ---- ここが重要 ----
        # Alt+Tabしても閉じないイベントループ
        while True:
            key = cv2.waitKey(50) & 0xFF

            # Esc または q で終了
            if key == 27 or key == ord('q'):
                break

            # ウィンドウが閉じられたら終了
            if cv2.getWindowProperty("Original Image", cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description="黄色領域と白を除いた領域の面積を計算"
    )
    parser.add_argument(
        "image_path",
        type=str,
        help="入力画像のパス"
    )

    args = parser.parse_args()

    try:
        analyzer = ColorAreaAnalyzer(args.image_path)

        yellow_area = analyzer.extract_yellow()
        non_white_area = analyzer.compute_non_white_area()

        print(f"黄色部分の面積 [pixel]        : {yellow_area}")
        print(f"白色を除いた全体の面積 [pixel]: {non_white_area}")
        percentage = (yellow_area / non_white_area * 100) if non_white_area > 0 else 0
        print(f"黄色部分の割合 [%]             : {percentage:.2f}")

        analyzer.visualize()

    except FileNotFoundError as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
