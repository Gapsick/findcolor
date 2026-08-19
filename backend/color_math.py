import math


def rgb_to_lab(rgb):
    values = []
    for channel in rgb:
        value = channel / 255
        values.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = values
    x = (red * 0.4124 + green * 0.3576 + blue * 0.1805) / 0.95047
    y = (red * 0.2126 + green * 0.7152 + blue * 0.0722)
    z = (red * 0.0193 + green * 0.1192 + blue * 0.9505) / 1.08883

    def pivot(value):
        return value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116

    fx, fy, fz = pivot(x), pivot(y), pivot(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(first_rgb, second_rgb):
    first = rgb_to_lab(first_rgb)
    second = rgb_to_lab(second_rgb)
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second)))


def similarity_score(first_rgb, second_rgb):
    # Delta E 60 이상은 사실상 다른 색으로 보고 0점 처리한다.
    return round(max(0, 100 * (1 - delta_e(first_rgb, second_rgb) / 60)), 1)
