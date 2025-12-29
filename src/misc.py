from random import normalvariate
import math
from typing import Optional


def get_random_data(mu: int, sigma: int):
    return normalvariate(mu, sigma)  # mock normal distribution


def calculate_z_score(data: list[float], n=10) -> Optional[float]:
    if len(data) < 2:
        return None

    recent_data = data[-n:]

    mean = sum(recent_data) / len(recent_data)

    variance = sum((x - mean) ** 2 for x in recent_data) / len(recent_data)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        z_score = 0.0
    else:
        z_score = (recent_data[-1] - mean) / std_dev

    return z_score
