# rules/deviation.py

# Shared raw-% deviation maths for benchmark and average comparisons.
#
# The result is signed: positive means the submitted value is above
# the reference, negative means below. Thresholds and severity are
# applied to the magnitude, so direction never changes whether a
# value is flagged, only how the finding reads.


def signed_deviation_percent(value, reference):
    return ((value - reference) / abs(reference)) * 100


def describe_direction(signed_percent):
    return "above" if signed_percent > 0 else "below"
