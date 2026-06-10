import math


def linear(p: float) -> float:
    return p


# Quadratic
def quadratic_ease_in(p: float) -> float:
    return p * p

def quadratic_ease_out(p: float) -> float:
    return -(p * (p - 2.0))

def quadratic_ease_in_out(p: float) -> float:
    if p < 0.5:
        return 2.0 * p * p
    return (-2.0 * p * p) + (4.0 * p) - 1.0


# Cubic
def cubic_ease_in(p: float) -> float:
    return p * p * p

def cubic_ease_out(p: float) -> float:
    f = p - 1.0
    return f * f * f + 1.0

def cubic_ease_in_out(p: float) -> float:
    if p < 0.5:
        return 4.0 * p * p * p
    f = (2.0 * p) - 2.0
    return 0.5 * f * f * f + 1.0


# Quartic
def quartic_ease_in(p: float) -> float:
    return p * p * p * p

def quartic_ease_out(p: float) -> float:
    f = p - 1.0
    return f * f * f * (1.0 - p) + 1.0

def quartic_ease_in_out(p: float) -> float:
    if p < 0.5:
        return 8.0 * p * p * p * p
    f = p - 1.0
    return -8.0 * f * f * f * f + 1.0


# Quintic
def quintic_ease_in(p: float) -> float:
    return p * p * p * p * p

def quintic_ease_out(p: float) -> float:
    f = p - 1.0
    return f * f * f * f * f + 1.0

def quintic_ease_in_out(p: float) -> float:
    if p < 0.5:
        return 16.0 * p * p * p * p * p
    f = (2.0 * p) - 2.0
    return 0.5 * f * f * f * f * f + 1.0


# Sine
def sine_ease_in(p: float) -> float:
    return math.sin((p - 1.0) * math.pi / 2.0) + 1.0

def sine_ease_out(p: float) -> float:
    return math.sin(p * math.pi / 2.0)

def sine_ease_in_out(p: float) -> float:
    return 0.5 * (1.0 - math.cos(p * math.pi))


# Circular
def circular_ease_in(p: float) -> float:
    return 1.0 - math.sqrt(1.0 - p * p)

def circular_ease_out(p: float) -> float:
    return math.sqrt((2.0 - p) * p)

def circular_ease_in_out(p: float) -> float:
    if p < 0.5:
        return 0.5 * (1.0 - math.sqrt(1.0 - 4.0 * p * p))
    return 0.5 * (math.sqrt(-((2.0 * p) - 3.0) * ((2.0 * p) - 1.0)) + 1.0)


# Exponential
def exponential_ease_in(p: float) -> float:
    return 0.0 if p == 0.0 else math.pow(2.0, 10.0 * (p - 1.0))

def exponential_ease_out(p: float) -> float:
    return 1.0 if p == 1.0 else 1.0 - math.pow(2.0, -10.0 * p)

def exponential_ease_in_out(p: float) -> float:
    if p == 0.0 or p == 1.0:
        return p
    if p < 0.5:
        return 0.5 * math.pow(2.0, (20.0 * p) - 10.0)
    return -0.5 * math.pow(2.0, (-20.0 * p) + 10.0) + 1.0


# Elastic
def elastic_ease_in(p: float) -> float:
    return math.sin(13.0 * math.pi / 2.0 * p) * math.pow(2.0, 10.0 * (p - 1.0))

def elastic_ease_out(p: float) -> float:
    return math.sin(-13.0 * math.pi / 2.0 * (p + 1.0)) * math.pow(2.0, -10.0 * p) + 1.0

def elastic_ease_in_out(p: float) -> float:
    if p < 0.5:
        return 0.5 * math.sin(13.0 * math.pi / 2.0 * (2.0 * p)) * math.pow(2.0, 10.0 * ((2.0 * p) - 1.0))
    return 0.5 * (math.sin(-13.0 * math.pi / 2.0 * ((2.0 * p - 1.0) + 1.0)) * math.pow(2.0, -10.0 * (2.0 * p - 1.0)) + 2.0)


# Back
def back_ease_in(p: float) -> float:
    return p * p * p - p * math.sin(p * math.pi)

def back_ease_out(p: float) -> float:
    f = 1.0 - p
    return 1.0 - (f * f * f - f * math.sin(f * math.pi))

def back_ease_in_out(p: float) -> float:
    if p < 0.5:
        f = 2.0 * p
        return 0.5 * (f * f * f - f * math.sin(f * math.pi))
    f = 1.0 - (2.0 * p - 1.0)
    return 0.5 * (1.0 - (f * f * f - f * math.sin(f * math.pi))) + 0.5


# Bounce
def bounce_ease_out(p: float) -> float:
    if p < 4.0 / 11.0:
        return (121.0 * p * p) / 16.0
    elif p < 8.0 / 11.0:
        return (363.0 / 40.0 * p * p) - (99.0 / 10.0 * p) + 17.0 / 5.0
    elif p < 9.0 / 10.0:
        return (4356.0 / 361.0 * p * p) - (35442.0 / 1805.0 * p) + 16061.0 / 1805.0
    return (54.0 / 5.0 * p * p) - (513.0 / 25.0 * p) + 268.0 / 25.0

def bounce_ease_in(p: float) -> float:
    return 1.0 - bounce_ease_out(1.0 - p)

def bounce_ease_in_out(p: float) -> float:
    if p < 0.5:
        return 0.5 * bounce_ease_in(p * 2.0)
    return 0.5 * bounce_ease_out(p * 2.0 - 1.0) + 0.5
